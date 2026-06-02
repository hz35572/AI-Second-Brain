from __future__ import annotations

import re

from app.rag.schemas import QueryPlan


_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:\-]+|[\u4e00-\u9fff]")
_SPACE_RE = re.compile(r"\s+")
_TRAILING_FILLER_RE = re.compile(r"(吗|呢|啊|吧|呀|请问)$")
_INTENT_HINTS = ("怎么处理", "如何处理", "怎么办", "最快检查", "修复", "注意事项", "原因")


def normalize_query(query: str) -> str:
    """Normalize a user query without damaging commands, error codes, or API names."""
    normalized = _SPACE_RE.sub(" ", query.replace("\u3000", " ")).strip()
    normalized = re.sub(r"[？?！!。.,，]{2,}$", "", normalized)
    return _TRAILING_FILLER_RE.sub("", normalized).strip()


def tokenize_query(text: str) -> list[str]:
    """Tokenize mixed Chinese and technical text for lightweight BM25 scoring."""
    tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
    return [token for token in tokens if token.strip()]


def build_query_plan(query: str) -> QueryPlan:
    """Build the fixed query variants used by hybrid retrieval."""
    normalized = normalize_query(query)
    keywords = _dedupe_tokens(tokenize_query(normalized))
    variants = [normalized] if normalized else []

    keyword_query = " ".join(keywords)
    if keyword_query and keyword_query != normalized.lower():
        variants.append(keyword_query)

    intent_query = _build_intent_query(normalized)
    if intent_query and intent_query not in variants:
        variants.append(intent_query)

    return QueryPlan(normalized_query=normalized, variants=variants[:3], keywords=keywords)


def _build_intent_query(normalized: str) -> str:
    if not normalized:
        return ""
    if any(hint in normalized for hint in _INTENT_HINTS):
        return normalized
    return f"{normalized} 最快检查 修复方法 注意事项"


def _dedupe_tokens(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped
