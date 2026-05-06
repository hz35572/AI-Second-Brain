from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.file import File
from app.db.models.folder import Folder
from app.repositories.chunks import FileChunkRepository
from app.repositories.conversations import ConversationRepository
from app.repositories.files import FileRepository
from app.repositories.messages import MessageRepository
from app.services.citation_validator import repair_missing_citations, validate_answer_citations


def _chunk_stream(text: str, *, size: int = 20) -> list[str]:
    text = text or ""
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.files = FileRepository(db)
        self.chunks = FileChunkRepository(db)

    async def _scope_file_ids(self, *, user_id: uuid.UUID, scope_type: str, scope_ids: list[uuid.UUID] | None) -> list[uuid.UUID] | None:
        if scope_type == "global":
            return None
        if scope_type == "file":
            return scope_ids or []
        if scope_type == "folder":
            if not scope_ids:
                return []
            # include descendants via path prefix
            folder_id = scope_ids[0]
            folder = await self.db.get(Folder, folder_id)
            if not folder or folder.user_id != user_id:
                return []
            descendant_ids = list(
                (await self.db.execute(select(Folder.id).where(Folder.user_id == user_id, Folder.path.like(f"{folder.path}%"))))
                .scalars()
                .all()
            )
            if not descendant_ids:
                return []
            file_ids = list(
                (await self.db.execute(select(File.id).where(File.user_id == user_id, File.folder_id.in_(descendant_ids))))
                .scalars()
                .all()
            )
            return file_ids
        return None

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
        file_ids = await self._scope_file_ids(user_id=user_id, scope_type=conv.scope_type, scope_ids=scope_ids)

        retrieved = await self.chunks.search(user_id=user_id, query=question, file_ids=file_ids, limit=top_k)
        if not retrieved:
            return "知识库中未找到相关内容。", [], {"token_usage": 0, "latency_ms": 0}

        file_name_by_id: dict[uuid.UUID, str] = {}
        file_ids_needed = {c.file_id for c in retrieved}
        if file_ids_needed:
            res = await self.db.execute(select(File.id, File.name).where(File.id.in_(list(file_ids_needed))))
            for fid, name in res.all():
                file_name_by_id[fid] = name

        citations: list[dict] = []
        lines: list[str] = []
        for i, c in enumerate(retrieved, start=1):
            snippet = (c.content or "").strip().replace("\n", " ")
            snippet = snippet[:200] + ("..." if len(snippet) > 200 else "")
            lines.append(f"- {snippet} [{i}]")
            citations.append(
                {
                    "index": i,
                    "chunk_id": str(c.id),
                    "file_id": str(c.file_id),
                    "file_name": file_name_by_id.get(c.file_id, ""),
                    "page": c.page_number,
                    "locator": c.locator,
                    "text": snippet,
                    "highlight_positions": {"start": c.start_pos or 0, "end": c.end_pos or max(0, len(snippet))},
                }
            )

        answer = "\n".join(lines)

        # Citation completeness validation + one repair pass (docs/TECH_DESIGN.md).
        if not validate_answer_citations(answer, max_index=len(citations)):
            repaired = repair_missing_citations(answer, fallback_index=1)
            if validate_answer_citations(repaired, max_index=len(citations)):
                answer = repaired
            else:
                return "知识库中未找到相关内容。", [], {"token_usage": 0, "latency_ms": 0}

        return answer, citations, {"token_usage": 0, "latency_ms": 0}

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
