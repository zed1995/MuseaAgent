from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


def test_search_agent_endpoint_returns_agent_workflow_result(monkeypatch) -> None:
    settings = get_settings()

    class StubWorkflow:
        def invoke(self, state):
            return {
                **state,
                "mode": "wallpaper",
                "topic_action": "new",
                "search_specs": [SimpleNamespace(spec_id="balanced-1")],
                "critic_result": SimpleNamespace(reason_code="ok"),
                "retry_count": 1,
                "final_items": [
                    SimpleNamespace(
                        model_dump=lambda: {
                            "unsplash_photo_id": "photo-1",
                            "source_spec_id": "balanced-1",
                        }
                    )
                ],
                "response_reason": "balanced-1 returned enough results",
            }

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

    monkeypatch.setattr("backend.api.routes.search_agent.create_engine", lambda url: StubEngine())
    monkeypatch.setattr("backend.api.routes.search_agent.build_retrieval_service", lambda **kwargs: object())
    monkeypatch.setattr(
        "backend.api.routes.search_agent.build_retrieval_preparation_service",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr("backend.api.routes.search_agent.build_agent_workflow", lambda **kwargs: StubWorkflow())
    monkeypatch.setattr("sqlalchemy.orm.Session", StubSession)

    client = TestClient(create_app(settings=settings))
    response = client.get("/api/search/agent", params={"query": "深色壁纸", "mode": "auto"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["response_reason"] == "balanced-1 returned enough results"
    assert payload["debug"]["retry_count"] == 1
    assert payload["debug"]["search_spec_ids"] == ["balanced-1"]
