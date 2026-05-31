from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


def test_health_endpoint_returns_service_status() -> None:
    s = get_settings()
    s.indexing.mock_translation = True
    s.indexing.mock_enrichment = True
    s.indexing.mock_embedding = True
    s.retrieval.enable_debug_endpoint = False
    client = TestClient(create_app(settings=s))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MuseaAgent API",
        "environment": "development",
        "debug_search_enabled": False,
    }


def test_app_lifespan_warms_database_connection(monkeypatch) -> None:
    calls = {"connect": 0, "execute": 0, "close": 0, "dispose": 0}

    class StubConnection:
        def execute(self, statement) -> None:
            calls["execute"] += 1

        def close(self) -> None:
            calls["close"] += 1

    class StubEngine:
        def connect(self):
            calls["connect"] += 1
            return StubConnection()

        def dispose(self) -> None:
            calls["dispose"] += 1

    monkeypatch.setattr("backend.app.create_engine_from_settings", lambda settings: StubEngine())
    monkeypatch.setattr("backend.app.create_session_factory", lambda engine: object())

    with TestClient(create_app(settings=get_settings())):
        pass

    assert calls["connect"] == 1
    assert calls["execute"] == 1
    assert calls["close"] == 1
    assert calls["dispose"] == 1
