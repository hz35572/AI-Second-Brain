import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.message import Message


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.db.get(Conversation, conversation_id)

    async def create(
        self, *, user_id: uuid.UUID, title: str | None, scope_type: str, scope_ids: list[uuid.UUID] | None
    ) -> Conversation:
        conv = Conversation(user_id=user_id, title=title, scope_type=scope_type, scope_ids=scope_ids)
        self.db.add(conv)
        await self.db.flush()
        return conv

    async def list(self, *, user_id: uuid.UUID, page: int, page_size: int) -> list[tuple[Conversation, int]]:
        msg_count = func.count(Message.id).label("message_count")
        stmt = (
            select(Conversation, msg_count)
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user_id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.db.execute(stmt)
        return [(row[0], int(row[1])) for row in res.all()]
