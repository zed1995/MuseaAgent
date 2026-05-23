"""Phase 2 persistence foundation: photo_index, conversations, messages, search_logs.

Revision ID: 20260523_0001
Revises:
Create Date: 2026-05-23
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "20260523_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIMENSION = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "photo_index",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'unsplash'")),
        sa.Column("unsplash_photo_id", sa.Text(), nullable=False),
        sa.Column("unsplash_user_id", sa.Text(), nullable=True),
        sa.Column("orientation", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(VECTOR_DIMENSION), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("unsplash_photo_id", name="uq_photo_index_unsplash_photo_id"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conv_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_foreign_key(
        "fk_messages_conv_id",
        "messages", "conversations",
        ["conv_id"], ["id"],
    )

    op.create_table(
        "search_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("intent", sa.JSON(), nullable=True),
        sa.Column("rewritten_queries", sa.JSON(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("retrieved_photo_ids", sa.JSON(), nullable=True),
        sa.Column("reranked_photo_ids", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("request_id", name="uq_search_logs_request_id"),
    )

    op.create_index("ix_photo_index_unsplash_user_id", "photo_index", ["unsplash_user_id"])
    op.create_index("ix_photo_index_orientation", "photo_index", ["orientation"])
    op.create_index("ix_messages_conv_id", "messages", ["conv_id"])
    op.execute(
        "CREATE INDEX ix_photo_index_search_text_fts ON photo_index "
        "USING GIN (to_tsvector('english', search_text))"
    )
    op.execute(
        "CREATE INDEX ix_photo_index_embedding_hnsw ON photo_index "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_photo_index_embedding_hnsw", table_name="photo_index")
    op.execute("DROP INDEX IF EXISTS ix_photo_index_search_text_fts")
    op.drop_index("ix_messages_conv_id", table_name="messages")
    op.drop_index("ix_photo_index_orientation", table_name="photo_index")
    op.drop_index("ix_photo_index_unsplash_user_id", table_name="photo_index")
    op.drop_table("search_logs")
    op.drop_constraint("fk_messages_conv_id", "messages", type_="foreignkey")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("photo_index")
