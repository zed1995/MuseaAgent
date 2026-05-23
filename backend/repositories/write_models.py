from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PhotoIndexWriteModel:
    id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    source_text: str | None
    search_text: str
    ai_caption: str
    ai_short_caption: str
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
class ConversationWriteModel:
    id: int
    user_id: str | None
    title: str | None


@dataclass(slots=True)
class MessageWriteModel:
    id: int
    conv_id: int
    role: str
    content: str
    structured_data: dict | None = None
    metadata: dict | None = None


@dataclass(slots=True)
class SearchLogWriteModel:
    id: int
    request_id: str
    user_id: str | None
    query: str
