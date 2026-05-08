from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


settings = get_settings()
_BCRYPT_PASSWORD_MAX_BYTES = 72


def _validate_bcrypt_password_length(password: str) -> None:
    if len(password.encode("utf-8")) > _BCRYPT_PASSWORD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "ERR_INVALID_ARGUMENT",
                "message": "password must be at most 72 UTF-8 bytes",
                "details": {},
            },
        )


def get_password_hash(password: str) -> str:
    _validate_bcrypt_password_length(password)
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    _validate_bcrypt_password_length(plain_password)
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
