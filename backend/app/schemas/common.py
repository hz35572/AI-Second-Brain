from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    data: T


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None

