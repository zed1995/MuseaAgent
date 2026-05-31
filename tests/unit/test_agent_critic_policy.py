from backend.agents.contracts import SearchResult
from backend.agents.policies.critic_policy import CriticPolicy


def test_critic_switches_to_balanced_when_strict_results_are_too_few() -> None:
    policy = CriticPolicy(min_acceptable_results=6, hard_constraint_min_match_ratio=0.85)

    result = policy.evaluate(
        search_results=[
            SearchResult(spec_id="strict-1", total_hits=2, items=[]),
            SearchResult(spec_id="balanced-1", total_hits=12, items=[]),
        ],
        retry_count=0,
    )

    assert result.passed is False
    assert result.retry_strategy == "switch_to_balanced"
    assert result.preferred_spec_id == "balanced-1"
