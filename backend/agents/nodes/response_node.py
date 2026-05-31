from backend.agents.states import VisualSearchState


class ResponseNode:
    def run(self, state: VisualSearchState) -> dict[str, object]:
        critic_result = state["critic_result"]
        preferred_spec_id = critic_result.preferred_spec_id if critic_result is not None else None
        chosen_result = next(
            (
                result
                for result in state["search_results"]
                if preferred_spec_id is not None and result.spec_id == preferred_spec_id
            ),
            state["search_results"][0] if state["search_results"] else None,
        )

        return {
            "final_items": [] if chosen_result is None else chosen_result.items[:20],
            "response_reason": None if critic_result is None else critic_result.summary,
        }
