from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PhotoIndexRecord:
    id: int
    source: str
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    source_text: str | None
    search_text: str
    status: str
    last_error: str | None
    indexed_at: datetime | None = None


@dataclass(slots=True)
class ConversationRecord:
    id: int
    user_id: str | None
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class MessageRecord:
    id: int
    conv_id: int
    role: str
    content: str
    structured_data: dict | None
    metadata: dict | None
    created_at: datetime


@dataclass(slots=True)
class SearchLogRecord:
    id: int
    request_id: str
    user_id: str | None
    query: str
    intent: dict | None
    rewritten_queries: dict | None
    filters: dict | None
    retrieved_photo_ids: dict | None
    reranked_photo_ids: dict | None
    latency_ms: int | None
    result_count: int | None
    created_at: datetime
