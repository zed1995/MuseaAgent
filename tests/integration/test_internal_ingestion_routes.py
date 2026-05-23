import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings
from backend.core.id_generator import IdGenerator
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.indexing.embedding import StubEmbedder
from backend.services.indexing.pipeline import IndexingPipeline
from backend.services.indexing.scoring import StubScorer
from backend.services.indexing.semantic_enrichment import StubSemanticEnricher
from backend.services.indexing.translation import StubTranslator


@pytest.fixture
def test_pipeline(session):
    return IndexingPipeline(
        id_generator=IdGenerator(machine_id=1),
        translator=StubTranslator(),
        enricher=StubSemanticEnricher(),
        scorer=StubScorer(),
        embedder=StubEmbedder(),
        repository=PhotoIndexRepository(session),
    )


@pytest.fixture
def client(test_pipeline):
    settings = get_settings()
    app = create_app(settings)

    async def override_dependency():
        yield test_pipeline

    app.dependency_overrides = {}

    from backend.api.routes.internal_ingestion import router
    from backend.services.indexing.factory import build_indexing_pipeline

    app.dependency_overrides[build_indexing_pipeline] = override_dependency

    return TestClient(app)


def test_post_internal_ingestion_photo_returns_run_summary(client) -> None:
    response = client.post(
        "/api/internal/ingestion/photo",
        json={
            "payload": {
                "id": "photo-1",
                "description": "Dark mountain wallpaper",
                "alt_description": "Dark mountain wallpaper",
                "user": {"id": "user-1"},
                "width": 1920,
                "height": 1080,
                "urls": {"regular": "https://images.example/photo-1.jpg"},
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["unsplash_photo_id"] == "photo-1"
    assert body["search_text"] is not None


def test_post_internal_ingestion_photo_returns_422_on_missing_payload(client) -> None:
    response = client.post(
        "/api/internal/ingestion/photo",
        json={},
    )

    assert response.status_code == 422
    assert "field required" in response.text.lower() or "payload" in response.text.lower()


def test_post_internal_ingestion_cold_start(client) -> None:
    response = client.post(
        "/api/internal/ingestion/cold-start",
        json={
            "payloads": [
                {
                    "id": "photo-cs-1",
                    "description": "Cold start photo",
                    "user": {"id": "user-1"},
                    "urls": {"regular": "https://images.example/cs-1.jpg"},
                },
                {
                    "id": "photo-cs-2",
                    "description": "Another cold start photo",
                    "user": {"id": "user-1"},
                    "urls": {"regular": "https://images.example/cs-2.jpg"},
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["trigger_type"] == "cold_start"
    assert body["total_candidates"] == 2
    assert body["succeeded"] == 2
