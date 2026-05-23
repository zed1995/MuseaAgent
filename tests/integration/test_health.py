from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


def test_health_endpoint_returns_service_status() -> None:
    s = get_settings()
    s.indexing.mock_translation = True
    s.indexing.mock_enrichment = True
    s.indexing.mock_embedding = True
    client = TestClient(create_app(settings=s))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MuseaAgent API",
        "environment": "development",
    }
