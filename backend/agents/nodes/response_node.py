from backend.agents.states import VisualSearchState


class ResponseNode:
    def __init__(self, chain=None) -> None:
        self._chain = chain

    def run(self, state: VisualSearchState) -> dict[str, object]:
        critic_result = state["critic_result"]
        preferred_spec_id = critic_result.preferred_spec_id if critic_result is not None else None
        # Response selection is a packaging step: by the time we get here, the
        # critic has already decided which spec outcome should win.
        chosen_result = next(
            (
                result
                for result in state["search_results"]
                if preferred_spec_id is not None and result.spec_id == preferred_spec_id
            ),
            state["search_results"][0] if state["search_results"] else None,
        )

        response_reason = None if critic_result is None else critic_result.summary
        if self._chain is not None and chosen_result is not None:
            reason_result = self._chain.invoke(
                {
                    "query": state["original_query"],
                    "mode": state["mode"],
                    "selected_spec_id": chosen_result.spec_id,
                    "top_result_ids": [item.unsplash_photo_id for item in chosen_result.items[:5]],
                }
            )
            response_reason = reason_result.reason

        return {
            "final_items": [] if chosen_result is None else chosen_result.items[:20],
            "response_reason": response_reason,
        }
