from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


_BCRYPT_PASSWORD_MAX_BYTES = 72


def _validate_bcrypt_password_length(password: str) -> str:
    if len(password.encode("utf-8")) > _BCRYPT_PASSWORD_MAX_BYTES:
        raise ValueError(f"password must be at most {_BCRYPT_PASSWORD_MAX_BYTES} UTF-8 bytes")
    return password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_length_for_bcrypt(cls, value: str) -> str:
        return _validate_bcrypt_password_length(value)


class RegisterResponseData(BaseModel):
    user_id: str
    email: str
    name: str | None = None
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length_for_bcrypt(cls, value: str) -> str:
        return _validate_bcrypt_password_length(value)


class UserPublic(BaseModel):
    id: str
    email: str
    name: str | None = None


class LoginResponseData(BaseModel):
    token: str
    expires_in: int
    user: UserPublic
