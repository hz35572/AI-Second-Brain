from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

from app.core.config import Settings, get_settings


EMBEDDING_DIMENSIONS: dict[str, int] = {
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
        if not self.settings.OPENAI_API_KEY:
            return [self._local_embedding(text) for text in cleaned]

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional runtime package
            raise RuntimeError("openai package is required when AISB_OPENAI_API_KEY is configured") from exc

        client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        response = await client.embeddings.create(model=self.model, input=list(cleaned))
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
