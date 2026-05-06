from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.utils import ok, parse_uuid
from app.core.database import get_db
from app.services.task_service import TaskService

router = APIRouter()


@router.get("/{task_id}/progress")
async def get_progress(task_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task_uuid = parse_uuid(task_id, field="task_id")
    data = await TaskService(db).get_progress(user_id=current_user.id, task_id=task_uuid)
    return ok(data)
