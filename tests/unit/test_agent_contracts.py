from backend.agents.contracts import CriticResult, SearchSpec
from backend.agents.states import VisualSearchState


def test_agent_contracts_preserve_retry_and_spec_metadata() -> None:
    spec = SearchSpec(
        spec_id="strict-1",
        query_text="dark calm wallpaper no people",
        query_mode="strict",
        filters={"has_human": False},
        limit=20,
    )
    critic = CriticResult(
        passed=False,
        reason_code="too_few_results",
        retry_strategy="switch_to_balanced",
        preferred_spec_id="balanced-1",
        summary="strict search was too narrow",
    )
    state: VisualSearchState = {
        "request_id": "req_123",
        "conversation_id": None,
        "user_id": None,
        "original_query": "我想找深色安静的壁纸，不要人物",
        "conversation_history": [],
        "mode": "wallpaper",
        "topic_action": "new",
        "hard_constraints": {"has_human": False},
        "soft_preferences": {"moods": ["calm"]},
        "search_specs": [spec],
        "search_results": [],
        "critic_result": critic,
        "retry_count": 0,
        "final_items": [],
        "response_reason": None,
        "errors": [],
    }

    assert state["search_specs"][0].query_mode == "strict"
    assert state["critic_result"].retry_strategy == "switch_to_balanced"
