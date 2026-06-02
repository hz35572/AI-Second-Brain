from __future__ import annotations

import uuid

import pytest

from app.agent.workflow import QAAgentWorkflow
from app.rag.generator import NOT_FOUND_ANSWER
from app.rag.schemas import RetrievedChunk


def _chunk(index: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        index=index,
        chunk_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        file_name="doc.txt",
        content="AI Second Brain is a knowledge base system.",
        score=0.9,
        page_number=1,
        start_pos=0,
        end_pos=42,
        locator={"type": "text", "start": 0, "end": 42},
        chunk_index=0,
    )


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk], metadata: dict | None = None):
        self.chunks = chunks
        self.last_metadata = metadata or {}
        self.calls: list[dict] = []

    async def retrieve(self, **kwargs) -> list[RetrievedChunk]:
        self.calls.append(kwargs)
        return self.chunks


class FakeGenerator:
    def __init__(self, answer: str):
        self.answer = answer
        self.calls: list[dict] = []

    async def generate(self, **kwargs) -> tuple[str, dict]:
        self.calls.append(kwargs)
        return self.answer, {"model": "fake", "token_usage": 0}


@pytest.mark.asyncio
async def test_agent_workflow_returns_cited_answer() -> None:
    workflow = QAAgentWorkflow(
        None,
        retriever=FakeRetriever([_chunk()], {"retrieval_strategy": "hybrid_rrf_rerank", "reranked_count": 1}),
        generator=FakeGenerator("有依据的回答 [1]"),
    )
    result = await workflow.answer(user_id=uuid.uuid4(), question="what", scope_type="global", scope_ids=[])

    assert result.answer == "有依据的回答 [1]"
    assert len(result.citations) == 1
    assert result.metadata["retrieved_count"] == 1
    assert result.metadata["selected_count"] == 1
    assert result.metadata["retrieval_strategy"] == "hybrid_rrf_rerank"
    assert result.metadata["reranked_count"] == 1
    assert result.metadata["validation_status"] == "valid"


@pytest.mark.asyncio
async def test_agent_workflow_repairs_missing_citation() -> None:
    workflow = QAAgentWorkflow(None, retriever=FakeRetriever([_chunk()]), generator=FakeGenerator("有依据的回答"))
    result = await workflow.answer(user_id=uuid.uuid4(), question="what", scope_type="global", scope_ids=[])

    assert result.answer == "有依据的回答 [1]"
    assert len(result.citations) == 1
    assert result.metadata["validation_status"] == "repaired"


@pytest.mark.asyncio
async def test_agent_workflow_degrades_invalid_citation() -> None:
    workflow = QAAgentWorkflow(None, retriever=FakeRetriever([_chunk()]), generator=FakeGenerator("越界回答 [2]"))
    result = await workflow.answer(user_id=uuid.uuid4(), question="what", scope_type="global", scope_ids=[])

    assert result.answer == NOT_FOUND_ANSWER
    assert result.citations == []
    assert result.metadata["validation_status"] == "degraded"
