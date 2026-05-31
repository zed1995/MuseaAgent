from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


class StubDebugChatService:
    def __init__(self) -> None:
        self._messages = {
            "9001": [
                {
                    "id": "1001",
                    "conversation_id": "9001",
                    "role": "user",
                    "content": "先给我深色壁纸",
                    "created_at": "2026-05-31T12:00:00Z",
                    "structured_data": None,
                    "metadata": None,
                },
                {
                    "id": "1002",
                    "conversation_id": "9001",
                    "role": "assistant",
                    "content": "这是第一轮结果。",
                    "created_at": "2026-05-31T12:00:01Z",
                    "structured_data": {"agent": {"mode": "wallpaper"}},
                    "metadata": None,
                },
            ]
        }

    def list_conversations(self):
        return [
            {
                "id": "9001",
                "title": "深色壁纸",
                "user_id": None,
                "message_count": 2,
                "created_at": "2026-05-31T12:00:00Z",
                "updated_at": "2026-05-31T12:00:01Z",
            }
        ]

    def create_conversation(self, *, title=None, user_id=None):
        return {
            "id": "9002",
            "title": title,
            "user_id": user_id,
            "message_count": 0,
            "created_at": "2026-05-31T12:05:00Z",
            "updated_at": "2026-05-31T12:05:00Z",
        }

    def list_messages(self, conversation_id: int):
        return self._messages.get(str(conversation_id), [])

    def respond(self, *, conversation_id: int, message: str, mode: str):
        conversation_id = str(conversation_id)
        assistant = {
            "id": "1004",
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": "我把结果往更安静的方向放宽了一点。",
            "created_at": "2026-05-31T12:06:01Z",
            "structured_data": {
                "agent": {
                    "mode": "wallpaper",
                    "topic_action": "refine",
                    "search_spec_ids": ["balanced-1"],
                    "critic_reason_code": "ok",
                    "retry_count": 1,
                },
                "retrieval": {
                    "final_items": [
                        {"unsplash_photo_id": "photo-1", "source_spec_id": "balanced-1"}
                    ]
                },
            },
            "metadata": None,
        }
        self._messages.setdefault(conversation_id, []).extend(
            [
                {
                    "id": "1003",
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": message,
                    "created_at": "2026-05-31T12:06:00Z",
                    "structured_data": None,
                    "metadata": None,
                },
                assistant,
            ]
        )
        return {
            "conversation": {
                "id": conversation_id,
                "title": "深色壁纸",
                "user_id": None,
                "message_count": len(self._messages[conversation_id]),
                "created_at": "2026-05-31T12:00:00Z",
                "updated_at": "2026-05-31T12:06:01Z",
            },
            "assistant_message": assistant,
            "debug": assistant["structured_data"]["agent"],
        }


def test_debug_chat_api_supports_minimal_multi_turn_flow() -> None:
    app = create_app(settings=get_settings())

    from backend.api.routes.debug_chat import build_debug_chat_service

    stub_service = StubDebugChatService()
    app.dependency_overrides[build_debug_chat_service] = lambda: stub_service

    client = TestClient(app)

    create_response = client.post("/api/debug/conversations", json={"title": "深色壁纸"})
    assert create_response.status_code == 200
    assert create_response.json()["id"] == "9002"

    list_response = client.get("/api/debug/conversations")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == "9001"

    respond_response = client.post(
        "/api/debug/conversations/9001/respond",
        json={"message": "再安静一点，不要人物", "mode": "auto"},
    )
    assert respond_response.status_code == 200
    payload = respond_response.json()
    assert payload["assistant_message"]["role"] == "assistant"
    assert isinstance(payload["assistant_message"]["id"], str)
    assert payload["debug"]["retry_count"] == 1
    assert payload["debug"]["search_spec_ids"] == ["balanced-1"]

    messages_response = client.get("/api/debug/conversations/9001/messages")
    assert messages_response.status_code == 200
    assert isinstance(messages_response.json()[0]["id"], str)
    assert messages_response.json()[-1]["content"] == "我把结果往更安静的方向放宽了一点。"


def test_debug_chat_app_reuses_one_session_factory_per_app(monkeypatch) -> None:
    counters = {"engine": 0, "session_factory": 0}

    class StubEngine:
        def dispose(self) -> None:
            return None

    def _build_engine(settings):
        counters["engine"] += 1
        return StubEngine()

    def _build_session_factory(engine):
        counters["session_factory"] += 1
        return object()

    monkeypatch.setattr("backend.app.create_engine_from_settings", _build_engine)
    monkeypatch.setattr("backend.app.create_session_factory", _build_session_factory)

    app = create_app(settings=get_settings())

    from backend.api.routes.debug_chat import build_debug_chat_service

    app.dependency_overrides[build_debug_chat_service] = lambda: StubDebugChatService()

    client = TestClient(app)
    client.get("/api/debug/conversations")
    client.get("/api/debug/conversations/9001/messages")

    assert counters["engine"] == 1
    assert counters["session_factory"] == 1
