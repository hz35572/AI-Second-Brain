from __future__ import annotations

import uuid

import pytest

from app.rag.generator import NOT_FOUND_ANSWER
from app.rag.pipeline import RAGPipeline
from app.rag.schemas import RAGResult, RetrievedChunk


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
    def __init__(self, chunks: list[RetrievedChunk]):
        self.chunks = chunks

    async def retrieve(self, **_kwargs) -> list[RetrievedChunk]:
        return self.chunks


class FakeGenerator:
    def __init__(self, answer: str):
        self.answer = answer

    async def generate(self, **_kwargs) -> tuple[str, dict]:
        return self.answer, {"model": "fake", "token_usage": 0}


@pytest.mark.asyncio
async def test_pipeline_returns_cited_answer() -> None:
    pipeline = RAGPipeline(None, retriever=FakeRetriever([_chunk()]), generator=FakeGenerator("有依据的回答 [1]"))
    result = await pipeline.answer(user_id=uuid.uuid4(), question="what", scope_type="global", scope_ids=[])

    assert isinstance(result, RAGResult)
    assert result.answer == "有依据的回答 [1]"
    assert len(result.citations) == 1
    assert result.citations[0]["index"] == 1


@pytest.mark.asyncio
async def test_pipeline_repairs_missing_citation() -> None:
    pipeline = RAGPipeline(None, retriever=FakeRetriever([_chunk()]), generator=FakeGenerator("有依据的回答"))
    result = await pipeline.answer(user_id=uuid.uuid4(), question="what", scope_type="global", scope_ids=[])

    assert result.answer == "有依据的回答 [1]"
    assert len(result.citations) == 1


@pytest.mark.asyncio
async def test_pipeline_degrades_invalid_citation() -> None:
    pipeline = RAGPipeline(None, retriever=FakeRetriever([_chunk()]), generator=FakeGenerator("越界回答 [2]"))
    result = await pipeline.answer(user_id=uuid.uuid4(), question="what", scope_type="global", scope_ids=[])

    assert result.answer == NOT_FOUND_ANSWER
    assert result.citations == []
