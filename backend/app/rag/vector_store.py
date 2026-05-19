from __future__ import annotations

import uuid
from collections.abc import Sequence
from math import sqrt
from typing import Any

from app.core.config import Settings, get_settings
from app.rag.embeddings import embedding_dimensions


class VectorStoreUnavailable(RuntimeError):
    """Raised when Qdrant cannot be used."""


class QdrantVectorStore:
    _memory_points: dict[str, dict[str, Any]] = {}

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.collection_name = self.settings.RAG_DEFAULT_COLLECTION
        self._client = None

    async def ensure_collection(self) -> None:
        client = self._try_get_client()
        if client is None:
            if not self._allow_memory_fallback:
                raise VectorStoreUnavailable("Qdrant client is unavailable in production")
            return
        try:
            await client.get_collection(self.collection_name)
            return
        except Exception:  # noqa: BLE001 - qdrant raises different typed errors across versions
            pass

        models = self._models()
        await client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=embedding_dimensions(self.settings.EMBEDDING_MODEL),
                distance=models.Distance.COSINE,
            ),
        )

    async def upsert_chunks(self, points: Sequence[dict[str, Any]]) -> None:
        if not points:
            return
        client = self._try_get_client()
        if client is None:
            if not self._allow_memory_fallback:
                raise VectorStoreUnavailable("Qdrant client is unavailable in production")
            self._memory_upsert(points)
            return
        try:
            await self.ensure_collection()
        except Exception:  # noqa: BLE001 - local/dev fallback when Qdrant is unavailable
            if not self._allow_memory_fallback:
                raise
            self._memory_upsert(points)
            return
        models = self._models()
        qdrant_points = [
            models.PointStruct(
                id=point["id"],
                vector=point["vector"],
                payload=point["payload"],
            )
            for point in points
        ]
        try:
            await client.upsert(collection_name=self.collection_name, points=qdrant_points)
        except Exception:  # noqa: BLE001 - local/dev fallback when Qdrant is unavailable
            if not self._allow_memory_fallback:
                raise
            self._memory_upsert(points)

    async def search(
        self,
        *,
        query_vector: list[float],
        user_id: uuid.UUID,
        file_ids: list[uuid.UUID] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        client = self._try_get_client()
        if client is None:
            if not self._allow_memory_fallback:
                raise VectorStoreUnavailable("Qdrant client is unavailable in production")
            return self._memory_search(query_vector=query_vector, user_id=user_id, file_ids=file_ids, limit=limit)
        try:
            await self.ensure_collection()
        except Exception:  # noqa: BLE001 - local/dev fallback when Qdrant is unavailable
            if not self._allow_memory_fallback:
                raise
            return self._memory_search(query_vector=query_vector, user_id=user_id, file_ids=file_ids, limit=limit)
        models = self._models()
        conditions = [
            models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
        ]
        if file_ids is not None:
            if not file_ids:
                return []
            conditions.append(
                models.FieldCondition(key="file_id", match=models.MatchAny(any=[str(file_id) for file_id in file_ids]))
            )
        query_filter = models.Filter(must=conditions)
        try:
            results = await client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception:  # noqa: BLE001 - local/dev fallback when Qdrant is unavailable
            if not self._allow_memory_fallback:
                raise
            return self._memory_search(query_vector=query_vector, user_id=user_id, file_ids=file_ids, limit=limit)
        return [
            {
                "id": str(point.id),
                "score": float(point.score),
                "payload": dict(point.payload or {}),
            }
            for point in results
        ]

    async def delete_by_file(self, *, user_id: uuid.UUID, file_id: uuid.UUID) -> None:
        self._memory_delete_by_file(user_id=user_id, file_id=file_id)
        client = self._try_get_client()
        if client is None:
            if not self._allow_memory_fallback:
                raise VectorStoreUnavailable("Qdrant client is unavailable in production")
            return
        try:
            await self.ensure_collection()
        except Exception:  # noqa: BLE001 - memory cleanup above already keeps dev/test consistent
            if not self._allow_memory_fallback:
                raise
            return
        models = self._models()
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="file_id", match=models.MatchValue(value=str(file_id))),
                ]
            )
        )
        try:
            await client.delete(collection_name=self.collection_name, points_selector=selector)
        except Exception:  # noqa: BLE001 - memory cleanup above already keeps dev/test consistent
            if not self._allow_memory_fallback:
                raise
            return

    def _try_get_client(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import AsyncQdrantClient
        except ImportError as exc:  # pragma: no cover - depends on optional runtime package
            _ = exc
            return None

        self._client = AsyncQdrantClient(
            host=self.settings.QDRANT_HOST,
            port=self.settings.QDRANT_PORT,
            api_key=self.settings.QDRANT_API_KEY or None,
        )
        return self._client

    def _get_client(self):
        client = self._try_get_client()
        if client is None:
            raise VectorStoreUnavailable("qdrant-client package is required for vector search")
        return client

    @property
    def _allow_memory_fallback(self) -> bool:
        return self.settings.ENVIRONMENT != "production"

    @staticmethod
    def _models():
        try:
            from qdrant_client import models
        except ImportError as exc:  # pragma: no cover - depends on optional runtime package
            raise VectorStoreUnavailable("qdrant-client package is required for vector search") from exc
        return models

    @classmethod
    def _memory_upsert(cls, points: Sequence[dict[str, Any]]) -> None:
        for point in points:
            cls._memory_points[str(point["id"])] = {
                "id": str(point["id"]),
                "vector": list(point["vector"]),
                "payload": dict(point.get("payload") or {}),
            }

    @classmethod
    def _memory_search(
        cls,
        *,
        query_vector: list[float],
        user_id: uuid.UUID,
        file_ids: list[uuid.UUID] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        allowed_file_ids = {str(file_id) for file_id in file_ids} if file_ids is not None else None
        scored: list[dict[str, Any]] = []
        for point in cls._memory_points.values():
            payload = point["payload"]
            if payload.get("user_id") != str(user_id):
                continue
            if allowed_file_ids is not None and payload.get("file_id") not in allowed_file_ids:
                continue
            scored.append(
                {
                    "id": point["id"],
                    "score": cls._cosine_similarity(query_vector, point["vector"]),
                    "payload": payload,
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    @classmethod
    def _memory_delete_by_file(cls, *, user_id: uuid.UUID, file_id: uuid.UUID) -> None:
        for point_id, point in list(cls._memory_points.items()):
            payload = point["payload"]
            if payload.get("user_id") == str(user_id) and payload.get("file_id") == str(file_id):
                del cls._memory_points[point_id]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        dot = sum(left[index] * right[index] for index in range(size))
        left_norm = sqrt(sum(value * value for value in left[:size])) or 1.0
        right_norm = sqrt(sum(value * value for value in right[:size])) or 1.0
        return dot / (left_norm * right_norm)
