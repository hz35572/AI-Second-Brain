from __future__ import annotations

import asyncio
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.files import FileRepository
from app.repositories.tasks import TaskRepository
from app.services.ingestion_service import IngestionService
from app.services.storage_service import StorageService
from app.tasks.background import run_background


async def _run_ingest_background(*, user_id: uuid.UUID, file_id: uuid.UUID, task_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        svc = IngestionService(db)
        await svc.ingest(user_id=user_id, file_id=file_id, task_id=task_id)


class FileService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageService()
        self.files = FileRepository(db)
        self.tasks = TaskRepository(db)

    async def upload_direct(self, *, user_id: uuid.UUID, upload: UploadFile, folder_id: uuid.UUID | None) -> dict:
        body = await upload.read()
        storage_meta = self.storage.save_direct_upload(user_id=user_id, filename=upload.filename or "upload.bin", body=body)

        f = await self.files.create(
            user_id=user_id,
            folder_id=folder_id,
            name=upload.filename or "upload.bin",
            original_name=upload.filename,
            file_path=storage_meta["file_path"],
            file_size=storage_meta["file_size"],
            mime_type=upload.content_type,
            sha256=storage_meta["sha256"],
            status="pending",
        )
        task = await self.tasks.create(user_id=user_id, task_type="embedding", related_file_id=f.id, status="pending")
        await self.db.commit()

        run_background(_run_ingest_background(user_id=user_id, file_id=f.id, task_id=task.id))
        return {"file_id": str(f.id), "task_id": str(task.id), "status": task.status}

    async def init_multipart(
        self,
        *,
        user_id: uuid.UUID,
        file_name: str,
        file_size: int,
        mime_type: str | None,
        folder_id: uuid.UUID | None,
    ) -> dict:
        return self.storage.init_multipart(
            user_id=user_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            folder_id=str(folder_id) if folder_id else None,
        )

    async def upload_chunk(self, *, user_id: uuid.UUID, upload_id: str, chunk_index: int, body: bytes) -> dict:
        self.storage.save_chunk(upload_id=upload_id, user_id=user_id, chunk_index=chunk_index, body=body)
        return {"chunk_index": chunk_index, "uploaded": True}

    async def complete_multipart(self, *, user_id: uuid.UUID, upload_id: str) -> dict:
        meta = self.storage.complete_multipart(upload_id=upload_id, user_id=user_id)

        folder_id = uuid.UUID(meta["folder_id"]) if meta.get("folder_id") else None
        f = await self.files.create(
            user_id=user_id,
            folder_id=folder_id,
            name=meta.get("original_name") or "upload.bin",
            original_name=meta.get("original_name"),
            file_path=meta["file_path"],
            file_size=meta["file_size"],
            mime_type=meta.get("mime_type"),
            sha256=meta.get("sha256"),
            status="pending",
        )
        task = await self.tasks.create(user_id=user_id, task_type="embedding", related_file_id=f.id, status="running")
        f.status = "parsing"
        await self.db.commit()

        run_background(_run_ingest_background(user_id=user_id, file_id=f.id, task_id=task.id))
        return {"file_id": str(f.id), "task_id": str(task.id), "status": "parsing"}
