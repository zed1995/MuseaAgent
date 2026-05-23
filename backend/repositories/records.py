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
    index_status: str
    ai_caption: str | None = None
    ai_short_caption: str | None = None
    scene_tags: list[str] | None = None
    mood_tags: list[str] | None = None
    style_tags: list[str] | None = None
    composition_tags: list[str] | None = None
    lighting_tags: list[str] | None = None
    color_tags: list[str] | None = None
    subject_tags: list[str] | None = None
    use_case_tags: list[str] | None = None
    dominant_colors: list[str] | None = None
    has_human: bool = False
    has_face: bool = False
    is_abstract: bool = False
    is_minimal: bool = False
    is_dark: bool = False
    wallpaper_score: float = 0.0
    photography_reference_score: float = 0.0
    embedding: list[float] | None = None
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
class PhotoRetrievalCandidate:
    id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    search_text: str
    ai_caption: str
    has_human: bool
    wallpaper_score: float
    photography_reference_score: float
    vector_score: float = 0.0
    fts_score: float = 0.0


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
