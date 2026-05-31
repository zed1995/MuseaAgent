from backend.agents.contracts import CandidateItem, SearchResult
from backend.agents.states import VisualSearchState
from backend.services.retrieval.contracts import RetrievalFilters


class SearchExecutionNode:
    def __init__(self, retrieval_service) -> None:
        self._retrieval_service = retrieval_service

    def run(self, state: VisualSearchState) -> dict[str, object]:
        results: list[SearchResult] = []

        for spec in state["search_specs"]:
            # Each planner spec is executed independently so the critic can
            # compare strict/balanced/exploratory outcomes instead of seeing
            # only one merged retrieval result.
            retrieval_result = self._retrieval_service.retrieve(
                query=spec.query_text,
                mode=state["mode"],
                limit=spec.limit,
                filters=RetrievalFilters.model_validate(spec.filters),
                debug=True,
            )
            items = [
                CandidateItem(
                    unsplash_photo_id=item.unsplash_photo_id,
                    orientation=getattr(item, "orientation", None),
                    vector_score=item.score_breakdown.vector_score,
                    fts_score=item.score_breakdown.fts_score,
                    hybrid_score=getattr(item.score_breakdown, "hybrid_score", None),
                    metadata_match_score=item.score_breakdown.metadata_match_score,
                    use_case_score=item.score_breakdown.use_case_score,
                    final_score=item.score_breakdown.final_score,
                    matched_constraints={},
                    source_spec_id=spec.spec_id,
                )
                for item in retrieval_result.items
            ]
            results.append(
                SearchResult(
                    spec_id=spec.spec_id,
                    total_hits=len(retrieval_result.items),
                    items=items,
                    debug=retrieval_result.trace.model_dump(),
                )
            )

        return {"search_results": results}
