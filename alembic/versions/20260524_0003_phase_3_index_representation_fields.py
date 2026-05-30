"""Phase 3 index representation fields for richer retrieval execution.

Revision ID: 20260524_0003
Revises: 20260523_0002
Create Date: 2026-05-24
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260524_0003"
down_revision: str | None = "20260523_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "photo_index",
        sa.Column("retrieval_caption_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "photo_index",
        sa.Column("retrieval_tag_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "photo_index",
        sa.Column("retrieval_document_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "photo_index",
        sa.Column("embedding_text", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("photo_index", "embedding_text")
    op.drop_column("photo_index", "retrieval_document_text")
    op.drop_column("photo_index", "retrieval_tag_text")
    op.drop_column("photo_index", "retrieval_caption_text")
