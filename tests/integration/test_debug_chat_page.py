from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


def test_debug_chat_page_renders_embedded_debug_ui() -> None:
    client = TestClient(create_app(settings=get_settings()))

    response = client.get("/debug/chat")

    assert response.status_code == 200
    assert "MuseaAgent Debug Chat" in response.text
    assert "/debug-assets/debug_chat.js" in response.text
    assert "No messages in this conversation yet." in response.text
    assert "Send one below to test the next turn." in response.text
    assert "Loading messages..." in response.text
    assert 'id="request-status"' in response.text
