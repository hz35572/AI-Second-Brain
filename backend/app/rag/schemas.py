from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RetrievedChunk:
    index: int
    chunk_id: uuid.UUID
    file_id: uuid.UUID
    file_name: str
    content: str
    score: float
    page_number: int | None
    start_pos: int | None
    end_pos: int | None
    locator: dict[str, Any] | None
    chunk_index: int
    metadata: dict[str, Any] | None = None
    context_before: str | None = None
    context_after: str | None = None


@dataclass(slots=True)
class RAGResult:
    answer: str
    citations: list[dict[str, Any]]
    metadata: dict[str, Any]


@dataclass(slots=True)
class QueryPlan:
    normalized_query: str
    variants: list[str]
    keywords: list[str]


@dataclass(slots=True)
class RerankResult:
    chunk_id: uuid.UUID
    score: float
    rank: int
