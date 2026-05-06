from __future__ import annotations

from pydantic import BaseModel, Field


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: str | None = None


class FolderCreateResponseData(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    path: str


class FolderTreeNode(BaseModel):
    id: str
    name: str
    children: list["FolderTreeNode"] = Field(default_factory=list)
    file_count: int = 0


FolderTreeNode.model_rebuild()

