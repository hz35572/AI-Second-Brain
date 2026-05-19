from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

from app.core.config import Settings, get_settings


EMBEDDING_DIMENSIONS: dict[str, int] = {
    "BAAI/bge-m3": 1024,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


def embedding_dimensions(model: str) -> int:
    return EMBEDDING_DIMENSIONS.get(model, 1536)


class EmbeddingClient:
    """Embedding client with a deterministic local fallback for tests/dev."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = self.settings.EMBEDDING_MODEL
        self.dimensions = embedding_dimensions(self.model)

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        cleaned = [text or "" for text in texts]
        if not cleaned:
            return []
        if self.settings.EMBEDDING_PROVIDER == "local":
            return [self._local_embedding(text) for text in cleaned]
        if self.settings.EMBEDDING_PROVIDER == "siliconflow":
            if not self.settings.SILICONFLOW_API_KEY:
                return [self._local_embedding(text) for text in cleaned]
            return await self._remote_embeddings(
                api_key=self.settings.SILICONFLOW_API_KEY,
                base_url=self.settings.SILICONFLOW_BASE_URL,
                texts=cleaned,
            )
        if not self.settings.OPENAI_API_KEY:
            return [self._local_embedding(text) for text in cleaned]
        return await self._remote_embeddings(
            api_key=self.settings.OPENAI_API_KEY,
            base_url=None,
            texts=cleaned,
        )

    async def _remote_embeddings(
        self,
        *,
        api_key: str,
        base_url: str | None,
        texts: Sequence[str],
    ) -> list[list[float]]:
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional runtime package
            raise RuntimeError("openai package is required for remote embeddings") from exc

        client = AsyncOpenAI(**client_kwargs)
        response = await client.embeddings.create(model=self.model, input=list(texts))
        by_index = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in by_index]

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    def _local_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            tokens = [text.lower()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
