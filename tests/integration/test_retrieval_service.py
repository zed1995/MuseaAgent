import pytest
from unittest.mock import Mock

from backend.services.retrieval.service import RetrievalService, RetrievalFailedError
from backend.services.retrieval.query_normalization import QueryNormalizationService
from backend.services.retrieval.rerank import RetrievalReranker
from backend.core.settings_models import RetrievalSettings


class FakeEmbedder:
    def __call__(self, text: str) -> list[float]:
        return [0.0] * 1536


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_retrieval_service_returns_ranked_results_for_chinese_wallpaper_query(session) -> None:
    from backend.repositories.photo_index_repository import PhotoIndexRepository
    repository = PhotoIndexRepository(session)
    service = RetrievalService(
        repository=repository,
        normalizer=QueryNormalizationService(),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(
        query="我想找深色安静的 OLED 壁纸，不要人物",
        mode="wallpaper",
        limit=5,
    )

    assert response.items
    assert response.applied_filters.has_human is False
    assert response.trace.vector_candidate_count > 0
    assert response.trace.fts_candidate_count > 0


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_retrieval_service_falls_back_to_fts_when_vector_path_errors(session) -> None:
    from backend.repositories.photo_index_repository import PhotoIndexRepository
    repository = PhotoIndexRepository(session)

    def failing_embedder(text: str) -> list[float]:
        raise RuntimeError("embedding failed")

    service = RetrievalService(
        repository=repository,
        normalizer=QueryNormalizationService(),
        embedder=failing_embedder,
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(
        query="深色壁纸",
        mode="wallpaper",
        limit=5,
    )

    assert response.items
    assert "vector_path_failed" in response.trace.dropped_candidate_reasons


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_retrieval_service_raises_on_dual_failure(session) -> None:
    from backend.repositories.photo_index_repository import PhotoIndexRepository
    repository = Mock()
    repository.search_vector.side_effect = RuntimeError("vector failed")
    repository.search_full_text.side_effect = RuntimeError("fts failed")

    service = RetrievalService(
        repository=repository,
        normalizer=QueryNormalizationService(),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    with pytest.raises(RetrievalFailedError):
        service.retrieve(query="test", mode="auto", limit=5)
