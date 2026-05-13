from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_verification_code import EmailVerificationCode


class EmailVerificationCodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        email: str,
        purpose: str,
        code_hash: str,
        expires_at: datetime,
        max_attempts: int,
    ) -> EmailVerificationCode:
        code = EmailVerificationCode(
            email=email,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=expires_at,
            max_attempts=max_attempts,
        )
        self.db.add(code)
        await self.db.flush()
        return code

    async def latest_for_email(self, *, email: str, purpose: str) -> EmailVerificationCode | None:
        res = await self.db.execute(
            select(EmailVerificationCode)
            .where(EmailVerificationCode.email == email, EmailVerificationCode.purpose == purpose)
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def latest_unconsumed(self, *, email: str, purpose: str) -> EmailVerificationCode | None:
        res = await self.db.execute(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def count_created_since(self, *, email: str, purpose: str, since: datetime) -> int:
        res = await self.db.execute(
            select(func.count(EmailVerificationCode.id)).where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.created_at >= since,
            )
        )
        return int(res.scalar_one())

    async def mark_sent(self, code: EmailVerificationCode) -> None:
        code.send_status = "sent"
        code.last_error = None
        code.updated_at = datetime.now(tz=code.expires_at.tzinfo)
        await self.db.flush()

    async def mark_failed(self, code: EmailVerificationCode, error: str) -> None:
        code.send_status = "failed"
        code.last_error = error[:1000]
        code.updated_at = datetime.now(tz=code.expires_at.tzinfo)
        await self.db.flush()

    async def increment_attempts(self, code: EmailVerificationCode) -> None:
        code.attempt_count += 1
        if code.attempt_count >= code.max_attempts:
            code.consumed_at = datetime.now(tz=code.expires_at.tzinfo)
        code.updated_at = datetime.now(tz=code.expires_at.tzinfo)
        await self.db.flush()

    async def consume(self, code: EmailVerificationCode, *, consumed_at: datetime) -> None:
        code.consumed_at = consumed_at
        code.updated_at = consumed_at
        await self.db.flush()
