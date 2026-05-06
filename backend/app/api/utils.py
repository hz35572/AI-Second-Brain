from __future__ import annotations

import uuid

from fastapi import HTTPException, status


def ok(data) -> dict:  # noqa: ANN001
    return {"code": 0, "data": data}


def parse_uuid(value: str, *, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ERR_INVALID_ARGUMENT", "message": "参数错误", "details": {"field": field}},
        )

