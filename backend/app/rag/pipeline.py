from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.workflow import QAAgentWorkflow
from app.core.config import Settings, get_settings
from app.rag.generator import RAGGenerator
from app.rag.retriever import RAGRetriever
from app.rag.schemas import RAGResult


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
        self.workflow = QAAgentWorkflow(
            db,
            settings=self.settings,
            retriever=self.retriever,
            generator=self.generator,
        )

    async def answer(
        self,
        *,
        user_id: uuid.UUID,
        question: str,
        scope_type: str,
        scope_ids: list[uuid.UUID] | None,
        top_k: int | None = None,
    ) -> RAGResult:
        return await self.workflow.answer(
            user_id=user_id,
            question=question,
            scope_type=scope_type,
            scope_ids=scope_ids,
            top_k=top_k,
        )
