from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.utils import ok, parse_uuid
from app.core.database import get_db
from app.schemas.folders import FolderCreateRequest
from app.services.folder_service import FolderService

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent_uuid = parse_uuid(payload.parent_id, field="parent_id") if payload.parent_id else None
    data = await FolderService(db).create_folder(user_id=current_user.id, name=payload.name, parent_id=parent_uuid)
    return ok(data)


@router.get("/tree")
async def get_folder_tree(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await FolderService(db).folder_tree(user_id=current_user.id)
    return ok(data)
