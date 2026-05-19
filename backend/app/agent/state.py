from __future__ import annotations

import uuid
from typing import Any, TypedDict

from app.rag.schemas import RetrievedChunk


class QAAgentState(TypedDict, total=False):
    user_id: uuid.UUID
    question: str
    scope_type: str
    scope_ids: list[uuid.UUID] | None
    top_k: int | None
    retrieved: list[RetrievedChunk]
    retrieval_ms: int
    generated_answer: str
    generation_meta: dict[str, Any]
    answer: str
    citations: list[dict[str, Any]]
    metadata: dict[str, Any]
    validation_status: str
    node_trace: list[str]
