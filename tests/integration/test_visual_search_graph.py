from types import SimpleNamespace

from backend.agents.contracts import SearchSpec
from backend.agents.factory import build_agent_workflow


class FakeRetrievalPreparationService:
    def prepare(self, query: str, mode: str, explicit_filters=None):
        understanding = SimpleNamespace(
            hard_filters=SimpleNamespace(
                model_dump=lambda exclude_none=True: {"has_human": False}
            ),
            soft_preferences=SimpleNamespace(
                model_dump=lambda: {
                    "moods": ["calm"],
                    "colors": ["dark"],
                    "qualities": ["oled"],
                }
            ),
        )
        return SimpleNamespace(understanding=understanding)


class FakeRetrievalService:
    def retrieve(self, query: str, mode: str, limit: int, filters, debug: bool):
        hit_count = 2 if "oled" in query else 8
        items = [
            SimpleNamespace(
                unsplash_photo_id=f"{query}-{index}",
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
            for index in range(hit_count)
        ]
        trace = SimpleNamespace(model_dump=lambda: {"query": query, "limit": limit})
        return SimpleNamespace(items=items, trace=trace)


def test_graph_runs_single_retry_then_returns_response() -> None:
    workflow = build_agent_workflow(
        retrieval_preparation_service=FakeRetrievalPreparationService(),
        retrieval_service=FakeRetrievalService(),
        min_acceptable_results=6,
        hard_constraint_min_match_ratio=0.85,
        max_retry_count=1,
    )

    result = workflow.invoke(
        {
            "request_id": "req_123",
            "conversation_id": None,
            "user_id": None,
            "original_query": "我想找深色安静的壁纸，不要人物",
            "conversation_history": [],
            "mode": "auto",
            "topic_action": None,
            "hard_constraints": {},
            "soft_preferences": {},
            "search_specs": [],
            "search_results": [],
            "critic_result": None,
            "retry_count": 0,
            "final_items": [],
            "response_reason": None,
            "errors": [],
        }
    )

    assert result["critic_result"] is not None
    assert result["retry_count"] == 1
    assert result["final_items"]
    assert result["response_reason"] == "balanced-1 returned enough results"
