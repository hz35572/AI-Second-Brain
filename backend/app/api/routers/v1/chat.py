import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.utils import ok, parse_uuid
from app.core.database import get_db
from app.repositories.conversations import ConversationRepository
from app.repositories.messages import MessageRepository
from app.schemas.chat import ConversationCreateRequest, SendMessageRequest
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/conversations", status_code=201)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    scope_ids = [parse_uuid(x, field="scope_ids") for x in (payload.scope_ids or [])]
    conv = await ConversationRepository(db).create(
        user_id=current_user.id,
        title=payload.title,
        scope_type=payload.scope_type,
        scope_ids=scope_ids,
    )
    await db.commit()
    return ok(
        {
            "id": str(conv.id),
            "title": conv.title,
            "scope_type": conv.scope_type,
            "created_at": conv.created_at.isoformat(),
        }
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv_uuid = parse_uuid(conversation_id, field="conversation_id")

    async def event_stream() -> AsyncGenerator[str, None]:
        svc = ChatService(db)
        events, _citations, _metadata = await svc.run_sse(
            user_id=current_user.id,
            conversation_id=conv_uuid,
            question=payload.content,
        )
        for ev in events:
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv_uuid = parse_uuid(conversation_id, field="conversation_id")
    conv = await ConversationRepository(db).get(conv_uuid)
    if not conv or conv.user_id != current_user.id:
        return ok({"items": []})
    msgs = await MessageRepository(db).list(conversation_id=conv_uuid, page=max(1, page), page_size=min(100, max(1, page_size)))
    items = []
    for m in msgs:
        item = {"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        if m.role == "assistant":
            item["citations"] = m.citations or []
        items.append(item)
    return ok({"items": items})


@router.get("/conversations")
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await ConversationRepository(db).list(user_id=current_user.id, page=max(1, page), page_size=min(100, max(1, page_size)))
    items = []
    for conv, count in rows:
        items.append(
            {
                "id": str(conv.id),
                "title": conv.title,
                "message_count": count,
                "updated_at": conv.updated_at.isoformat(),
            }
        )
    return ok({"items": items})
