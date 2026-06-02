from __future__ import annotations

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.rag.query import tokenize_query
from app.rag.schemas import RetrievedChunk


CASE_RE = re.compile(
    r"### Q(?P<number>\d+)\s*-\s*(?P<question_type>[^\n]+)\n"
    r"\*\*问题：(?P<question>.*?)\*\*\n\n"
    r"\*\*答案原文：\*\*\n(?P<answer>.*?)\n\n"
    r"\*\*来源：\*\*\s*(?P<source_file>[^，,\n]+)[，,]\s*段落：(?P<section>.*?)\n",
    re.S,
)
QUOTE_RE = re.compile(r'^[\s"“”]+|[\s"“”]+$')
SPACE_RE = re.compile(r"\s+")
TECH_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:\-]+")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(slots=True)
class RAGEvalCase:
    number: int
    question_type: str
    question: str
    expected_answer: str
    expected_file: str
    expected_section: str


@dataclass(slots=True)
class ChunkHit:
    rank: int
    file_hit: bool
    section_hit: bool
    answer_coverage: float
    answer_hit: bool
    relevance: int
    file_name: str
    chunk_id: str
    section_text: str | None
    preview: str


@dataclass(slots=True)
class CaseHitReport:
    case: RAGEvalCase
    hits: list[ChunkHit]
    top_k: int

    @property
    def file_hit(self) -> bool:
        return any(hit.file_hit for hit in self.hits[: self.top_k])

    @property
    def section_hit(self) -> bool:
        return any(hit.section_hit for hit in self.hits[: self.top_k])

    @property
    def answer_hit(self) -> bool:
        return any(hit.answer_hit for hit in self.hits[: self.top_k])

    @property
    def answer_mrr(self) -> float:
        for hit in self.hits[: self.top_k]:
            if hit.answer_hit:
                return 1 / hit.rank
        return 0.0

    @property
    def file_mrr(self) -> float:
        for hit in self.hits[: self.top_k]:
            if hit.file_hit:
                return 1 / hit.rank
        return 0.0

    @property
    def ndcg(self) -> float:
        gains = [hit.relevance for hit in self.hits[: self.top_k]]
        ideal = sorted(gains, reverse=True)
        return _dcg(gains) / (_dcg(ideal) or 1.0)

    @property
    def best_answer_coverage(self) -> float:
        return max((hit.answer_coverage for hit in self.hits[: self.top_k]), default=0.0)


def parse_qa_markdown(markdown: str) -> list[RAGEvalCase]:
    """Parse the project RAG QA markdown into structured evaluation cases."""
    cases: list[RAGEvalCase] = []
    for match in CASE_RE.finditer(markdown):
        cases.append(
            RAGEvalCase(
                number=int(match.group("number")),
                question_type=match.group("question_type").strip(),
                question=_clean_inline(match.group("question")),
                expected_answer=_clean_answer(match.group("answer")),
                expected_file=match.group("source_file").strip(),
                expected_section=match.group("section").strip(),
            )
        )
    return cases


def evaluate_case_hits(
    case: RAGEvalCase,
    chunks: list[RetrievedChunk],
    *,
    top_k: int,
    answer_threshold: float = 0.35,
) -> CaseHitReport:
    """Score retrieved chunks for one QA case."""
    hits = [
        _score_chunk(case=case, chunk=chunk, rank=rank, answer_threshold=answer_threshold)
        for rank, chunk in enumerate(chunks[:top_k], start=1)
    ]
    return CaseHitReport(case=case, hits=hits, top_k=top_k)


def summarize_reports(reports: list[CaseHitReport]) -> dict[str, Any]:
    """Aggregate case-level hit reports into metrics."""
    total = len(reports)
    if total == 0:
        return {
            "total": 0,
            "file_hit_rate": 0.0,
            "section_hit_rate": 0.0,
            "answer_hit_rate": 0.0,
            "file_mrr": 0.0,
            "answer_mrr": 0.0,
            "ndcg": 0.0,
            "best_answer_coverage": 0.0,
        }
    return {
        "total": total,
        "file_hit_rate": _avg(1.0 if report.file_hit else 0.0 for report in reports),
        "section_hit_rate": _avg(1.0 if report.section_hit else 0.0 for report in reports),
        "answer_hit_rate": _avg(1.0 if report.answer_hit else 0.0 for report in reports),
        "file_mrr": _avg(report.file_mrr for report in reports),
        "answer_mrr": _avg(report.answer_mrr for report in reports),
        "ndcg": _avg(report.ndcg for report in reports),
        "best_answer_coverage": _avg(report.best_answer_coverage for report in reports),
    }


def summarize_by_question_type(reports: list[CaseHitReport]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[CaseHitReport]] = {}
    for report in reports:
        grouped.setdefault(report.case.question_type, []).append(report)
    return {question_type: summarize_reports(items) for question_type, items in sorted(grouped.items())}


def report_to_dict(report: CaseHitReport) -> dict[str, Any]:
    return {
        "question_id": f"Q{report.case.number}",
        "question_type": report.case.question_type,
        "question": report.case.question,
        "expected_file": report.case.expected_file,
        "expected_section": report.case.expected_section,
        "file_hit": report.file_hit,
        "section_hit": report.section_hit,
        "answer_hit": report.answer_hit,
        "answer_mrr": report.answer_mrr,
        "file_mrr": report.file_mrr,
        "ndcg": report.ndcg,
        "best_answer_coverage": report.best_answer_coverage,
        "hits": [
            {
                "rank": hit.rank,
                "file_hit": hit.file_hit,
                "section_hit": hit.section_hit,
                "answer_hit": hit.answer_hit,
                "answer_coverage": hit.answer_coverage,
                "relevance": hit.relevance,
                "file_name": hit.file_name,
                "chunk_id": hit.chunk_id,
                "section_text": hit.section_text,
                "preview": hit.preview,
            }
            for hit in report.hits
        ],
    }


def _score_chunk(
    *,
    case: RAGEvalCase,
    chunk: RetrievedChunk,
    rank: int,
    answer_threshold: float,
) -> ChunkHit:
    file_hit = _normalize_text(chunk.file_name) == _normalize_text(case.expected_file)
    section_text = _chunk_section_text(chunk)
    section_hit = file_hit and _contains_normalized(section_text, case.expected_section)
    answer_coverage = answer_text_coverage(case.expected_answer, chunk.content)
    answer_hit = file_hit and answer_coverage >= answer_threshold
    relevance = 3 if answer_hit else 2 if section_hit else 1 if file_hit else 0
    return ChunkHit(
        rank=rank,
        file_hit=file_hit,
        section_hit=section_hit,
        answer_coverage=answer_coverage,
        answer_hit=answer_hit,
        relevance=relevance,
        file_name=chunk.file_name,
        chunk_id=str(chunk.chunk_id),
        section_text=section_text or None,
        preview=_preview(chunk.content),
    )


def answer_text_coverage(expected_answer: str, candidate_text: str) -> float:
    """Return a robust 0..1 coverage estimate for an expected answer inside a chunk."""
    expected = _normalize_text(expected_answer)
    candidate = _normalize_text(candidate_text)
    if not expected or not candidate:
        return 0.0
    if expected in candidate:
        return 1.0

    units = _coverage_units(expected)
    if units:
        matched = sum(1 for unit in units if unit in candidate)
        return matched / len(units)
    return SequenceMatcher(None, expected, candidate).ratio()


def _coverage_units(text: str) -> list[str]:
    tech_tokens = TECH_TOKEN_RE.findall(text.lower())
    chinese_units: list[str] = []
    for match in CHINESE_RE.finditer(text):
        value = match.group(0)
        if len(value) <= 2:
            chinese_units.append(value)
            continue
        chinese_units.extend(value[index : index + 2] for index in range(len(value) - 1))
    raw_units = [*tech_tokens, *chinese_units]
    deduped: list[str] = []
    seen: set[str] = set()
    for unit in raw_units:
        if unit and unit not in seen:
            seen.add(unit)
            deduped.append(unit)
    return deduped


def _chunk_section_text(chunk: RetrievedChunk) -> str:
    metadata = chunk.metadata or {}
    locator = chunk.locator or {}
    parts = [
        str(metadata.get("heading_path") or ""),
        str(metadata.get("section_title") or ""),
        _stringify_path(locator.get("path") or locator.get("heading_path")),
        chunk.content[:300],
    ]
    return " ".join(part for part in parts if part)


def _contains_normalized(text: str, needle: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_needle = _normalize_text(needle)
    if not normalized_needle:
        return False
    if normalized_needle in normalized_text:
        return True
    needle_tokens = tokenize_query(normalized_needle)
    if not needle_tokens:
        return False
    return all(token in normalized_text for token in needle_tokens)


def _clean_inline(value: str) -> str:
    return SPACE_RE.sub(" ", QUOTE_RE.sub("", value)).strip()


def _clean_answer(value: str) -> str:
    return QUOTE_RE.sub("", value.strip())


def _normalize_text(value: str) -> str:
    value = QUOTE_RE.sub("", value or "").lower()
    value = re.sub(r"[`*_#\[\]（）()\s，。；;：:、,.!?！？\"“”]+", "", value)
    return value.strip()


def _stringify_path(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    if value is None:
        return ""
    return str(value)


def _preview(text: str, *, length: int = 160) -> str:
    compact = SPACE_RE.sub(" ", text.strip())
    return compact[:length] + ("..." if len(compact) > length else "")


def _dcg(gains: list[int]) -> float:
    return sum((2**gain - 1) / math.log2(index + 2) for index, gain in enumerate(gains))


def _avg(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)
