import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.file import File
from app.db.models.folder import Folder


class FolderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, folder_id: uuid.UUID) -> Folder | None:
        return await self.db.get(Folder, folder_id)

    async def list_by_user(self, user_id: uuid.UUID) -> list[Folder]:
        res = await self.db.execute(select(Folder).where(Folder.user_id == user_id).order_by(Folder.path))
        return list(res.scalars().all())

    async def create(
        self, *, user_id: uuid.UUID, name: str, parent_id: uuid.UUID | None, path: str, sort_order: int = 0
    ) -> Folder:
        folder = Folder(user_id=user_id, name=name, parent_id=parent_id, path=path, sort_order=sort_order)
        self.db.add(folder)
        await self.db.flush()
        return folder

    async def file_counts_by_folder(self, user_id: uuid.UUID) -> dict[uuid.UUID, int]:
        res = await self.db.execute(
            select(File.folder_id, func.count(File.id)).where(File.user_id == user_id).group_by(File.folder_id)
        )
        out: dict[uuid.UUID, int] = {}
        for folder_id, count in res.all():
            if folder_id is None:
                continue
            out[folder_id] = int(count)
        return out
