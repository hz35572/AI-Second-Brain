from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import ok
from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.users import UserRepository
from app.schemas.auth import EmailVerificationCodeRequest, LoginRequest, RegisterRequest
from app.services.auth_service import AuthService
from app.services.email_verification_service import EmailVerificationService

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    token, user_id = await svc.register(
        email=payload.email,
        password=payload.password,
        name=payload.name,
        verification_code=payload.verification_code,
    )
    user = await UserRepository(db).get_by_id(user_id)
    await db.commit()
    settings = get_settings()
    expires_in = int(settings.jwt_expire_minutes) * 60
    return ok(
        {
            "token": token,
            "expires_in": expires_in,
            "user": {
                "id": str(user.id) if user else str(user_id),
                "email": user.email if user else payload.email,
                "name": user.name if user else payload.name,
            },
        }
    )


@router.post("/email-verification-code")
async def send_email_verification_code(payload: EmailVerificationCodeRequest, db: AsyncSession = Depends(get_db)):
    svc = EmailVerificationService(db)
    await svc.send_register_code(email=payload.email)
    await db.commit()
    return ok({"sent": True, "expires_in": get_settings().EMAIL_CODE_EXPIRE_MINUTES * 60})


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    token, user_id = await svc.login(email=payload.email, password=payload.password)
    user = await UserRepository(db).get_by_id(user_id)
    settings = get_settings()
    expires_in = int(settings.jwt_expire_minutes) * 60
    return ok(
        {
            "token": token,
            "expires_in": expires_in,
            "user": {
                "id": str(user.id) if user else str(user_id),
                "email": user.email if user else payload.email,
                "name": user.name if user else None,
            },
        }
    )
