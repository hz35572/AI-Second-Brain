import asyncio
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.main import create_app


async def _can_connect(db_url: str) -> bool:
    try:
        engine = create_async_engine(db_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.asyncio
async def test_full_flow_txt_upload_and_chat_sse():
    # Requires local Postgres (see docker-compose.yml). Skip if not available.
    settings = get_settings()
    if not await _can_connect(settings.database_url):
        pytest.skip("Postgres not available; start services via docker-compose.yml")

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "..", "alembic"))
    command.upgrade(alembic_cfg, "head")

    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        email = f"test-{uuid.uuid4()}@example.com"
        r = await client.post("/api/v1/auth/register", json={"email": email, "password": "password1", "name": "测试"})
        assert r.status_code == 201
        token = r.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        content = b"AI Second Brain is a knowledge base system.\nIt must cite sources."
        r = await client.post("/api/v1/files/upload", files={"file": ("doc.txt", content, "text/plain")}, headers=headers)
        assert r.status_code == 202
        task_id = r.json()["data"]["task_id"]

        # Wait for ingestion background task
        status_ = "pending"
        for _ in range(100):
            pr = await client.get(f"/api/v1/tasks/{task_id}/progress", headers=headers)
            assert pr.status_code == 200
            status_ = pr.json()["data"]["status"]
            if status_ in {"completed", "failed"}:
                break
            await asyncio.sleep(0.05)
        assert status_ == "completed"

        r = await client.post("/api/v1/chat/conversations", json={"title": "t", "scope_type": "global", "scope_ids": []}, headers=headers)
        assert r.status_code == 201
        conv_id = r.json()["data"]["id"]

        events = []
        async with client.stream(
            "POST",
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"content": "AI Second Brain", "stream": True},
            headers=headers,
        ) as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[len("data: ") :]
                if not payload:
                    continue
                events.append(__import__("json").loads(payload))

        assert events
        assert events[-1]["type"] == "done"

        seen_non_chunk = False
        combined = ""
        for ev in events:
            if ev["type"] == "chunk":
                assert not seen_non_chunk
                combined += ev.get("content", "")
            else:
                seen_non_chunk = True

        # citation must appear before done when answer exists
        types = [e["type"] for e in events]
        assert "citation" in types
        assert types.index("citation") < types.index("done")

        # ensure citation markers exist in final text
        assert "[" in combined and "]" in combined


@pytest.mark.asyncio
async def test_register_rejects_password_over_bcrypt_limit():
    settings = get_settings()
    if not await _can_connect(settings.database_url):
        pytest.skip("Postgres not available; start services via docker-compose.yml")

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "..", "alembic"))
    command.upgrade(alembic_cfg, "head")

    app = create_app()
    password = "a" * 73

    async with AsyncClient(app=app, base_url="http://test") as client:
        email = f"test-{uuid.uuid4()}@example.com"
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "too-long"},
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "ERR_INVALID_ARGUMENT"
    assert any("72 UTF-8 bytes" in error["msg"] for error in payload["details"]["errors"])
