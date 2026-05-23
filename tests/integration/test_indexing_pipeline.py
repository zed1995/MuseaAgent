from dataclasses import dataclass

import pytest

from backend.core.config import get_settings
from backend.core.id_generator import IdGenerator
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.services.indexing.contracts import SemanticArtifacts
from backend.services.indexing.embedding import Embedder
from backend.services.indexing.scoring import Scorer
from backend.services.indexing.semantic_enrichment import SemanticEnricher
from backend.services.indexing.translation import Translator


@pytest.fixture
def settings():
    return get_settings()


class FakeTranslator(Translator):
    def to_search_text(self, *, analysis_text: str) -> str:
        return analysis_text.strip().lower()


class FakeSemanticEnricher(SemanticEnricher):
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts:
        return SemanticArtifacts(
            ai_caption=f"A {search_text}.",
            ai_short_caption=search_text,
            scene_tags=["mountain"],
            mood_tags=["calm"],
            style_tags=["minimal"],
            wallpaper_score=0.9,
        )


class FakeScorer(Scorer):
    def score(self, *, semantic_artifacts: SemanticArtifacts) -> SemanticArtifacts:
        return semantic_artifacts


class FakeEmbedder(Embedder):
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]:
        return [0.1] * 1536


@dataclass
class FakeServices:
    translator: Translator
    enricher: SemanticEnricher
    scorer: Scorer
    embedder: Embedder
    repository: PhotoIndexRepository


@pytest.fixture
def fake_services(session):
    return FakeServices(
        translator=FakeTranslator(),
        enricher=FakeSemanticEnricher(),
        scorer=FakeScorer(),
        embedder=FakeEmbedder(),
        repository=PhotoIndexRepository(session),
    )


# Lazy import to allow pipeline module creation after test collection
@pytest.fixture
def pipeline(fake_services):
    from backend.services.indexing.pipeline import IndexingPipeline

    return IndexingPipeline(
        id_generator=IdGenerator(machine_id=1),
        translator=fake_services.translator,
        enricher=fake_services.enricher,
        scorer=fake_services.scorer,
        embedder=fake_services.embedder,
        repository=fake_services.repository,
    )


def test_indexing_pipeline_builds_completed_index_entry(pipeline) -> None:
    payload = {
        "id": "photo-1",
        "description": "Quiet dark mountain wallpaper",
        "alt_description": "Dark mountain wallpaper",
        "user": {"id": "user-1"},
        "width": 1920,
        "height": 1080,
        "urls": {"regular": "https://images.example/photo-1.jpg"},
    }

    record = pipeline.process_photo(payload)

    assert record.unsplash_photo_id == "photo-1"
    assert record.search_text is not None
    assert "quiet" in record.search_text
    assert record.ai_caption is not None
    assert record.embedding is not None


def test_indexing_pipeline_handles_payload_without_user(fake_services) -> None:
    from backend.services.indexing.pipeline import IndexingPipeline

    pipeline = IndexingPipeline(
        id_generator=IdGenerator(machine_id=1),
        translator=fake_services.translator,
        enricher=fake_services.enricher,
        scorer=fake_services.scorer,
        embedder=fake_services.embedder,
        repository=fake_services.repository,
    )
    payload = {
        "id": "photo-2",
        "user": None,
        "urls": {"regular": "https://images.example/photo-2.jpg"},
    }

    record = pipeline.process_photo(payload)

    assert record.unsplash_photo_id == "photo-2"
    assert record.search_text is not None


def test_build_indexing_pipeline_returns_pipeline_with_configured_adapters(session_factory, settings) -> None:
    from backend.services.indexing.factory import build_indexing_pipeline

    pipeline = build_indexing_pipeline(session_factory=session_factory, settings=settings)

    assert pipeline is not None
    assert pipeline.translator is not None
    assert pipeline.enricher is not None
    assert pipeline.embedder is not None
