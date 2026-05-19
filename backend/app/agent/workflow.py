from __future__ import annotations

import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import QAAgentState
from app.core.config import Settings, get_settings
from app.rag.generator import NOT_FOUND_ANSWER, RAGGenerator
from app.rag.retriever import RAGRetriever
from app.rag.schemas import RAGResult, RetrievedChunk
from app.services.citation_validator import repair_missing_citations, validate_answer_citations


class QAAgentWorkflow:
    """Minimal LangGraph workflow for scoped knowledge-base Q&A."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        retriever: RAGRetriever | None = None,
        generator: RAGGenerator | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.retriever = retriever or RAGRetriever(db, settings=self.settings)
        self.generator = generator or RAGGenerator(self.settings)
        self.graph = self._build_graph()

    async def answer(
        self,
        *,
        user_id: uuid.UUID,
        question: str,
        scope_type: str,
        scope_ids: list[uuid.UUID] | None,
        top_k: int | None = None,
    ) -> RAGResult:
        state = await self.graph.ainvoke(
            {
                "user_id": user_id,
                "question": question,
                "scope_type": scope_type,
                "scope_ids": scope_ids,
                "top_k": top_k,
            }
        )
        return RAGResult(
            answer=state["answer"],
            citations=state["citations"],
            metadata=state["metadata"],
        )

    def _build_graph(self):
        graph = StateGraph(QAAgentState)
        graph.add_node("load_context", self._load_context)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("generate", self._generate)
        graph.add_node("validate", self._validate)
        graph.add_node("emit", self._emit)

        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", "validate")
        graph.add_edge("validate", "emit")
        graph.add_edge("emit", END)
        return graph.compile()

    async def _load_context(self, state: QAAgentState) -> dict[str, Any]:
        return {
            "scope_ids": state.get("scope_ids") or [],
            "top_k": state.get("top_k"),
            "node_trace": [*state.get("node_trace", []), "load_context"],
        }

    async def _retrieve(self, state: QAAgentState) -> dict[str, Any]:
        start = time.perf_counter()
        retrieved = await self.retriever.retrieve(
            user_id=state["user_id"],
            query=state["question"],
            scope_type=state["scope_type"],
            scope_ids=state.get("scope_ids"),
            top_k=state.get("top_k"),
        )
        return {
            "retrieved": retrieved,
            "retrieval_ms": int((time.perf_counter() - start) * 1000),
            "node_trace": [*state.get("node_trace", []), "retrieve"],
        }

    async def _generate(self, state: QAAgentState) -> dict[str, Any]:
        generated, generation_meta = await self.generator.generate(
            question=state["question"],
            chunks=state.get("retrieved", []),
        )
        return {
            "generated_answer": generated,
            "generation_meta": generation_meta,
            "node_trace": [*state.get("node_trace", []), "generate"],
        }

    async def _validate(self, state: QAAgentState) -> dict[str, Any]:
        retrieved = state.get("retrieved", [])
        citations = self._build_citations(retrieved)
        answer, validation_status = self._validate_or_degrade(
            state.get("generated_answer", ""),
            max_index=len(citations),
        )
        if answer == NOT_FOUND_ANSWER:
            citations = []
        return {
            "answer": answer,
            "citations": citations,
            "validation_status": validation_status,
            "node_trace": [*state.get("node_trace", []), "validate"],
        }

    async def _emit(self, state: QAAgentState) -> dict[str, Any]:
        metadata = {
            **state.get("generation_meta", {}),
            "retrieval_ms": state.get("retrieval_ms", 0),
            "retrieved_count": len(state.get("retrieved", [])),
            "validation_status": state.get("validation_status", "unknown"),
        }
        return {
            "metadata": metadata,
            "node_trace": [*state.get("node_trace", []), "emit"],
        }

    def _validate_or_degrade(self, answer: str, *, max_index: int) -> tuple[str, str]:
        if not answer.strip() or answer.strip() == NOT_FOUND_ANSWER or max_index < 1:
            return NOT_FOUND_ANSWER, "degraded"
        if validate_answer_citations(answer, max_index=max_index):
            return answer, "valid"
        repaired = repair_missing_citations(answer, fallback_index=1)
        if validate_answer_citations(repaired, max_index=max_index):
            return repaired, "repaired"
        return NOT_FOUND_ANSWER, "degraded"

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
