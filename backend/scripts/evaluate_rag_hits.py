from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.rag.evaluation import evaluate_case_hits, parse_qa_markdown, report_to_dict, summarize_by_question_type
from app.rag.evaluation import summarize_reports


logger = logging.getLogger("app.rag.evaluation")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval hit metrics from tests/rag_test_qa.md.")
    parser.add_argument("--qa-file", default="tests/rag_test_qa.md", help="QA markdown path relative to backend/.")
    parser.add_argument("--user-id", default="", help="User id whose indexed files should be evaluated.")
    parser.add_argument("--scope-type", default="global", choices=["global", "folder", "file"])
    parser.add_argument("--scope-id", action="append", default=[], help="Scope id. Repeat for multiple file scopes.")
    parser.add_argument("--top-k", type=int, default=6, help="Number of final chunks to score.")
    parser.add_argument("--answer-threshold", type=float, default=0.35, help="Answer coverage threshold for AnswerHit.")
    parser.add_argument("--json-output", default="", help="Optional JSON report output path.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings.LOG_LEVEL = args.log_level
    settings.LOG_FILE_ENABLED = False
    settings.LOG_QUEUE_ENABLED = False
    configure_logging(settings)

    qa_path = Path(args.qa_file)
    cases = parse_qa_markdown(qa_path.read_text(encoding="utf-8"))
    logger.info("rag eval start: qa_file=%s cases=%s top_k=%s", qa_path, len(cases), args.top_k)

    from app.db.session import get_db_context
    from app.rag.retriever import RAGRetriever

    try:
        async with get_db_context() as db:
            user_id = await _resolve_user_id(db, args.user_id)
            scope_ids = [uuid.UUID(raw_id) for raw_id in args.scope_id]
            retriever = RAGRetriever(db)
            reports = []
            for case in cases:
                chunks = await retriever.retrieve(
                    user_id=user_id,
                    query=case.question,
                    scope_type=args.scope_type,
                    scope_ids=scope_ids,
                    top_k=args.top_k,
                )
                report = evaluate_case_hits(
                    case,
                    chunks,
                    top_k=args.top_k,
                    answer_threshold=args.answer_threshold,
                )
                reports.append(report)
                _log_case(report=report, metadata=retriever.last_metadata)
    except OSError as exc:
        logger.error(
            "rag eval database unavailable: %s. %s",
            exc,
            _database_hint(),
        )
        raise SystemExit(2) from exc

    summary = summarize_reports(reports)
    output = {
        "summary": summary,
        "by_question_type": summarize_by_question_type(reports),
        "cases": [report_to_dict(report) for report in reports],
    }
    logger.info("rag eval summary: %s", _compact_json(summary))
    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("rag eval json written: %s", output_path)
    else:
        print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


async def _resolve_user_id(db: Any, raw_user_id: str) -> uuid.UUID:
    from sqlalchemy import select

    from app.db.models.user import User

    if raw_user_id:
        return uuid.UUID(raw_user_id)
    result = await db.execute(select(User.id).order_by(User.created_at.asc()).limit(1))
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise RuntimeError("No user found. Pass --user-id after registering and ingesting test files.")
    return user_id


def _log_case(*, report: Any, metadata: dict[str, Any]) -> None:
    first_hit = report.hits[0] if report.hits else None
    logger.info(
        "rag eval case: q=Q%s type=%s expected_file=%s file_hit=%s section_hit=%s "
        "answer_hit=%s answer_mrr=%.3f coverage=%.3f top_file=%s strategy=%s rerank_degraded=%s",
        report.case.number,
        report.case.question_type,
        report.case.expected_file,
        report.file_hit,
        report.section_hit,
        report.answer_hit,
        report.answer_mrr,
        report.best_answer_coverage,
        first_hit.file_name if first_hit else None,
        metadata.get("retrieval_strategy"),
        metadata.get("rerank_degraded"),
    )
    if logger.isEnabledFor(logging.DEBUG):
        for hit in report.hits:
            logger.debug(
                "rag eval hit: q=Q%s rank=%s file=%s file_hit=%s section_hit=%s "
                "answer_hit=%s coverage=%.3f relevance=%s chunk_id=%s preview=%s",
                report.case.number,
                hit.rank,
                hit.file_name,
                hit.file_hit,
                hit.section_hit,
                hit.answer_hit,
                hit.answer_coverage,
                hit.relevance,
                hit.chunk_id,
                hit.preview,
            )


def _compact_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _database_hint() -> str:
    return (
        "Start local dependencies with `docker compose up -d postgres redis qdrant`, "
        "then run `uv run alembic -c alembic.ini upgrade head` from backend/. "
        f"Current Postgres target is {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}."
    )


if __name__ == "__main__":
    asyncio.run(main())
