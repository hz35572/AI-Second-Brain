from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.workflow import QAAgentWorkflow
from app.repositories.conversations import ConversationRepository
from app.repositories.messages import MessageRepository


def _chunk_stream(text: str, *, size: int = 20) -> list[str]:
    text = text or ""
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.agent = QAAgentWorkflow(db)

    async def generate_answer(
        self,
        *,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        question: str,
        top_k: int = 5,
    ) -> tuple[str, list[dict], dict]:
        conv = await self.conversations.get(conversation_id)
        if not conv or conv.user_id != user_id:
            raise ValueError("conversation not found")

        scope_ids = [uuid.UUID(str(x)) for x in (conv.scope_ids or [])]
        result = await self.agent.answer(
            user_id=user_id,
            question=question,
            scope_type=conv.scope_type,
            scope_ids=scope_ids,
            top_k=top_k,
        )
        return result.answer, result.citations, result.metadata

    async def append_user_message(self, *, conversation_id: uuid.UUID, content: str) -> None:
        await self.messages.create(conversation_id=conversation_id, role="user", content=content)
        conv = await self.conversations.get(conversation_id)
        if conv:
            conv.updated_at = datetime.now(timezone.utc)

    async def append_assistant_message(self, *, conversation_id: uuid.UUID, content: str, citations: list[dict], metadata: dict) -> None:
        await self.messages.create(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            citations=citations,
            metadata=metadata,
        )
        conv = await self.conversations.get(conversation_id)
        if conv:
            conv.updated_at = datetime.now(timezone.utc)

    async def run_sse(
        self,
        *,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        question: str,
    ) -> tuple[list[dict], list[dict], dict]:
        start = time.perf_counter()
        await self.append_user_message(conversation_id=conversation_id, content=question)
        answer, citations, metadata = await self.generate_answer(
            user_id=user_id,
            conversation_id=conversation_id,
            question=question,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        metadata = {**metadata, "latency_ms": latency_ms}
        await self.append_assistant_message(
            conversation_id=conversation_id,
            content=answer,
            citations=citations or None,
            metadata=metadata,
        )
        await self.db.commit()

        chunks = [{"type": "chunk", "content": part} for part in _chunk_stream(answer)]
        events: list[dict] = chunks
        if citations:
            events.append({"type": "citation", "citations": citations})
        events.append({"type": "done", "metadata": metadata})
        return events, citations, metadata
