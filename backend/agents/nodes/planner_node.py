from backend.agents.contracts import SearchSpec


class PlannerNode:
    def __init__(self, chain=None) -> None:
        self._chain = chain

    def run(self, state: dict[str, object]) -> dict[str, object]:
        if self._chain is not None:
            # When an LLM planner is available, it must still emit controlled
            # search specs rather than free-form retrieval behavior.
            result = self._chain.invoke(
                {
                    "mode": state["mode"],
                    "hard_constraints": state["hard_constraints"],
                    "soft_preferences": state["soft_preferences"],
                }
            )
            return {"search_specs": result.search_specs}

        mode = str(state["mode"])
        hard_constraints = dict(state["hard_constraints"])
        soft_preferences = dict(state["soft_preferences"])

        # The deterministic fallback keeps the workflow usable without a model
        # by always producing the same strict/balanced/exploratory spec set.
        strict_terms = self._build_terms(mode, soft_preferences, include_qualities=True, exploratory=False)
        balanced_terms = self._build_terms(mode, soft_preferences, include_qualities=False, exploratory=False)
        exploratory_terms = self._build_terms(mode, soft_preferences, include_qualities=False, exploratory=True)
        negative_terms = self._negative_terms(hard_constraints)

        search_specs = [
            SearchSpec(
                spec_id="strict-1",
                query_text=" ".join(strict_terms + negative_terms),
                query_mode="strict",
                filters=hard_constraints,
                limit=20,
            ),
            SearchSpec(
                spec_id="balanced-1",
                query_text=" ".join(balanced_terms + negative_terms),
                query_mode="balanced",
                filters=hard_constraints,
                limit=20,
            ),
            SearchSpec(
                spec_id="exploratory-1",
                query_text=" ".join(exploratory_terms + negative_terms),
                query_mode="exploratory",
                filters=hard_constraints,
                limit=20,
            ),
        ]

        return {"search_specs": search_specs}

    def _build_terms(
        self,
        mode: str,
        soft_preferences: dict[str, object],
        *,
        include_qualities: bool,
        exploratory: bool,
    ) -> list[str]:
        terms: list[str] = []
        colors = [str(value) for value in soft_preferences.get("colors", [])]
        moods = [str(value) for value in soft_preferences.get("moods", [])]
        qualities = [str(value) for value in soft_preferences.get("qualities", [])]

        terms.extend(colors[:1])

        if exploratory:
            if moods:
                terms.append("moody" if moods[0] == "calm" else moods[0])
        else:
            terms.extend(moods[:1])

        if include_qualities:
            terms.extend(qualities[:1])

        if mode != "auto":
            terms.append(mode)

        return [term for term in terms if term]

    def _negative_terms(self, hard_constraints: dict[str, object]) -> list[str]:
        if hard_constraints.get("has_human") is False:
            return ["no", "people"]
        return []
