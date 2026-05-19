from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.db.models.conversation import Conversation
from app.services.chat_service import ChatService


class FakeConversationRepo:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        if conversation_id == self.conversation.id:
            return self.conversation
        return None


class FakeMessageRepo:
    def __init__(self):
        self.created: list[dict] = []

    async def create(self, **kwargs):
        self.created.append(kwargs)
        return object()


class FakeAgent:
    def __init__(self):
        self.calls: list[dict] = []

    async def answer(self, **kwargs):
        self.calls.append(kwargs)
        return type(
            "Result",
            (),
            {
                "answer": "有依据的回答 [1]",
                "citations": [{"index": 1}],
                "metadata": {"model": "fake", "token_usage": 0, "retrieval_ms": 1, "retrieved_count": 1},
            },
        )()


@pytest.mark.asyncio
async def test_run_sse_emits_chunk_citation_done(monkeypatch) -> None:
    conversation = Conversation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="t",
        scope_type="global",
        scope_ids=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service = ChatService.__new__(ChatService)
    service.db = None
    service.conversations = FakeConversationRepo(conversation)
    service.messages = FakeMessageRepo()
    service.agent = FakeAgent()

    async def _noop_commit():
        return None

    service.db = type("DB", (), {"commit": staticmethod(_noop_commit)})()

    events, citations, metadata = await service.run_sse(
        user_id=conversation.user_id,
        conversation_id=conversation.id,
        question="what",
    )

    types = [event["type"] for event in events]
    assert types[0] == "chunk"
    assert types[-2:] == ["citation", "done"]
    assert all(event_type == "chunk" for event_type in types[: types.index("citation")])
    assert citations == [{"index": 1}]
    assert metadata["latency_ms"] >= 0
    assert service.messages.created[0]["role"] == "user"
    assert service.messages.created[1]["role"] == "assistant"
