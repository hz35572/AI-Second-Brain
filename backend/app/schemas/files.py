from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponseData(BaseModel):
    file_id: str
    task_id: str
    status: str


class UploadInitRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(ge=1)
    mime_type: str | None = None
    folder_id: str | None = None


class UploadInitResponseData(BaseModel):
    upload_id: str
    chunk_size: int
    total_chunks: int


class FileListItem(BaseModel):
    id: str
    name: str
    file_size: int
    mime_type: str | None = None
    page_count: int = 0
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str
    created_at: str


class FileListResponseData(BaseModel):
    total: int
    items: list[FileListItem]

