from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings
from app.rag.reranker import QwenReranker
from app.rag.schemas import RetrievedChunk


def _chunk(index: int = 1, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        index=index,
        chunk_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        file_name="doc.md",
        content="Telegram getMe returned 401 需要重新生成 BotFather token。",
        score=score,
        page_number=None,
        start_pos=0,
        end_pos=30,
        locator={"type": "markdown", "start": 0, "end": 30},
        chunk_index=index - 1,
    )


@pytest.mark.asyncio
async def test_qwen_reranker_degrades_without_api_key() -> None:
    settings = Settings(RERANK_API_KEY="", RERANK_PROVIDER="dashscope")
    reranker = QwenReranker(settings)

    results, metadata = await reranker.rerank(query="Telegram 401", chunks=[_chunk(score=0.7), _chunk(score=0.5)])

    assert [result.rank for result in results] == [1, 2]
    assert [result.score for result in results] == [0.7, 0.5]
    assert metadata["rerank_model"] == "qwen3-rerank"
    assert metadata["rerank_degraded"] is True
    assert metadata["rerank_degraded_reason"] == "missing_api_key"
