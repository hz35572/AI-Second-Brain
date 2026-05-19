from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.rag.generator import NOT_FOUND_ANSWER, RAGGenerator
from app.rag.retriever import RAGRetriever
from app.rag.schemas import RAGResult, RetrievedChunk
from app.services.citation_validator import repair_missing_citations, validate_answer_citations


class RAGPipeline:
    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        retriever: RAGRetriever | None = None,
        generator: RAGGenerator | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.retriever = retriever or RAGRetriever(db, settings=self.settings)
        self.generator = generator or RAGGenerator(self.settings)

    async def answer(
        self,
        *,
        user_id: uuid.UUID,
        question: str,
        scope_type: str,
        scope_ids: list[uuid.UUID] | None,
        top_k: int | None = None,
    ) -> RAGResult:
        start = time.perf_counter()
        retrieved = await self.retriever.retrieve(
            user_id=user_id,
            query=question,
            scope_type=scope_type,
            scope_ids=scope_ids,
            top_k=top_k,
        )
        retrieval_ms = int((time.perf_counter() - start) * 1000)
        if not retrieved:
            return RAGResult(
                answer=NOT_FOUND_ANSWER,
                citations=[],
                metadata={"token_usage": 0, "retrieval_ms": retrieval_ms, "retrieved_count": 0},
            )

        generated, generation_meta = await self.generator.generate(question=question, chunks=retrieved)
        citations = self._build_citations(retrieved)
        answer = self._validate_or_degrade(generated, max_index=len(citations))
        if answer == NOT_FOUND_ANSWER:
            citations = []

        metadata = {
            **generation_meta,
            "retrieval_ms": retrieval_ms,
            "retrieved_count": len(retrieved),
        }
        return RAGResult(answer=answer, citations=citations, metadata=metadata)

    def _validate_or_degrade(self, answer: str, *, max_index: int) -> str:
        if answer.strip() == NOT_FOUND_ANSWER:
            return NOT_FOUND_ANSWER
        if validate_answer_citations(answer, max_index=max_index):
            return answer
        repaired = repair_missing_citations(answer, fallback_index=1)
        if validate_answer_citations(repaired, max_index=max_index):
            return repaired
        return NOT_FOUND_ANSWER

    @staticmethod
    def _build_citations(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        for chunk in chunks:
            snippet = " ".join((chunk.content or "").strip().split())
            preview = snippet[:300] + ("..." if len(snippet) > 300 else "")
            citations.append(
                {
                    "index": chunk.index,
                    "chunk_id": str(chunk.chunk_id),
                    "file_id": str(chunk.file_id),
                    "file_name": chunk.file_name,
                    "page": chunk.page_number,
                    "locator": chunk.locator,
                    "text": preview,
                    "highlight_positions": {
                        "start": chunk.start_pos or 0,
                        "end": chunk.end_pos or max(0, len(preview)),
                    },
                }
            )
        return citations
