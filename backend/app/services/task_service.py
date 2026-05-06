import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tasks import TaskRepository


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tasks = TaskRepository(db)

    async def get_progress(self, *, user_id: uuid.UUID, task_id: uuid.UUID) -> dict:
        task = await self.tasks.get(task_id)
        if not task or task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ERR_TASK_NOT_FOUND", "message": "任务不存在", "details": {}},
            )
        message = self._progress_message(task.task_type, task.status, task.progress)
        return {
            "task_id": str(task.id),
            "task_type": task.task_type,
            "status": task.status,
            "progress": int(task.progress),
            "message": message,
        }

    def _progress_message(self, task_type: str, status: str, progress: int) -> str:
        if status == "completed":
            return "已完成"
        if status == "failed":
            return "处理失败"
        if task_type in {"embedding", "embed"}:
            return f"正在向量化：{int(progress)}%"
        if task_type == "parse":
            return f"正在解析：{int(progress)}%"
        return f"处理中：{int(progress)}%"

