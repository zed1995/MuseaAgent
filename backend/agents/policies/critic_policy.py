from backend.agents.contracts import CriticResult, SearchResult


class CriticPolicy:
    def __init__(self, min_acceptable_results: int, hard_constraint_min_match_ratio: float) -> None:
        self._min_acceptable_results = min_acceptable_results
        self._hard_constraint_min_match_ratio = hard_constraint_min_match_ratio

    def evaluate(self, search_results: list[SearchResult], retry_count: int) -> CriticResult:
        if not search_results:
            return CriticResult(
                passed=False,
                reason_code="too_few_results",
                retry_strategy="none" if retry_count > 0 else "switch_to_exploratory",
                preferred_spec_id=None,
                summary="no search results were produced",
            )

        ordered = sorted(search_results, key=lambda result: result.total_hits, reverse=True)
        best = ordered[0]
        strict = next((result for result in search_results if result.spec_id.startswith("strict")), None)
        balanced = next((result for result in search_results if result.spec_id.startswith("balanced")), None)
        exploratory = next((result for result in search_results if result.spec_id.startswith("exploratory")), None)

        if strict and balanced and balanced.total_hits > strict.total_hits:
            return CriticResult(
                passed=False,
                reason_code="too_few_results",
                retry_strategy="switch_to_balanced",
                preferred_spec_id=balanced.spec_id,
                summary="strict search was too narrow",
            )

        if exploratory and exploratory.total_hits > best.total_hits:
            return CriticResult(
                passed=False,
                reason_code="overly_narrow_query",
                retry_strategy="switch_to_exploratory",
                preferred_spec_id=exploratory.spec_id,
                summary="a broader exploratory search should be tried",
            )

        if best.total_hits >= self._min_acceptable_results:
            return CriticResult(
                passed=True,
                reason_code="ok",
                retry_strategy="none",
                preferred_spec_id=best.spec_id,
                summary=f"{best.spec_id} returned enough results",
            )

        if retry_count > 0:
            return CriticResult(
                passed=False,
                reason_code="too_few_results",
                retry_strategy="none",
                preferred_spec_id=best.spec_id,
                summary="results remained too narrow after one retry",
            )

        return CriticResult(
            passed=False,
            reason_code="low_relevance",
            retry_strategy="relax_soft_preferences",
            preferred_spec_id=best.spec_id,
            summary="current results are not strong enough",
        )
