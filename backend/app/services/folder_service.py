from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.vector_store import QdrantVectorStore
from app.repositories.chunks import FileChunkRepository
from app.repositories.files import FileRepository
from app.repositories.folders import FolderRepository
from app.repositories.tasks import TaskRepository
from app.services.storage_service import StorageService


class FolderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.folders = FolderRepository(db)
        self.files = FileRepository(db)
        self.chunks = FileChunkRepository(db)
        self.tasks = TaskRepository(db)
        self.storage = StorageService()
        self.vector_store = QdrantVectorStore()

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

    async def delete_folder(self, *, user_id: uuid.UUID, folder_id: uuid.UUID) -> dict:
        folder = await self.folders.get(folder_id)
        if not folder or folder.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ERR_FOLDER_NOT_FOUND", "message": "文件夹不存在", "details": {}},
            )

        descendant_folders = await self.folders.list_descendants(user_id=user_id, path=folder.path)
        folder_ids = [item.id for item in descendant_folders]
        files = await self.files.list_by_folder_ids(user_id=user_id, folder_ids=folder_ids)
        storage_paths = [item.file_path for item in files]

        for item in files:
            await self.vector_store.delete_by_file(user_id=user_id, file_id=item.id)
            await self.tasks.delete_by_file(item.id)
            await self.chunks.delete_by_file(item.id)
            await self.files.delete(item.id)

        await self.folders.delete(folder_id)
        await self.db.commit()

        for file_path in storage_paths:
            self.storage.delete_file(file_path=file_path)

        return {
            "deleted": True,
            "folder_id": str(folder_id),
            "deleted_folder_count": len(folder_ids),
            "deleted_file_count": len(files),
        }

