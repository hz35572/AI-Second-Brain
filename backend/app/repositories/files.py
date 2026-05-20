from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.file import File


class FileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, file_id: uuid.UUID) -> File | None:
        return await self.db.get(File, file_id)

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        folder_id: uuid.UUID | None,
        name: str,
        original_name: str | None,
        file_path: str,
        file_size: int,
        mime_type: str | None,
        sha256: str | None,
        status: str,
    ) -> File:
        f = File(
            user_id=user_id,
            folder_id=folder_id,
            name=name,
            original_name=original_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            sha256=sha256,
            status=status,
        )
        self.db.add(f)
        await self.db.flush()
        return f

    async def list(
        self,
        *,
        user_id: uuid.UUID,
        folder_id: uuid.UUID | None,
        root_only: bool = False,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[File]]:
        stmt = select(File).where(File.user_id == user_id)
        count_stmt = select(func.count(File.id)).where(File.user_id == user_id)
        if root_only:
            stmt = stmt.where(File.folder_id.is_(None))
            count_stmt = count_stmt.where(File.folder_id.is_(None))
        elif folder_id is not None:
            stmt = stmt.where(File.folder_id == folder_id)
            count_stmt = count_stmt.where(File.folder_id == folder_id)
        if status is not None:
            stmt = stmt.where(File.status == status)
            count_stmt = count_stmt.where(File.status == status)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(File.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await self.db.execute(stmt)).scalars().all())
        return total, items

    async def list_by_folder_ids(self, *, user_id: uuid.UUID, folder_ids: list[uuid.UUID]) -> list[File]:
        if not folder_ids:
            return []

        res = await self.db.execute(select(File).where(File.user_id == user_id, File.folder_id.in_(folder_ids)))
        return list(res.scalars().all())

    async def update_status(self, file_id: uuid.UUID, status: str, *, error_message: str | None = None) -> None:
        f = await self.get(file_id)
        if not f:
            return
        f.status = status
        if error_message is not None:
            f.error_message = error_message

    async def delete(self, file_id: uuid.UUID) -> None:
        await self.db.execute(delete(File).where(File.id == file_id))
