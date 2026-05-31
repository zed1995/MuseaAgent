from types import SimpleNamespace

from backend.agents.contracts import SearchSpec
from backend.services.agent_runtime import AgentRuntimeService


class FakeRetrievalService:
    def retrieve(self, query: str, mode: str, limit: int, filters, debug: bool):
        item = SimpleNamespace(
            unsplash_photo_id=f"{query}-photo",
            orientation="portrait",
            score_breakdown=SimpleNamespace(
                vector_score=0.8,
                fts_score=0.7,
                hybrid_score=0.75,
                metadata_match_score=1.0,
                use_case_score=0.9,
                final_score=0.88,
            ),
        )
        trace = SimpleNamespace(
            model_dump=lambda: {
                "query": query,
                "mode": mode,
                "filters": filters.model_dump() if hasattr(filters, "model_dump") else filters,
            }
        )
        return SimpleNamespace(items=[item], trace=trace)


def test_agent_runtime_executes_multiple_search_specs_and_preserves_source_spec_id() -> None:
    runtime = AgentRuntimeService(retrieval_service=FakeRetrievalService(), graph=None)

    results = runtime.execute_search_specs(
        mode="wallpaper",
        search_specs=[
            SearchSpec(
                spec_id="strict-1",
                query_text="dark calm wallpaper no people",
                query_mode="strict",
                filters={"has_human": False},
                limit=10,
            ),
            SearchSpec(
                spec_id="balanced-1",
                query_text="dark wallpaper no people",
                query_mode="balanced",
                filters={"has_human": False},
                limit=10,
            ),
        ],
    )

    assert len(results) == 2
    assert all(result.spec_id in {"strict-1", "balanced-1"} for result in results)
    assert all(item.source_spec_id == result.spec_id for result in results for item in result.items)
