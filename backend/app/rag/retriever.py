from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.file import File
from app.db.models.file_chunk import FileChunk
from app.db.models.folder import Folder
from app.rag.embeddings import EmbeddingClient
from app.rag.query import build_query_plan, tokenize_query
from app.rag.reranker import QwenReranker
from app.rag.schemas import QueryPlan, RerankResult, RetrievedChunk
from app.rag.vector_store import QdrantVectorStore


RRF_K = 60
MAX_FUSION_CANDIDATES = 40


@dataclass(slots=True)
class _Candidate:
    chunk_id: uuid.UUID
    score: float = 0.0
    vector_rank: int | None = None
    vector_score: float | None = None
    keyword_rank: int | None = None
    keyword_score: float | None = None
    rrf_score: float = 0.0
    matched_query_variant: str | None = None


class RAGRetriever:
    """Hybrid RAG retriever using vector recall, lightweight BM25, RRF, and optional qwen rerank."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        embeddings: EmbeddingClient | None = None,
        vector_store: QdrantVectorStore | None = None,
        reranker: QwenReranker | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.embeddings = embeddings or EmbeddingClient(self.settings)
        self.vector_store = vector_store or QdrantVectorStore(self.settings)
        self.reranker = reranker or QwenReranker(self.settings)
        self.last_metadata: dict[str, Any] = {}

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
        query_plan = build_query_plan(query)
        file_ids = await self.resolve_scope_file_ids(user_id=user_id, scope_type=scope_type, scope_ids=scope_ids)
        if file_ids == []:
            self.last_metadata = self._empty_metadata(query_plan=query_plan, strategy="hybrid_rrf_rerank")
            return []

        if not self.settings.RAG_HYBRID_SEARCH:
            retrieved = await self._vector_only(user_id=user_id, query_plan=query_plan, file_ids=file_ids, top_k=top_k)
            self.last_metadata = {
                **self._base_metadata(query_plan=query_plan, strategy="vector"),
                "retrieved_count": len(retrieved),
                "reranked_count": 0,
                "rerank_degraded": False,
            }
            return retrieved

        candidates = await self._hybrid_candidates(user_id=user_id, query_plan=query_plan, file_ids=file_ids)
        hydrated = await self._hydrate_candidates(user_id=user_id, candidates=candidates[:MAX_FUSION_CANDIDATES])
        rerank_results, rerank_metadata = await self.reranker.rerank(
            query=query_plan.normalized_query,
            chunks=hydrated,
        )
        selected = self._select_reranked_chunks(
            chunks=hydrated,
            rerank_results=rerank_results,
            top_k=self._context_limit(top_k),
            apply_threshold=not rerank_metadata.get("rerank_degraded", False),
        )
        await self._attach_adjacent_context(user_id=user_id, chunks=selected)
        self._renumber(selected)
        self.last_metadata = {
            **self._base_metadata(query_plan=query_plan, strategy="hybrid_rrf_rerank"),
            **rerank_metadata,
            "retrieved_count": len(hydrated),
            "selected_count": len(selected),
            "vector_top_k": self.settings.RAG_VECTOR_TOP_K,
            "keyword_top_k": self.settings.RAG_KEYWORD_TOP_K,
        }
        return selected

    async def _vector_only(
        self,
        *,
        user_id: uuid.UUID,
        query_plan: QueryPlan,
        file_ids: list[uuid.UUID] | None,
        top_k: int | None,
    ) -> list[RetrievedChunk]:
        limit = top_k or self.settings.RAG_TOP_K
        query_vector = await self.embeddings.embed_query(query_plan.normalized_query)
        hits = await self.vector_store.search(
            query_vector=query_vector,
            user_id=user_id,
            file_ids=file_ids,
            limit=limit,
        )
        return await self._hydrate_hits(user_id=user_id, hits=hits)

    async def _hybrid_candidates(
        self,
        *,
        user_id: uuid.UUID,
        query_plan: QueryPlan,
        file_ids: list[uuid.UUID] | None,
    ) -> list[_Candidate]:
        candidates: dict[uuid.UUID, _Candidate] = {}
        for variant in query_plan.variants:
            query_vector = await self.embeddings.embed_query(variant)
            hits = await self.vector_store.search(
                query_vector=query_vector,
                user_id=user_id,
                file_ids=file_ids,
                limit=self.settings.RAG_VECTOR_TOP_K,
            )
            self._merge_vector_hits(candidates=candidates, hits=hits, variant=variant)

        keyword_hits = await self._keyword_search(
            user_id=user_id,
            query_plan=query_plan,
            file_ids=file_ids,
            limit=self.settings.RAG_KEYWORD_TOP_K,
        )
        self._merge_keyword_hits(candidates=candidates, hits=keyword_hits)
        merged = list(candidates.values())
        merged.sort(key=lambda item: (item.rrf_score, item.score), reverse=True)
        return merged

    def _merge_vector_hits(self, *, candidates: dict[uuid.UUID, _Candidate], hits: list[dict], variant: str) -> None:
        for rank, hit in enumerate(hits, start=1):
            chunk_id = self._hit_chunk_id(hit)
            if chunk_id is None:
                continue
            score = float(hit.get("score") or 0.0)
            candidate = candidates.setdefault(chunk_id, _Candidate(chunk_id=chunk_id))
            if candidate.vector_rank is None or rank < candidate.vector_rank:
                candidate.vector_rank = rank
                candidate.vector_score = score
                candidate.matched_query_variant = variant
            candidate.rrf_score += 1 / (RRF_K + rank)
            candidate.score = max(candidate.score, score)

    def _merge_keyword_hits(
        self, *, candidates: dict[uuid.UUID, _Candidate], hits: list[tuple[uuid.UUID, float]]
    ) -> None:
        for rank, (chunk_id, score) in enumerate(hits, start=1):
            candidate = candidates.setdefault(chunk_id, _Candidate(chunk_id=chunk_id))
            candidate.keyword_rank = rank
            candidate.keyword_score = score
            candidate.rrf_score += 1 / (RRF_K + rank)
            candidate.score = max(candidate.score, score)

    async def _keyword_search(
        self,
        *,
        user_id: uuid.UUID,
        query_plan: QueryPlan,
        file_ids: list[uuid.UUID] | None,
        limit: int,
    ) -> list[tuple[uuid.UUID, float]]:
        if not query_plan.keywords:
            return []
        stmt = (
            select(FileChunk.id, FileChunk.content, File.name)
            .join(File, File.id == FileChunk.file_id)
            .where(FileChunk.user_id == user_id, File.user_id == user_id)
        )
        if file_ids is not None:
            if not file_ids:
                return []
            stmt = stmt.where(FileChunk.file_id.in_(file_ids))
        rows = list((await self.db.execute(stmt)).all())
        if not rows:
            return []

        query_tokens = query_plan.keywords
        docs = [(chunk_id, tokenize_query(f"{file_name} {content}")) for chunk_id, content, file_name in rows]
        doc_count = len(docs)
        document_frequency: dict[str, int] = {}
        for _, tokens in docs:
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1

        avg_length = sum(len(tokens) for _, tokens in docs) / max(doc_count, 1)
        scored: list[tuple[uuid.UUID, float]] = []
        for chunk_id, tokens in docs:
            score = self._bm25_score(
                doc_tokens=tokens,
                query_tokens=query_tokens,
                document_frequency=document_frequency,
                doc_count=doc_count,
                avg_length=avg_length,
            )
            if score > 0:
                scored.append((chunk_id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    @staticmethod
    def _bm25_score(
        *,
        doc_tokens: list[str],
        query_tokens: list[str],
        document_frequency: dict[str, int],
        doc_count: int,
        avg_length: float,
    ) -> float:
        if not doc_tokens:
            return 0.0
        frequencies: dict[str, int] = {}
        for token in doc_tokens:
            frequencies[token] = frequencies.get(token, 0) + 1

        k1 = 1.5
        b = 0.75
        score = 0.0
        doc_length = len(doc_tokens)
        for token in query_tokens:
            term_frequency = frequencies.get(token, 0)
            if term_frequency == 0:
                continue
            df = document_frequency.get(token, 0)
            idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
            denominator = term_frequency + k1 * (1 - b + b * doc_length / max(avg_length, 1.0))
            score += idf * (term_frequency * (k1 + 1)) / denominator
        return score

    async def _hydrate_candidates(self, *, user_id: uuid.UUID, candidates: list[_Candidate]) -> list[RetrievedChunk]:
        if not candidates:
            return []
        by_id = {candidate.chunk_id: candidate for candidate in candidates}
        rows = await self._select_chunks(user_id=user_id, chunk_ids=list(by_id))
        order = {candidate.chunk_id: index for index, candidate in enumerate(candidates)}
        rows.sort(key=lambda row: order.get(row[0].id, len(order)))
        retrieved: list[RetrievedChunk] = []
        for index, (chunk, file_name, mime_type) in enumerate(rows, start=1):
            candidate = by_id[chunk.id]
            retrieved.append(
                self._to_retrieved_chunk(
                    index=index,
                    chunk=chunk,
                    file_name=file_name,
                    mime_type=mime_type,
                    score=candidate.score,
                    metadata={
                        "vector_rank": candidate.vector_rank,
                        "vector_score": candidate.vector_score,
                        "keyword_rank": candidate.keyword_rank,
                        "keyword_score": candidate.keyword_score,
                        "rrf_score": candidate.rrf_score,
                        "matched_query_variant": candidate.matched_query_variant,
                    },
                )
            )
        return retrieved

    async def _hydrate_hits(self, *, user_id: uuid.UUID, hits: list[dict]) -> list[RetrievedChunk]:
        chunk_ids: list[uuid.UUID] = []
        scores: dict[uuid.UUID, float] = {}
        for hit in hits:
            chunk_id = self._hit_chunk_id(hit)
            if chunk_id is None:
                continue
            chunk_ids.append(chunk_id)
            scores[chunk_id] = float(hit.get("score") or 0.0)
        if not chunk_ids:
            return []

        rows = await self._select_chunks(user_id=user_id, chunk_ids=chunk_ids)
        order = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
        rows.sort(key=lambda row: (order.get(row[0].id, len(order)), row[0].chunk_index))
        retrieved: list[RetrievedChunk] = []
        for index, (chunk, file_name, mime_type) in enumerate(rows, start=1):
            retrieved.append(
                self._to_retrieved_chunk(
                    index=index,
                    chunk=chunk,
                    file_name=file_name,
                    mime_type=mime_type,
                    score=scores.get(chunk.id, 0.0),
                    metadata={},
                )
            )
        return retrieved

    async def _select_chunks(
        self, *, user_id: uuid.UUID, chunk_ids: list[uuid.UUID]
    ) -> list[tuple[FileChunk, str, str | None]]:
        stmt = (
            select(FileChunk, File.name, File.mime_type)
            .join(File, File.id == FileChunk.file_id)
            .where(FileChunk.user_id == user_id, File.user_id == user_id, FileChunk.id.in_(chunk_ids))
        )
        return list((await self.db.execute(stmt)).all())

    def _select_reranked_chunks(
        self,
        *,
        chunks: list[RetrievedChunk],
        rerank_results: list[RerankResult],
        top_k: int,
        apply_threshold: bool,
    ) -> list[RetrievedChunk]:
        by_id = {chunk.chunk_id: chunk for chunk in chunks}
        selected: list[RetrievedChunk] = []
        for result in sorted(rerank_results, key=lambda item: item.rank):
            if apply_threshold and result.score < self.settings.RAG_MIN_RELEVANCE_SCORE:
                continue
            chunk = by_id.get(result.chunk_id)
            if chunk is None:
                continue
            metadata = dict(chunk.metadata or {})
            metadata["rerank_rank"] = result.rank
            metadata["rerank_score"] = result.score
            chunk.metadata = metadata
            chunk.score = result.score
            selected.append(chunk)
            if len(selected) >= top_k:
                break
        return selected

    def _context_limit(self, top_k: int | None) -> int:
        requested = top_k or self.settings.RAG_CONTEXT_MAX_CHUNKS
        return max(1, min(requested, self.settings.RAG_CONTEXT_MAX_CHUNKS, self.settings.RAG_RERANK_TOP_K))

    async def _attach_adjacent_context(self, *, user_id: uuid.UUID, chunks: list[RetrievedChunk]) -> None:
        if not chunks:
            return
        pairs = {(chunk.file_id, chunk.chunk_index - 1) for chunk in chunks if chunk.chunk_index > 0}
        pairs.update((chunk.file_id, chunk.chunk_index + 1) for chunk in chunks)
        stmt = select(FileChunk).where(
            FileChunk.user_id == user_id,
            tuple_(FileChunk.file_id, FileChunk.chunk_index).in_(pairs),
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        by_position = {(row.file_id, row.chunk_index): row.content for row in rows}
        for chunk in chunks:
            chunk.context_before = by_position.get((chunk.file_id, chunk.chunk_index - 1))
            chunk.context_after = by_position.get((chunk.file_id, chunk.chunk_index + 1))

    @staticmethod
    def _renumber(chunks: list[RetrievedChunk]) -> None:
        for index, chunk in enumerate(chunks, start=1):
            chunk.index = index

    @staticmethod
    def _hit_chunk_id(hit: dict) -> uuid.UUID | None:
        payload = hit.get("payload") or {}
        raw_chunk_id = payload.get("chunk_id") or hit.get("id")
        try:
            return uuid.UUID(str(raw_chunk_id))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_retrieved_chunk(
        *,
        index: int,
        chunk: FileChunk,
        file_name: str,
        mime_type: str | None,
        score: float,
        metadata: dict[str, Any],
    ) -> RetrievedChunk:
        locator = chunk.locator or {}
        heading_path = locator.get("path") or locator.get("heading_path") or []
        if isinstance(heading_path, list):
            heading_text = " > ".join(str(item) for item in heading_path if item)
        else:
            heading_text = str(heading_path)
        return RetrievedChunk(
            index=index,
            chunk_id=chunk.id,
            file_id=chunk.file_id,
            file_name=file_name,
            content=chunk.content,
            score=score,
            page_number=chunk.page_number,
            start_pos=chunk.start_pos,
            end_pos=chunk.end_pos,
            locator=chunk.locator,
            chunk_index=chunk.chunk_index,
            metadata={
                **metadata,
                "document_type": (locator.get("type") if locator else None) or mime_type,
                "heading_path": heading_text,
                "section_title": heading_text.split(" > ")[-1] if heading_text else None,
                "token_count": chunk.token_count,
            },
        )

    @staticmethod
    def _base_metadata(*, query_plan: QueryPlan, strategy: str) -> dict[str, Any]:
        return {
            "retrieval_strategy": strategy,
            "normalized_query": query_plan.normalized_query,
            "query_variants": query_plan.variants,
            "query_keywords": query_plan.keywords,
        }

    def _empty_metadata(self, *, query_plan: QueryPlan, strategy: str) -> dict[str, Any]:
        return {
            **self._base_metadata(query_plan=query_plan, strategy=strategy),
            "retrieved_count": 0,
            "selected_count": 0,
            "reranked_count": 0,
            "rerank_degraded": False,
        }
