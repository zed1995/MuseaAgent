from backend.agents.contracts import CriticResult, SearchSpec


def apply_retry_strategy(
    search_specs: list[SearchSpec],
    critic_result: CriticResult,
) -> list[SearchSpec]:
    # Retry rewrites the active spec set, not the whole workflow state. This
    # keeps retries explainable and prevents hidden replanning in the loop.
    if critic_result.retry_strategy == "none":
        return search_specs

    if critic_result.preferred_spec_id is not None:
        preferred = [spec for spec in search_specs if spec.spec_id == critic_result.preferred_spec_id]
        if preferred:
            return preferred

    if critic_result.retry_strategy == "switch_to_balanced":
        return [spec for spec in search_specs if spec.query_mode == "balanced"] or search_specs

    if critic_result.retry_strategy == "switch_to_exploratory":
        return [spec for spec in search_specs if spec.query_mode == "exploratory"] or search_specs

    return [
        SearchSpec(
            spec_id=spec.spec_id,
            query_text=spec.query_text,
            query_mode=spec.query_mode,
            filters=dict(spec.filters),
            limit=spec.limit,
        )
        for spec in search_specs
    ]
