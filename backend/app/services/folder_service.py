from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.folders import FolderRepository


class FolderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.folders = FolderRepository(db)

    async def create_folder(self, *, user_id: uuid.UUID, name: str, parent_id: uuid.UUID | None) -> dict:
        if parent_id is None:
            path = f"/{name}"
        else:
            parent = await self.folders.get(parent_id)
            if not parent or parent.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "ERR_FOLDER_NOT_FOUND", "message": "父文件夹不存在", "details": {}},
                )
            path = f"{parent.path}/{name}"

        folder = await self.folders.create(user_id=user_id, name=name, parent_id=parent_id, path=path)
        await self.db.commit()
        return {"id": str(folder.id), "name": folder.name, "parent_id": str(folder.parent_id) if folder.parent_id else None, "path": folder.path}

    async def folder_tree(self, *, user_id: uuid.UUID) -> list[dict]:
        folders = await self.folders.list_by_user(user_id)
        counts = await self.folders.file_counts_by_folder(user_id)

        nodes: dict[uuid.UUID, dict] = {}
        for f in folders:
            nodes[f.id] = {"id": str(f.id), "name": f.name, "children": [], "file_count": counts.get(f.id, 0)}

        roots: list[dict] = []
        for f in folders:
            node = nodes[f.id]
            if f.parent_id and f.parent_id in nodes:
                nodes[f.parent_id]["children"].append(node)
            else:
                roots.append(node)

        return [{"id": "root", "name": "根目录", "children": roots, "file_count": 0}]

