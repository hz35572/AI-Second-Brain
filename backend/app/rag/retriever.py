from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.file import File
from app.db.models.file_chunk import FileChunk
from app.db.models.folder import Folder
from app.rag.embeddings import EmbeddingClient
from app.rag.schemas import RetrievedChunk
from app.rag.vector_store import QdrantVectorStore


class RAGRetriever:
    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        embeddings: EmbeddingClient | None = None,
        vector_store: QdrantVectorStore | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.embeddings = embeddings or EmbeddingClient(self.settings)
        self.vector_store = vector_store or QdrantVectorStore(self.settings)

    async def resolve_scope_file_ids(
        self, *, user_id: uuid.UUID, scope_type: str, scope_ids: list[uuid.UUID] | None
    ) -> list[uuid.UUID] | None:
        if scope_type == "global":
            return None
        if scope_type == "file":
            return scope_ids or []
        if scope_type == "folder":
            if not scope_ids:
                return []
            folder = await self.db.get(Folder, scope_ids[0])
            if not folder or folder.user_id != user_id:
                return []
            descendant_ids = list(
                (
                    await self.db.execute(
                        select(Folder.id).where(Folder.user_id == user_id, Folder.path.like(f"{folder.path}%"))
                    )
                )
                .scalars()
                .all()
            )
            if not descendant_ids:
                return []
            return list(
                (
                    await self.db.execute(
                        select(File.id).where(File.user_id == user_id, File.folder_id.in_(descendant_ids))
                    )
                )
                .scalars()
                .all()
            )
        return None

    async def retrieve(
        self,
        *,
        user_id: uuid.UUID,
        query: str,
        scope_type: str,
        scope_ids: list[uuid.UUID] | None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        file_ids = await self.resolve_scope_file_ids(user_id=user_id, scope_type=scope_type, scope_ids=scope_ids)
        limit = top_k or self.settings.RAG_TOP_K
        query_vector = await self.embeddings.embed_query(query)
        hits = await self.vector_store.search(query_vector=query_vector, user_id=user_id, file_ids=file_ids, limit=limit)
        return await self._hydrate_hits(user_id=user_id, hits=hits)

    async def _hydrate_hits(self, *, user_id: uuid.UUID, hits: list[dict]) -> list[RetrievedChunk]:
        chunk_ids: list[uuid.UUID] = []
        scores: dict[uuid.UUID, float] = {}
        for hit in hits:
            payload = hit.get("payload") or {}
            raw_chunk_id = payload.get("chunk_id") or hit.get("id")
            try:
                chunk_id = uuid.UUID(str(raw_chunk_id))
            except (TypeError, ValueError):
                continue
            chunk_ids.append(chunk_id)
            scores[chunk_id] = float(hit.get("score") or 0.0)
        if not chunk_ids:
            return []

        stmt = (
            select(FileChunk, File.name)
            .join(File, File.id == FileChunk.file_id)
            .where(FileChunk.user_id == user_id, File.user_id == user_id, FileChunk.id.in_(chunk_ids))
        )
        rows = list((await self.db.execute(stmt)).all())
        order = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
        rows.sort(key=lambda row: (order.get(row[0].id, len(order)), row[0].chunk_index))

        retrieved: list[RetrievedChunk] = []
        for index, (chunk, file_name) in enumerate(rows, start=1):
            retrieved.append(
                RetrievedChunk(
                    index=index,
                    chunk_id=chunk.id,
                    file_id=chunk.file_id,
                    file_name=file_name,
                    content=chunk.content,
                    score=scores.get(chunk.id, 0.0),
                    page_number=chunk.page_number,
                    start_pos=chunk.start_pos,
                    end_pos=chunk.end_pos,
                    locator=chunk.locator,
                    chunk_index=chunk.chunk_index,
                )
            )
        return retrieved
