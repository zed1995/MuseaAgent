from datetime import datetime

from sqlalchemy import BigInteger, Integer, JSON, Text, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class SearchLogOrmModel(Base):
    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rewritten_queries: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retrieved_photo_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reranked_photo_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
