from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, Float, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

VECTOR_DIMENSION = 1536


class PhotoIndexOrmModel(Base):
    __tablename__ = "photo_index"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unsplash'"))
    unsplash_photo_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    unsplash_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    orientation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(VECTOR_DIMENSION), nullable=True)
    index_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))

    # Phase 3 completed-record enrichment fields
    ai_caption: Mapped[str] = mapped_column(Text, nullable=False)
    ai_short_caption: Mapped[str] = mapped_column(Text, nullable=False)
    scene_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    mood_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    style_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    composition_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    lighting_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    color_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    subject_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    use_case_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    dominant_colors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    has_human: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_face: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_abstract: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_minimal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_dark: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wallpaper_score: Mapped[float] = mapped_column(Float, nullable=False)
    photography_reference_score: Mapped[float] = mapped_column(Float, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
