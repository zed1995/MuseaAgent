from dataclasses import dataclass

from backend.repositories.records import PhotoRetrievalCandidate


@dataclass(slots=True)
class FusedRetrievalCandidate:
    id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    search_text: str
    ai_caption: str
    has_human: bool
    wallpaper_score: float
    photography_reference_score: float
    vector_score: float
    fts_score: float
    hybrid_score: float = 0.0
    provenance: str = "vector"  # "vector", "fts", or "both"


def reciprocal_rank_fusion(
    vector_results: list[PhotoRetrievalCandidate],
    fts_results: list[PhotoRetrievalCandidate],
    k: int = 60,
) -> list[FusedRetrievalCandidate]:
    """Merge vector and FTS search results using reciprocal-rank fusion (RRF).

    Each candidate's RRF score is computed as the sum of 1/(k + rank + 1)
    across all result lists in which it appears.  Results present in both
    lists receive a boost, while duplicates are deduplicated.

    Args:
        vector_results: Candidates from the vector (embedding) search, in rank order.
        fts_results: Candidates from the full-text search, in rank order.
        k: RRF constant (default 60).

    Returns:
        A deduplicated list of FusedRetrievalCandidate sorted descending by
        hybrid_score (the RRF score).
    """
    # accumulator: unsplash_photo_id -> FusedRetrievalCandidate
    fused: dict[str, FusedRetrievalCandidate] = {}

    for rank, candidate in enumerate(vector_results):
        photo_id = candidate.unsplash_photo_id
        rrf_contribution = 1.0 / (k + rank + 1)
        if photo_id in fused:
            existing = fused[photo_id]
            existing.hybrid_score += rrf_contribution
            existing.provenance = "both"
            existing.vector_score = max(
                existing.vector_score, candidate.vector_score
            )
            existing.fts_score = max(existing.fts_score, candidate.fts_score)
        else:
            fused[photo_id] = FusedRetrievalCandidate(
                id=candidate.id,
                unsplash_photo_id=photo_id,
                unsplash_user_id=candidate.unsplash_user_id,
                orientation=candidate.orientation,
                search_text=candidate.search_text,
                ai_caption=candidate.ai_caption,
                has_human=candidate.has_human,
                wallpaper_score=candidate.wallpaper_score,
                photography_reference_score=candidate.photography_reference_score,
                vector_score=candidate.vector_score,
                fts_score=candidate.fts_score,
                hybrid_score=rrf_contribution,
                provenance="vector",
            )

    for rank, candidate in enumerate(fts_results):
        photo_id = candidate.unsplash_photo_id
        rrf_contribution = 1.0 / (k + rank + 1)
        if photo_id in fused:
            existing = fused[photo_id]
            existing.hybrid_score += rrf_contribution
            existing.provenance = "both"
            existing.vector_score = max(
                existing.vector_score, candidate.vector_score
            )
            existing.fts_score = max(existing.fts_score, candidate.fts_score)
        else:
            fused[photo_id] = FusedRetrievalCandidate(
                id=candidate.id,
                unsplash_photo_id=photo_id,
                unsplash_user_id=candidate.unsplash_user_id,
                orientation=candidate.orientation,
                search_text=candidate.search_text,
                ai_caption=candidate.ai_caption,
                has_human=candidate.has_human,
                wallpaper_score=candidate.wallpaper_score,
                photography_reference_score=candidate.photography_reference_score,
                vector_score=candidate.vector_score,
                fts_score=candidate.fts_score,
                hybrid_score=rrf_contribution,
                provenance="fts",
            )

    return sorted(fused.values(), key=lambda x: x.hybrid_score, reverse=True)
