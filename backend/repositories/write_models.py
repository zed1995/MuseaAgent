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
    embedding: list[float] | None
    status: str


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
