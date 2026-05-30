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
    retrieval_caption_text: str = ""
    retrieval_tag_text: str = ""


def _normalize_terms(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        lowered = value.lower().strip()
        if len(lowered) <= 2 or lowered in _WORDS_TO_SKIP or lowered in result:
            continue
        result.append(lowered)
    return result


def _compute_alignment_scores(
    soft_signals: dict[str, list[str]],
    search_text: str,
    ai_caption: str,
    retrieval_caption_text: str,
    retrieval_tag_text: str,
) -> tuple[float, float]:
    combined_text = " ".join(
        [search_text, ai_caption, retrieval_caption_text, retrieval_tag_text]
    ).lower()
    explicit_terms = _normalize_terms(soft_signals.get("user_explicit_terms", []))
    supporting_terms = _normalize_terms(soft_signals.get("supporting_terms", []))

    explicit_matches = sum(1 for term in explicit_terms if term in combined_text)
    supporting_matches = sum(1 for term in supporting_terms if term in combined_text)

    explicit_score = (
        explicit_matches / len(explicit_terms)
        if explicit_terms
        else 0.0
    )
    supporting_score = (
        supporting_matches / len(supporting_terms)
        if supporting_terms
        else 0.0
    )
    return explicit_score, supporting_score


def _compute_structured_match_score(
    soft_signals: dict[str, list[str] | bool],
    candidate: FusedRetrievalCandidate,
) -> float:
    structured_terms = _normalize_terms(
        [
            *(candidate.scene_tags or []),
            *(candidate.style_tags or []),
            *(candidate.color_tags or []),
            *(candidate.subject_tags or []),
            *(candidate.use_case_tags or []),
        ]
    )
    if not structured_terms and not soft_signals.get("exclude_faces", False):
        return 0.0

    structured_text = " ".join(structured_terms)
    explicit_terms = _normalize_terms(soft_signals.get("user_explicit_terms", []))
    supporting_terms = _normalize_terms(soft_signals.get("supporting_terms", []))

    term_match_scores: list[float] = []
    if explicit_terms:
        explicit_matches = sum(1 for term in explicit_terms if term in structured_text)
        term_match_scores.append(explicit_matches / len(explicit_terms))
    if supporting_terms:
        supporting_matches = sum(1 for term in supporting_terms if term in structured_text)
        term_match_scores.append(supporting_matches / len(supporting_terms))

    if soft_signals.get("exclude_faces", False):
        term_match_scores.append(1.0 if candidate.has_face is False else 0.0)

    return sum(term_match_scores) / len(term_match_scores) if term_match_scores else 0.0


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
        soft_signals: dict[str, list[str]],
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

            # --- explicit/supporting alignment scores (0.0 - 1.0) ---
            explicit_alignment_score, supporting_alignment_score = _compute_alignment_scores(
                soft_signals,
                c.search_text,
                c.ai_caption,
                c.retrieval_caption_text,
                c.retrieval_tag_text,
            )
            structured_match_score = _compute_structured_match_score(soft_signals, c)

            # --- final_score ---
            final_score = (
                0.50 * c.hybrid_score
                + 0.20 * use_case_score
                + 0.15 * metadata_score
                + 0.10 * explicit_alignment_score
                + 0.03 * supporting_alignment_score
                + 0.02 * structured_match_score
            )

            breakdown = RetrievalScoreBreakdown(
                vector_score=c.vector_score,
                fts_score=c.fts_score,
                hybrid_score=c.hybrid_score,
                metadata_match_score=metadata_score,
                use_case_score=use_case_score,
                explicit_term_match_score=explicit_alignment_score,
                supporting_term_match_score=supporting_alignment_score,
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
                    retrieval_caption_text=c.retrieval_caption_text,
                    retrieval_tag_text=c.retrieval_tag_text,
                    score_breakdown=breakdown,
                )
            )

        ranked.sort(key=lambda x: x.score_breakdown.final_score, reverse=True)
        return ranked[:limit]
