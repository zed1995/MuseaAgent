from backend.agents.contracts import SearchResult
from backend.agents.policies.critic_policy import HybridCriticPolicy, RuleCriticPolicy


class FakeCriticAdviceChain:
    def invoke(self, payload: dict):
        class Result:
            summary = f"strict underperformed; preferred={payload['rule_result'].preferred_spec_id}"

        return Result()


def test_hybrid_critic_preserves_rule_decision_and_adds_model_summary() -> None:
    policy = HybridCriticPolicy(
        base_policy=RuleCriticPolicy(
            min_acceptable_results=6,
            hard_constraint_min_match_ratio=0.85,
        ),
        advice_chain=FakeCriticAdviceChain(),
    )

    result = policy.evaluate(
        search_results=[
            SearchResult(spec_id="strict-1", total_hits=2, items=[]),
            SearchResult(spec_id="balanced-1", total_hits=12, items=[]),
        ],
        retry_count=0,
    )

    assert result.retry_strategy == "switch_to_balanced"
    assert "strict" in result.summary
