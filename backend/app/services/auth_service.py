import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)

    async def register(self, *, email: str, password: str, name: str | None) -> tuple[uuid.UUID, str]:
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_EMAIL_EXISTS", "message": "邮箱已注册", "details": {}},
            )
        user = await self.users.create(email=email, password_hash=get_password_hash(password), name=name)
        token = create_access_token(str(user.id))
        return user.id, token

    async def login(self, *, email: str, password: str) -> tuple[str, uuid.UUID]:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "ERR_INVALID_CREDENTIALS", "message": "邮箱或密码错误", "details": {}},
            )
        token = create_access_token(str(user.id))
        return token, user.id

