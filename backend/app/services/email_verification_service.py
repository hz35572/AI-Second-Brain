from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.email_verification_codes import EmailVerificationCodeRepository
from app.repositories.users import UserRepository
from app.services.email_service import EmailDeliveryError, EmailService


REGISTER_PURPOSE = "register"


class EmailVerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.codes = EmailVerificationCodeRepository(db)
        self.users = UserRepository(db)
        self.email_service = EmailService(self.settings)

    async def send_register_code(self, *, email: str) -> None:
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_EMAIL_EXISTS", "message": "邮箱已注册", "details": {}},
            )

        now = datetime.now(timezone.utc)
        latest = await self.codes.latest_for_email(email=email, purpose=REGISTER_PURPOSE)
        if latest and latest.created_at >= now - timedelta(seconds=self.settings.EMAIL_CODE_RESEND_INTERVAL_SECONDS):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "ERR_VERIFICATION_CODE_RATE_LIMITED", "message": "验证码发送过于频繁", "details": {}},
            )

        daily_count = await self.codes.count_created_since(
            email=email,
            purpose=REGISTER_PURPOSE,
            since=now - timedelta(days=1),
        )
        if daily_count >= self.settings.EMAIL_CODE_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "ERR_VERIFICATION_CODE_DAILY_LIMIT", "message": "今日验证码发送次数已达上限", "details": {}},
            )

        plain_code = f"{secrets.randbelow(1_000_000):06d}"
        record = await self.codes.create(
            email=email,
            purpose=REGISTER_PURPOSE,
            code_hash=self.hash_code(email=email, purpose=REGISTER_PURPOSE, code=plain_code),
            expires_at=now + timedelta(minutes=self.settings.EMAIL_CODE_EXPIRE_MINUTES),
            max_attempts=self.settings.EMAIL_CODE_MAX_ATTEMPTS,
        )

        try:
            self.email_service.send_register_code(
                to_email=email,
                code=plain_code,
                expires_minutes=self.settings.EMAIL_CODE_EXPIRE_MINUTES,
            )
        except EmailDeliveryError as exc:
            await self.codes.mark_failed(record, str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": "ERR_EMAIL_SEND_FAILED", "message": "验证码邮件发送失败", "details": {}},
            ) from exc

        await self.codes.mark_sent(record)

    async def verify_register_code(self, *, email: str, code: str) -> None:
        now = datetime.now(timezone.utc)
        latest = await self.codes.latest_unconsumed(email=email, purpose=REGISTER_PURPOSE)
        if latest is None:
            consumed_latest = await self.codes.latest_for_email(email=email, purpose=REGISTER_PURPOSE)
            if consumed_latest and consumed_latest.consumed_at is not None:
                if consumed_latest.attempt_count >= consumed_latest.max_attempts:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "ERR_VERIFICATION_CODE_ATTEMPTS_EXCEEDED",
                            "message": "验证码尝试次数已达上限",
                            "details": {},
                        },
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "ERR_VERIFICATION_CODE_USED", "message": "验证码已使用或已失效", "details": {}},
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_INVALID_VERIFICATION_CODE", "message": "验证码错误", "details": {}},
            )

        if latest.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_VERIFICATION_CODE_EXPIRED", "message": "验证码已过期", "details": {}},
            )
        if latest.attempt_count >= latest.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_VERIFICATION_CODE_ATTEMPTS_EXCEEDED", "message": "验证码尝试次数已达上限", "details": {}},
            )

        expected = self.hash_code(email=email, purpose=REGISTER_PURPOSE, code=code)
        if not hmac.compare_digest(expected, latest.code_hash):
            await self.codes.increment_attempts(latest)
            if latest.attempt_count >= latest.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "ERR_VERIFICATION_CODE_ATTEMPTS_EXCEEDED",
                        "message": "验证码尝试次数已达上限",
                        "details": {},
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_INVALID_VERIFICATION_CODE", "message": "验证码错误", "details": {}},
            )

        await self.codes.consume(latest, consumed_at=now)

    def hash_code(self, *, email: str, purpose: str, code: str) -> str:
        payload = f"{email.lower()}:{purpose}:{code}".encode("utf-8")
        return hmac.new(self.settings.SECRET_KEY.encode("utf-8"), payload, sha256).hexdigest()
