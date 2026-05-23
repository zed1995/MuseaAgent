from dataclasses import dataclass

from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval.fusion import FusedRetrievalCandidate
from backend.schemas.search import RetrievalScoreBreakdown


_WORDS_TO_SKIP = frozenset(
    {"prefer", "avoid", "has", "is", "no", "not", "with", "without", "the"}
)


@dataclass(slots=True)
class RankedRetrievalItem:
    id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    search_text: str
    ai_caption: str
    has_human: bool
    wallpaper_score: float
    photography_reference_score: float
    score_breakdown: RetrievalScoreBreakdown


def _compute_normalization_alignment(
    soft_signals: dict[str, bool | float | str],
    search_text: str,
    ai_caption: str,
) -> float:
    """Small bonus when soft signal keywords appear in the candidate text."""
    score = 0.0
    combined_text = (search_text + " " + ai_caption).lower()

    for key, value in soft_signals.items():
        if not value:
            continue
        words = [
            w
            for w in key.lower().split("_")
            if len(w) > 2 and w not in _WORDS_TO_SKIP
        ]
        for word in words:
            if word in combined_text:
                score += 0.1
                break

    return min(score, 0.2)


class RetrievalReranker:
    """Deterministic reranker that combines multiple score signals.

    The final score is a weighted combination of:
      - hybrid_score (RRF)         55 %
      - use_case_score              20 %
      - metadata_match_score        15 %
      - normalization_alignment     10 %
    """

    def rank(
        self,
        candidates: list[FusedRetrievalCandidate],
        mode: str,
        filters: RetrievalFilters,
        soft_signals: dict[str, bool | float | str],
        limit: int,
    ) -> list[RankedRetrievalItem]:
        """Rerank fused candidates using deterministic scoring.

        Args:
            candidates: Fused candidates from RRF, pre-sorted by hybrid_score.
            mode: Use-case mode - "wallpaper", "reference", or "auto".
            filters: Hard filters that also contribute metadata-match bonus.
            soft_signals: Normalization soft signals for alignment bonus.
            limit: Maximum number of results to return.

        Returns:
            Top-``limit`` candidates sorted descending by final_score, each
            wrapped in a ``RankedRetrievalItem`` with a full score breakdown.
        """
        ranked: list[RankedRetrievalItem] = []

        for c in candidates:
            # --- metadata_match_score (0.0 - 1.0) ---
            metadata_score = 0.0

            if (
                filters.orientation is None
                or c.orientation == filters.orientation
            ):
                metadata_score += 0.5

            if filters.has_human is None or c.has_human == filters.has_human:
                metadata_score += 0.5

            # --- use_case_score (0.0 - 1.0) ---
            if mode == "wallpaper":
                use_case_score = c.wallpaper_score
            elif mode == "reference":
                use_case_score = c.photography_reference_score
            else:  # "auto"
                use_case_score = max(
                    c.wallpaper_score, c.photography_reference_score
                )

            # --- normalization_alignment_score (0.0 - 0.2) ---
            alignment_score = _compute_normalization_alignment(
                soft_signals, c.search_text, c.ai_caption
            )

            # --- final_score ---
            final_score = (
                0.55 * c.hybrid_score
                + 0.20 * use_case_score
                + 0.15 * metadata_score
                + 0.10 * alignment_score
            )

            breakdown = RetrievalScoreBreakdown(
                vector_score=c.vector_score,
                fts_score=c.fts_score,
                hybrid_score=c.hybrid_score,
                metadata_match_score=metadata_score,
                use_case_score=use_case_score,
                final_score=final_score,
            )

            ranked.append(
                RankedRetrievalItem(
                    id=c.id,
                    unsplash_photo_id=c.unsplash_photo_id,
                    unsplash_user_id=c.unsplash_user_id,
                    orientation=c.orientation,
                    search_text=c.search_text,
                    ai_caption=c.ai_caption,
                    has_human=c.has_human,
                    wallpaper_score=c.wallpaper_score,
                    photography_reference_score=c.photography_reference_score,
                    score_breakdown=breakdown,
                )
            )

        ranked.sort(key=lambda x: x.score_breakdown.final_score, reverse=True)
        return ranked[:limit]
