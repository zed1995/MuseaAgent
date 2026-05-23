from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Text, TIMESTAMP, text
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
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
