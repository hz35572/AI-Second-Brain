import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.file_chunk import FileChunk


class FileChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_by_file(self, file_id: uuid.UUID) -> None:
        await self.db.execute(delete(FileChunk).where(FileChunk.file_id == file_id))

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        file_id: uuid.UUID,
        chunk_index: int,
        content: str,
        page_number: int | None,
        start_pos: int | None,
        end_pos: int | None,
        locator: dict | None,
    ) -> FileChunk:
        chunk = FileChunk(
            user_id=user_id,
            file_id=file_id,
            chunk_index=chunk_index,
            content=content,
            page_number=page_number,
            start_pos=start_pos,
            end_pos=end_pos,
            locator=locator,
        )
        self.db.add(chunk)
        await self.db.flush()
        return chunk

    async def search(
        self,
        *,
        user_id: uuid.UUID,
        query: str,
        file_ids: list[uuid.UUID] | None,
        limit: int,
    ) -> list[FileChunk]:
        stmt = select(FileChunk).where(FileChunk.user_id == user_id)
        if file_ids:
            stmt = stmt.where(FileChunk.file_id.in_(file_ids))
        if query.strip():
            stmt = stmt.where(FileChunk.content.ilike(f"%{query.strip()}%"))
        stmt = stmt.order_by(FileChunk.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())
