from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from backend.schemas.debug_chat import (
    DebugChatConversation,
    DebugChatCreateConversationRequest,
    DebugChatMessage,
    DebugChatRespondRequest,
    DebugChatRespondResponse,
)
from backend.services.chat_debug.service import DebugChatService

page_router = APIRouter(tags=["debug-chat-page"])
api_router = APIRouter(prefix="/debug", tags=["debug-chat"])

_DEBUG_CHAT_HTML = (
    Path(__file__).resolve().parents[2] / "web" / "templates" / "debug_chat.html"
)


def build_debug_chat_service(request: Request) -> DebugChatService:
    # Reuse the app-level engine/session factory so debug chat requests do not
    # pay remote database connection setup cost on every click.
    return DebugChatService(
        session_factory=request.app.state.session_factory,
        settings=request.app.state.settings,
    )


@page_router.get("/debug/chat", response_class=HTMLResponse)
def debug_chat_page() -> HTMLResponse:
    # The embedded page is a lightweight internal tool, so a static HTML shell
    # is enough and keeps the current FastAPI server self-contained.
    return HTMLResponse(_DEBUG_CHAT_HTML.read_text(encoding="utf-8"))


@api_router.get("/conversations", response_model=list[DebugChatConversation])
def list_debug_conversations(service: DebugChatService = Depends(build_debug_chat_service)):
    return service.list_conversations()


@api_router.post("/conversations", response_model=DebugChatConversation)
def create_debug_conversation(
    request: DebugChatCreateConversationRequest,
    service: DebugChatService = Depends(build_debug_chat_service),
):
    return service.create_conversation(title=request.title, user_id=request.user_id)


@api_router.get("/conversations/{conversation_id}/messages", response_model=list[DebugChatMessage])
def list_debug_conversation_messages(
    conversation_id: str,
    service: DebugChatService = Depends(build_debug_chat_service),
):
    return service.list_messages(int(conversation_id))


@api_router.post("/conversations/{conversation_id}/respond", response_model=DebugChatRespondResponse)
def respond_in_debug_conversation(
    conversation_id: str,
    request: DebugChatRespondRequest,
    service: DebugChatService = Depends(build_debug_chat_service),
):
    try:
        return service.respond(
            conversation_id=int(conversation_id),
            message=request.message,
            mode=request.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
