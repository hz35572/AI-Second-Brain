from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Sequence
from typing import Any

from app.core.config import Settings, get_settings
from app.rag.schemas import RerankResult, RetrievedChunk


class QwenReranker:
    """DashScope qwen3-rerank client with safe local degradation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def rerank(
        self, *, query: str, chunks: Sequence[RetrievedChunk]
    ) -> tuple[list[RerankResult], dict[str, Any]]:
        if not chunks:
            return [], self._metadata(degraded=False, reason=None, count=0)
        if self.settings.RERANK_PROVIDER == "none" or not self.settings.RERANK_API_KEY:
            return self._fallback(chunks, reason="missing_api_key")

        try:
            payload = {
                "model": self.settings.RERANK_MODEL,
                "input": {
                    "query": query,
                    "documents": [self._document_text(chunk) for chunk in chunks],
                },
            }
            response = await asyncio.wait_for(
                asyncio.to_thread(self._post_json, payload),
                timeout=self.settings.RERANK_TIMEOUT_SECONDS,
            )
            results = self._parse_response(response=response, chunks=chunks)
        except (TimeoutError, OSError, urllib.error.URLError, ValueError, KeyError, TypeError):
            return self._fallback(chunks, reason="request_failed")

        if not results:
            return self._fallback(chunks, reason="empty_response")
        return results, self._metadata(degraded=False, reason=None, count=len(results))

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.settings.RERANK_BASE_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.RERANK_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.settings.RERANK_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def _parse_response(self, *, response: dict[str, Any], chunks: Sequence[RetrievedChunk]) -> list[RerankResult]:
        raw_results = response.get("output", {}).get("results") or response.get("results") or []
        parsed: list[RerankResult] = []
        for rank, item in enumerate(raw_results, start=1):
            index = int(item.get("index"))
            if index < 0 or index >= len(chunks):
                continue
            score = float(item.get("relevance_score", item.get("score", 0.0)))
            parsed.append(RerankResult(chunk_id=chunks[index].chunk_id, score=score, rank=rank))
        return parsed

    def _fallback(self, chunks: Sequence[RetrievedChunk], *, reason: str) -> tuple[list[RerankResult], dict[str, Any]]:
        results = [
            RerankResult(chunk_id=chunk.chunk_id, score=float(chunk.score), rank=index)
            for index, chunk in enumerate(chunks, start=1)
        ]
        return results, self._metadata(degraded=True, reason=reason, count=len(results))

    def _metadata(self, *, degraded: bool, reason: str | None, count: int) -> dict[str, Any]:
        return {
            "rerank_model": self.settings.RERANK_MODEL if self.settings.RERANK_PROVIDER != "none" else None,
            "reranked_count": count,
            "rerank_degraded": degraded,
            "rerank_degraded_reason": reason,
        }

    @staticmethod
    def _document_text(chunk: RetrievedChunk) -> str:
        metadata = chunk.metadata or {}
        heading_path = metadata.get("heading_path") or ""
        return f"文件：{chunk.file_name}\n章节：{heading_path}\n正文：{chunk.content}"
