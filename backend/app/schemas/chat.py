from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.citation import Citation


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    scope_type: str = Field(default="global")
    scope_ids: list[str] = Field(default_factory=list)


class ConversationCreateResponseData(BaseModel):
    id: str
    title: str | None = None
    scope_type: str
    created_at: str


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    stream: bool = True


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] | None = None
    created_at: str


class MessageListResponseData(BaseModel):
    items: list[MessageItem]


class ConversationListItem(BaseModel):
    id: str
    title: str | None = None
    message_count: int
    updated_at: str


class ConversationListResponseData(BaseModel):
    items: list[ConversationListItem]

