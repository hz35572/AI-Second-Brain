from __future__ import annotations

from pydantic import BaseModel


class TaskProgressResponseData(BaseModel):
    task_id: str
    task_type: str
    status: str
    progress: int
    message: str

