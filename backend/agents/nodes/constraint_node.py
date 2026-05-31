from backend.agents.states import VisualSearchState


class ConstraintNode:
    def __init__(self, retrieval_preparation_service) -> None:
        self._retrieval_preparation_service = retrieval_preparation_service

    def run(self, state: VisualSearchState) -> dict[str, object]:
        # Constraint extraction intentionally reuses the Phase 4 preparation
        # stack so the graph consumes the same understanding contract that the
        # retrieval core already trusts.
        prepared = self._retrieval_preparation_service.prepare(
            query=state["original_query"],
            mode=state["mode"],
            explicit_filters=None,
        )
        return {
            "hard_constraints": prepared.understanding.hard_filters.model_dump(exclude_none=True),
            "soft_preferences": prepared.understanding.soft_preferences.model_dump(),
        }
