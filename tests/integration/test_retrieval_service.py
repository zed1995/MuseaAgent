import pytest
from unittest.mock import Mock

from backend.repositories.records import PhotoRetrievalCandidate
from backend.services.retrieval.service import RetrievalService, RetrievalFailedError
from backend.services.retrieval.rerank import RetrievalReranker
from backend.core.settings_models import RetrievalSettings
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService
from backend.services.retrieval_preparation.service import (
    RetrievalPreparationError,
    RetrievalPreparationService,
)
from backend.services.retrieval_preparation.understanding import QueryUnderstandingService


class FakeEmbedder:
    def __call__(self, text: str) -> list[float]:
        return [0.0] * 1536


class FailingRewriteService:
    def rewrite(self, understanding):
        raise RuntimeError("rewrite failed")


class EmptyRewriteService:
    def rewrite(self, understanding):
        from backend.services.retrieval_preparation.contracts import RetrievalRewriteResult

        return RetrievalRewriteResult(
            rewrite_for_embedding=" ",
            rewrite_for_fts=" ",
            lexical_terms=[],
            user_explicit_terms=[],
            expansion_terms=[],
            negative_terms=[],
            rewrite_notes=["model returned empty rewrites"],
        )


class EmptyStructuredUnderstandingService:
    def understand(self, query, mode, explicit_filters=None):
        from backend.services.retrieval_preparation.contracts import QueryUnderstandingResult

        return QueryUnderstandingResult(
            raw_query=query,
            detected_language="zh",
            inferred_mode="generic",
        )


class FailingUnderstandingService:
    def understand(self, query, mode, explicit_filters=None):
        raise RuntimeError("understanding failed")


class InvalidJsonUnderstandingService:
    def understand(self, query, mode, explicit_filters=None):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


def _understanding_service():
    return QueryUnderstandingService(
        model_client=lambda query, mode: {
            "raw_query": query,
            "detected_language": "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in query) else "en",
            "inferred_mode": "wallpaper" if mode in {"auto", "wallpaper"} else mode,
            "hard_filters": {"orientation": None, "has_human": False if "不要人物" in query else None},
            "negative_constraints": {"exclude_people": "不要人物" in query, "exclude_faces": False},
            "soft_preferences": {"colors": ["dark"] if "深色" in query else [], "moods": ["calm"] if "安静" in query else [], "qualities": ["oled"] if "OLED" in query or "oled" in query.lower() else []},
            "understanding_notes": ["stub understanding"],
        }
    )


class FakeRepository:
    def __init__(
        self,
        *,
        vector_candidates: list[PhotoRetrievalCandidate] | None = None,
        fts_candidates: list[PhotoRetrievalCandidate] | None = None,
    ) -> None:
        self._vector_candidates = vector_candidates or []
        self._fts_candidates = fts_candidates or []

    def search_vector(self, **kwargs) -> list[PhotoRetrievalCandidate]:
        return list(self._vector_candidates)

    def search_full_text(self, **kwargs) -> list[PhotoRetrievalCandidate]:
        return list(self._fts_candidates)


def _candidate(
    *,
    id: int,
    photo_id: str,
    orientation: str = "portrait",
    has_human: bool = False,
    search_text: str = "dark calm oled wallpaper",
    retrieval_caption_text: str = "Dark calm wallpaper",
    retrieval_tag_text: str = "dark calm oled wallpaper minimal",
    vector_score: float = 0.0,
    fts_score: float = 0.0,
    wallpaper_score: float = 0.9,
    photography_reference_score: float = 0.3,
    has_face: bool = False,
    is_dark: bool = False,
    is_minimal: bool = False,
    scene_tags: list[str] | None = None,
    style_tags: list[str] | None = None,
    color_tags: list[str] | None = None,
    subject_tags: list[str] | None = None,
    use_case_tags: list[str] | None = None,
) -> PhotoRetrievalCandidate:
    return PhotoRetrievalCandidate(
        id=id,
        unsplash_photo_id=photo_id,
        unsplash_user_id=None,
        orientation=orientation,
        search_text=search_text,
        ai_caption="A dark calm wallpaper.",
        has_human=has_human,
        wallpaper_score=wallpaper_score,
        photography_reference_score=photography_reference_score,
        retrieval_caption_text=retrieval_caption_text,
        retrieval_tag_text=retrieval_tag_text,
        has_face=has_face,
        is_dark=is_dark,
        is_minimal=is_minimal,
        scene_tags=scene_tags,
        style_tags=style_tags,
        color_tags=color_tags,
        subject_tags=subject_tags,
        use_case_tags=use_case_tags,
        vector_score=vector_score,
        fts_score=fts_score,
    )


def test_retrieval_service_returns_ranked_results_for_chinese_wallpaper_query() -> None:
    repository = FakeRepository(
        vector_candidates=[_candidate(id=1, photo_id="vector-hit", vector_score=0.0)],
        fts_candidates=[_candidate(id=1, photo_id="vector-hit", fts_score=0.7)],
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=RetrievalRewriteService(),
        ),
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
    assert response.trace.vector_candidate_count == 1
    assert response.trace.fts_candidate_count > 0
    assert "vector_path_failed" not in response.trace.dropped_candidate_reasons
    assert response.trace.rewrite_for_embedding
    assert response.trace.rewrite_for_fts
    assert response.trace.user_explicit_terms
    assert response.trace.fallback_path is None
    assert response.trace.representation_bundle_used is True
    assert response.trace.fts_document_version == "multi_field_weighted_v1"
    assert "structured_phase_3_signals" in response.trace.rerank_features_used


def test_retrieval_service_falls_back_to_fts_when_vector_path_errors() -> None:
    def failing_embedder(text: str) -> list[float]:
        raise RuntimeError("embedding failed")

    repository = FakeRepository(
        fts_candidates=[_candidate(id=2, photo_id="fts-hit", fts_score=0.9)]
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=RetrievalRewriteService(),
        ),
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


def test_retrieval_service_raises_on_dual_failure() -> None:
    repository = Mock()
    repository.search_vector.side_effect = RuntimeError("vector failed")
    repository.search_full_text.side_effect = RuntimeError("fts failed")

    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    with pytest.raises(RetrievalFailedError):
        service.retrieve(query="test", mode="auto", limit=5)


def test_retrieval_service_uses_rewrite_fallback_when_rewrite_pass_fails() -> None:
    repository = FakeRepository(
        fts_candidates=[_candidate(id=3, photo_id="fallback-hit", fts_score=0.8)]
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=FailingRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(query="深色壁纸 不要人物", mode="wallpaper", limit=5)

    assert response.items
    assert response.trace.fallback_path == "rewrite"


def test_retrieval_service_uses_rewrite_fallback_when_rewrite_pass_returns_empty_values(
    caplog,
) -> None:
    repository = FakeRepository(
        fts_candidates=[_candidate(id=4, photo_id="empty-rewrite-hit", fts_score=0.8)]
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=EmptyRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(query="深色壁纸 不要人物", mode="wallpaper", limit=5)

    assert response.items
    assert response.trace.fallback_path == "rewrite"
    assert response.trace.rewrite_for_fts
    assert "empty rewrite" in caplog.text.lower()


def test_retrieval_service_raises_when_understanding_fails() -> None:
    repository = FakeRepository()
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=FailingUnderstandingService(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    with pytest.raises(
        RetrievalPreparationError,
        match="retrieval understanding failed and did not return valid structured JSON",
    ):
        service.retrieve(query="test", mode="auto", limit=5)


def test_retrieval_service_does_not_fallback_when_understanding_model_is_unavailable() -> None:
    repository = FakeRepository()
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=QueryUnderstandingService(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    with pytest.raises(
        RetrievalPreparationError,
        match="retrieval understanding failed and did not return valid structured JSON",
    ):
        service.retrieve(query="test", mode="auto", limit=5)


def test_retrieval_service_wraps_invalid_understanding_payload_errors() -> None:
    repository = FakeRepository()
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=InvalidJsonUnderstandingService(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    with pytest.raises(
        RetrievalPreparationError,
        match="retrieval understanding failed and did not return valid structured JSON",
    ):
        service.retrieve(query="test", mode="auto", limit=5)


def test_retrieval_service_raises_preparation_error_when_rewrite_and_fallback_both_fail() -> None:
    repository = FakeRepository()
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=EmptyStructuredUnderstandingService(),
            rewrite_service=FailingRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    with pytest.raises(
        RetrievalPreparationError,
        match="retrieval rewrite failed and fallback could not produce a valid rewrite",
    ):
        service.retrieve(query="test", mode="auto", limit=5)


def test_retrieval_service_respects_requested_limit() -> None:
    repository = FakeRepository(
        vector_candidates=[
            _candidate(id=index, photo_id=f"photo-{index}", vector_score=1.0 - index * 0.01)
            for index in range(1, 8)
        ]
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(
        query="我想找深色安静的 OLED 壁纸，不要人物",
        mode="wallpaper",
        limit=10,
    )

    assert len(response.items) == 7


def test_retrieval_service_prefers_candidates_matching_structured_phase_3_features() -> None:
    repository = FakeRepository(
        vector_candidates=[
            _candidate(
                id=10,
                photo_id="dark-minimal-match",
                search_text="wallpaper",
                retrieval_tag_text="dark minimal wallpaper oled",
                vector_score=0.4,
                wallpaper_score=0.8,
                is_dark=True,
                is_minimal=True,
                style_tags=["minimal"],
                color_tags=["dark"],
                use_case_tags=["wallpaper"],
            ),
            _candidate(
                id=11,
                photo_id="generic-wallpaper",
                search_text="wallpaper",
                retrieval_tag_text="wallpaper scenic",
                vector_score=0.4,
                wallpaper_score=0.8,
                style_tags=["scenic"],
                use_case_tags=["wallpaper"],
            ),
        ]
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(
        query="我想找深色的极简壁纸",
        mode="wallpaper",
        limit=5,
    )

    assert response.items
    assert response.items[0].unsplash_photo_id == "dark-minimal-match"
