"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-04-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100)),
        sa.Column("avatar_url", sa.String(length=500)),
        sa.Column("deployment_mode", sa.String(length=20), server_default=sa.text("'cloud'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("idx_users_email", "users", ["email"])

    op.create_table(
        "folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1000), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE", name="fk_folders_parent_id_folders"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_folders_user_id_users"),
    )
    op.create_index("idx_folders_user", "folders", ["user_id"])
    op.create_index("idx_folders_parent", "folders", ["parent_id"])
    op.create_index("idx_folders_path", "folders", ["path"])

    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255)),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100)),
        sa.Column("sha256", sa.String(length=64)),
        sa.Column("page_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("upload_progress", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="SET NULL", name="fk_files_folder_id_folders"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_files_user_id_users"),
    )
    op.create_index("idx_files_user", "files", ["user_id"])
    op.create_index("idx_files_folder", "files", ["folder_id"])
    op.create_index("idx_files_status", "files", ["status"])
    op.create_index("idx_files_sha256", "files", ["sha256"])

    op.create_table(
        "file_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("start_pos", sa.Integer()),
        sa.Column("end_pos", sa.Integer()),
        sa.Column("locator", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("token_count", sa.Integer()),
        sa.Column("vector_id", sa.String(length=100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE", name="fk_file_chunks_file_id_files"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_file_chunks_user_id_users"),
        sa.UniqueConstraint("file_id", "chunk_index", name="idx_chunks_file_chunk_index"),
    )
    op.create_index("idx_chunks_file", "file_chunks", ["file_id"])
    op.create_index("idx_chunks_user", "file_chunks", ["user_id"])

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2)),
        sa.Column("source", sa.String(length=20), server_default=sa.text("'ai'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE", name="fk_tags_file_id_files"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_tags_user_id_users"),
        sa.UniqueConstraint("user_id", "file_id", "name", name="idx_tags_user_file_name"),
    )
    op.create_index("idx_tags_name", "tags", ["name"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255)),
        sa.Column("scope_type", sa.String(length=20), server_default=sa.text("'global'"), nullable=False),
        sa.Column("scope_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("model_provider", sa.String(length=50)),
        sa.Column("model_name", sa.String(length=100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_conversations_user_id_users"),
    )
    op.create_index("idx_conversations_user", "conversations", ["user_id"])
    op.create_index(
        "idx_conversations_scope_ids",
        "conversations",
        ["scope_ids"],
        postgresql_using="gin",
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE", name="fk_messages_conversation_id_conversations"
        ),
    )
    op.create_index("idx_messages_conv", "messages", ["conversation_id"])
    op.create_index("idx_messages_created", "messages", ["created_at"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("related_file_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("progress", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["related_file_id"], ["files.id"], ondelete="SET NULL", name="fk_tasks_related_file_id_files"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_tasks_user_id_users"),
    )
    op.create_index("idx_tasks_user", "tasks", ["user_id"])
    op.create_index("idx_tasks_status", "tasks", ["status"])
    op.create_index("idx_tasks_file", "tasks", ["related_file_id"])


def downgrade() -> None:
    op.drop_index("idx_tasks_file", table_name="tasks")
    op.drop_index("idx_tasks_status", table_name="tasks")
    op.drop_index("idx_tasks_user", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("idx_messages_created", table_name="messages")
    op.drop_index("idx_messages_conv", table_name="messages")
    op.drop_table("messages")

    op.drop_index("idx_conversations_scope_ids", table_name="conversations")
    op.drop_index("idx_conversations_user", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("idx_tags_name", table_name="tags")
    op.drop_table("tags")

    op.drop_index("idx_chunks_user", table_name="file_chunks")
    op.drop_index("idx_chunks_file", table_name="file_chunks")
    op.drop_table("file_chunks")

    op.drop_index("idx_files_sha256", table_name="files")
    op.drop_index("idx_files_status", table_name="files")
    op.drop_index("idx_files_folder", table_name="files")
    op.drop_index("idx_files_user", table_name="files")
    op.drop_table("files")

    op.drop_index("idx_folders_path", table_name="folders")
    op.drop_index("idx_folders_parent", table_name="folders")
    op.drop_index("idx_folders_user", table_name="folders")
    op.drop_table("folders")

    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")

