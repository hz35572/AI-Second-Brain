"""add email verification codes

Revision ID: 0002_email_verification_codes
Revises: 0001_init
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_email_verification_codes"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("send_status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(
        "idx_email_verification_codes_email_purpose_created",
        "email_verification_codes",
        ["email", "purpose", "created_at"],
    )
    op.create_index(
        "idx_email_verification_codes_email_purpose_active",
        "email_verification_codes",
        ["email", "purpose", "expires_at"],
        postgresql_where=sa.text("consumed_at IS NULL"),
    )
    op.create_index("idx_email_verification_codes_expires_at", "email_verification_codes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_email_verification_codes_expires_at", table_name="email_verification_codes")
    op.drop_index("idx_email_verification_codes_email_purpose_active", table_name="email_verification_codes")
    op.drop_index("idx_email_verification_codes_email_purpose_created", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")
