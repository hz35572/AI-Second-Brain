import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    send_status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("5"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


Index(
    "idx_email_verification_codes_email_purpose_created",
    EmailVerificationCode.email,
    EmailVerificationCode.purpose,
    EmailVerificationCode.created_at,
)
Index("idx_email_verification_codes_expires_at", EmailVerificationCode.expires_at)
Index(
    "idx_email_verification_codes_email_purpose_active",
    EmailVerificationCode.email,
    EmailVerificationCode.purpose,
    EmailVerificationCode.expires_at,
    postgresql_where=EmailVerificationCode.consumed_at.is_(None),
)
