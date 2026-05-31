from backend.agents.policies.critic_policy import CriticPolicy
from backend.agents.states import VisualSearchState


class CriticNode:
    def __init__(self, policy: CriticPolicy) -> None:
        self._policy = policy

    def run(self, state: VisualSearchState) -> dict[str, object]:
        return {
            "critic_result": self._policy.evaluate(
                search_results=state["search_results"],
                retry_count=state["retry_count"],
            )
        }
