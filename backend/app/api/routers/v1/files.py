import uuid

from fastapi import APIRouter, Depends, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import ok, parse_uuid
from app.api.deps import get_current_user
from app.core.database import get_db
from app.repositories.files import FileRepository
from app.schemas.files import UploadInitRequest
from app.services.file_service import FileService

router = APIRouter()


@router.post("/upload", status_code=202)
async def upload_file(
    file: UploadFile,
    folder_id: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FileService(db)
    folder_uuid = parse_uuid(folder_id, field="folder_id") if folder_id else None
    data = await svc.upload_direct(user_id=current_user.id, upload=file, folder_id=folder_uuid)
    return ok(data)


@router.post("/upload/init")
async def init_multipart_upload(
    payload: UploadInitRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    folder_uuid = parse_uuid(payload.folder_id, field="folder_id") if payload.folder_id else None
    data = await FileService(db).init_multipart(
        user_id=current_user.id,
        file_name=payload.file_name,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        folder_id=folder_uuid,
    )
    return ok(data)


@router.put("/upload/{upload_id}/chunks/{chunk_index}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    data = await FileService(db).upload_chunk(
        user_id=current_user.id,
        upload_id=upload_id,
        chunk_index=chunk_index,
        body=body,
    )
    return ok(data)


@router.post("/upload/{upload_id}/complete", status_code=202)
async def complete_upload(
    upload_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await FileService(db).complete_multipart(user_id=current_user.id, upload_id=upload_id)
    return ok(data)


@router.get("")
async def list_files(
    folder_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    tag: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = tag  # reserved for V1.5
    folder_uuid = parse_uuid(folder_id, field="folder_id") if folder_id else None
    total, items = await FileRepository(db).list(
        user_id=current_user.id,
        folder_id=folder_uuid,
        status=status,
        page=max(1, page),
        page_size=min(100, max(1, page_size)),
    )
    out_items = [
        {
            "id": str(f.id),
            "name": f.name,
            "file_size": int(f.file_size),
            "mime_type": f.mime_type,
            "page_count": int(f.page_count or 0),
            "summary": f.summary,
            "tags": [],
            "status": f.status,
            "created_at": f.created_at.isoformat(),
        }
        for f in items
    ]
    return ok({"total": total, "items": out_items})
