from datetime import datetime

from pydantic import BaseModel


class DebugChatConversation(BaseModel):
    id: str
    title: str | None = None
    user_id: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class DebugChatMessage(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    structured_data: dict | None = None
    metadata: dict | None = None


class DebugChatCreateConversationRequest(BaseModel):
    title: str | None = None
    user_id: str | None = None


class DebugChatRespondRequest(BaseModel):
    message: str
    mode: str = "auto"


class DebugChatRespondResponse(BaseModel):
    conversation: DebugChatConversation
    assistant_message: DebugChatMessage
    debug: dict | None = None
