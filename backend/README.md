# Backend

FastAPI backend skeleton for AI Second Brain.

Run (dev):

```powershell
cd ..
docker compose up -d postgres redis
cd backend
uv sync
alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Environment:

- Copy `.env.example` to `.env` and adjust values (variables use `AISB_` prefix).
