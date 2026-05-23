"""Phase 3 ingestion write path: add completed enrichment fields to photo_index.

Revision ID: 20260523_0002
Revises: 20260523_0001
Create Date: 2026-05-23
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260523_0002"
down_revision: str | None = "20260523_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new completed-record enrichment columns
    op.add_column("photo_index", sa.Column("ai_caption", sa.Text(), nullable=False))
    op.add_column("photo_index", sa.Column("ai_short_caption", sa.Text(), nullable=False))
    op.add_column("photo_index", sa.Column("scene_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("mood_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("style_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("composition_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("lighting_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("color_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("subject_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("use_case_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("dominant_colors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("photo_index", sa.Column("has_human", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("photo_index", sa.Column("has_face", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("photo_index", sa.Column("is_abstract", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("photo_index", sa.Column("is_minimal", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("photo_index", sa.Column("is_dark", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("photo_index", sa.Column("wallpaper_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("photo_index", sa.Column("photography_reference_score", sa.Float(), nullable=False, server_default="0"))

    # Remove Phase 2 process-state coupling
    op.drop_column("photo_index", "last_error")
    op.alter_column("photo_index", "status", new_column_name="index_status")


def downgrade() -> None:
    op.alter_column("photo_index", "index_status", new_column_name="status")
    op.add_column("photo_index", sa.Column("last_error", sa.Text(), nullable=True))

    op.drop_column("photo_index", "photography_reference_score")
    op.drop_column("photo_index", "wallpaper_score")
    op.drop_column("photo_index", "is_dark")
    op.drop_column("photo_index", "is_minimal")
    op.drop_column("photo_index", "is_abstract")
    op.drop_column("photo_index", "has_face")
    op.drop_column("photo_index", "has_human")
    op.drop_column("photo_index", "dominant_colors")
    op.drop_column("photo_index", "use_case_tags")
    op.drop_column("photo_index", "subject_tags")
    op.drop_column("photo_index", "color_tags")
    op.drop_column("photo_index", "lighting_tags")
    op.drop_column("photo_index", "composition_tags")
    op.drop_column("photo_index", "style_tags")
    op.drop_column("photo_index", "mood_tags")
    op.drop_column("photo_index", "scene_tags")
    op.drop_column("photo_index", "ai_short_caption")
    op.drop_column("photo_index", "ai_caption")
