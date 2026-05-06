import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import Task


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, task_id: uuid.UUID) -> Task | None:
        return await self.db.get(Task, task_id)

    async def create(
        self, *, user_id: uuid.UUID, task_type: str, related_file_id: uuid.UUID | None, status: str = "pending"
    ) -> Task:
        task = Task(user_id=user_id, task_type=task_type, related_file_id=related_file_id, status=status)
        self.db.add(task)
        await self.db.flush()
        return task

    async def set_progress(
        self,
        task_id: uuid.UUID,
        *,
        status: str | None = None,
        progress: int | None = None,
        error_message: str | None = None,
        result: dict | None = None,
    ) -> None:
        task = await self.get(task_id)
        if not task:
            return
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = max(0, min(100, int(progress)))
        if error_message is not None:
            task.error_message = error_message
        if result is not None:
            task.result = result
