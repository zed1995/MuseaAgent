from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


def test_search_debug_endpoint_is_not_exposed_by_default() -> None:
    settings = get_settings()
    settings.retrieval.enable_debug_endpoint = False
    client = TestClient(create_app(settings=settings))

    response = client.get("/api/search/debug", params={"query": "dark wallpaper"})

    assert response.status_code == 404


def test_search_debug_endpoint_can_be_enabled_without_real_services(monkeypatch) -> None:
    settings = get_settings()
    settings.retrieval.enable_debug_endpoint = True
    captured: dict[str, int] = {}

    class StubService:
        def retrieve(self, *, query: str, mode: str, limit: int, filters):
            captured["limit"] = limit
            from backend.schemas.search import RetrievalScoreBreakdown, RetrievalTrace
            from backend.services.retrieval.service import RetrievalItem, RetrievalResponse

            return RetrievalResponse(
                normalized_query="dark wallpaper",
                applied_filters=filters,
                candidates_considered=1,
                items=[
                    RetrievalItem(
                        photo_id=1,
                        unsplash_photo_id="photo-1",
                        unsplash_user_id=None,
                        orientation="portrait",
                        has_human=False,
                        search_text="dark wallpaper",
                        ai_caption="Dark wallpaper",
                        wallpaper_score=0.9,
                        photography_reference_score=0.2,
                        score_breakdown=RetrievalScoreBreakdown(final_score=0.9),
                    )
                ],
                trace=RetrievalTrace(
                    original_query=query,
                    normalized_query_text="dark wallpaper",
                    normalization_notes=[],
                    rewritten_terms=["dark", "wallpaper"],
                    applied_filters=filters,
                    vector_candidate_count=1,
                    fts_candidate_count=1,
                    fused_candidate_count=1,
                    dropped_candidate_reasons=[],
                    representation_bundle_used=True,
                    fts_document_version="multi_field_weighted_v1",
                    rerank_features_used=["structured_phase_3_signals"],
                ),
            )

    class StubConnection:
        def close(self) -> None:
            pass

    class StubEngine:
        def connect(self) -> StubConnection:
            return StubConnection()

        def dispose(self) -> None:
            pass

    class StubSession:
        def __init__(self, bind) -> None:
            self.bind = bind

        def close(self) -> None:
            pass

    monkeypatch.setattr("backend.api.routes.search_debug.create_engine", lambda url: StubEngine())
    monkeypatch.setattr("backend.api.routes.search_debug.build_retrieval_service", lambda **kwargs: StubService())
    monkeypatch.setattr("sqlalchemy.orm.Session", StubSession)

    client = TestClient(create_app(settings=settings))
    response = client.get("/api/search/debug", params={"query": "dark wallpaper"})

    assert response.status_code == 200
    assert response.json()["normalized_query"] == "dark wallpaper"
    assert response.json()["representation"]["bundle_used"] is True
    assert captured["limit"] == 5


def test_search_debug_endpoint_passes_through_explicit_limit(monkeypatch) -> None:
    settings = get_settings()
    settings.retrieval.enable_debug_endpoint = True
    captured: dict[str, int] = {}

    class StubService:
        def retrieve(self, *, query: str, mode: str, limit: int, filters):
            captured["limit"] = limit
            from backend.schemas.search import RetrievalScoreBreakdown, RetrievalTrace
            from backend.services.retrieval.service import RetrievalItem, RetrievalResponse

            return RetrievalResponse(
                normalized_query="dark wallpaper",
                applied_filters=filters,
                candidates_considered=1,
                items=[
                    RetrievalItem(
                        photo_id=1,
                        unsplash_photo_id="photo-1",
                        unsplash_user_id=None,
                        orientation="portrait",
                        has_human=False,
                        search_text="dark wallpaper",
                        ai_caption="Dark wallpaper",
                        wallpaper_score=0.9,
                        photography_reference_score=0.2,
                        score_breakdown=RetrievalScoreBreakdown(final_score=0.9),
                    )
                ],
                trace=RetrievalTrace(
                    original_query=query,
                    normalized_query_text="dark wallpaper",
                    normalization_notes=[],
                    rewritten_terms=["dark", "wallpaper"],
                    applied_filters=filters,
                    vector_candidate_count=1,
                    fts_candidate_count=1,
                    fused_candidate_count=1,
                    dropped_candidate_reasons=[],
                    representation_bundle_used=True,
                    fts_document_version="multi_field_weighted_v1",
                    rerank_features_used=["structured_phase_3_signals"],
                ),
            )

    class StubConnection:
        def close(self) -> None:
            pass

    class StubEngine:
        def connect(self) -> StubConnection:
            return StubConnection()

        def dispose(self) -> None:
            pass

    class StubSession:
        def __init__(self, bind) -> None:
            self.bind = bind

        def close(self) -> None:
            pass

    monkeypatch.setattr("backend.api.routes.search_debug.create_engine", lambda url: StubEngine())
    monkeypatch.setattr("backend.api.routes.search_debug.build_retrieval_service", lambda **kwargs: StubService())
    monkeypatch.setattr("sqlalchemy.orm.Session", StubSession)

    client = TestClient(create_app(settings=settings))
    response = client.get("/api/search/debug", params={"query": "dark wallpaper", "limit": 8})

    assert response.status_code == 200
    assert captured["limit"] == 8


def test_search_debug_endpoint_returns_structured_error_on_preparation_failure(monkeypatch) -> None:
    settings = get_settings()
    settings.retrieval.enable_debug_endpoint = True

    class FailingService:
        def retrieve(self, *, query: str, mode: str, limit: int, filters):
            from backend.services.retrieval_preparation.service import RetrievalPreparationError

            raise RetrievalPreparationError(
                "retrieval rewrite failed and fallback could not produce a valid rewrite"
            )

    class StubConnection:
        def close(self) -> None:
            pass

    class StubEngine:
        def connect(self) -> StubConnection:
            return StubConnection()

        def dispose(self) -> None:
            pass

    class StubSession:
        def __init__(self, bind) -> None:
            self.bind = bind

        def close(self) -> None:
            pass

    monkeypatch.setattr("backend.api.routes.search_debug.create_engine", lambda url: StubEngine())
    monkeypatch.setattr("backend.api.routes.search_debug.build_retrieval_service", lambda **kwargs: FailingService())
    monkeypatch.setattr("sqlalchemy.orm.Session", StubSession)

    client = TestClient(create_app(settings=settings))
    response = client.get("/api/search/debug", params={"query": "broken query"})

    assert response.status_code == 502
    assert "retrieval rewrite failed" in response.json()["detail"]


def test_search_debug_endpoint_returns_structured_error_on_understanding_failure(monkeypatch) -> None:
    settings = get_settings()
    settings.retrieval.enable_debug_endpoint = True

    class FailingService:
        def retrieve(self, *, query: str, mode: str, limit: int, filters):
            from backend.services.retrieval_preparation.service import RetrievalPreparationError

            raise RetrievalPreparationError(
                "retrieval understanding failed and did not return valid structured JSON"
            )

    class StubConnection:
        def close(self) -> None:
            pass

    class StubEngine:
        def connect(self) -> StubConnection:
            return StubConnection()

        def dispose(self) -> None:
            pass

    class StubSession:
        def __init__(self, bind) -> None:
            self.bind = bind

        def close(self) -> None:
            pass

    monkeypatch.setattr("backend.api.routes.search_debug.create_engine", lambda url: StubEngine())
    monkeypatch.setattr("backend.api.routes.search_debug.build_retrieval_service", lambda **kwargs: FailingService())
    monkeypatch.setattr("sqlalchemy.orm.Session", StubSession)

    client = TestClient(create_app(settings=settings))
    response = client.get("/api/search/debug", params={"query": "broken query"})

    assert response.status_code == 502
    assert "retrieval understanding failed" in response.json()["detail"]
