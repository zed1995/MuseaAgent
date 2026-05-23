from fastapi.testclient import TestClient

from backend.app import create_app


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MuseaAgent API",
        "environment": "development",
    }
