from backend.services.retrieval.contracts import RetrievalFilters
from backend.services.retrieval.fusion import FusedRetrievalCandidate
from backend.services.retrieval.rerank import RetrievalReranker


def test_rerank_prefers_wallpaper_fit_when_mode_is_wallpaper() -> None:
    reranker = RetrievalReranker()
    candidates = [
        FusedRetrievalCandidate(
            id=1,
            unsplash_photo_id="high-wallpaper",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="",
            ai_caption="",
            has_human=False,
            wallpaper_score=0.95,
            photography_reference_score=0.3,
            vector_score=0.7,
            fts_score=0.0,
            hybrid_score=0.7,
        ),
        FusedRetrievalCandidate(
            id=2,
            unsplash_photo_id="low-wallpaper",
            unsplash_user_id=None,
            orientation="landscape",
            search_text="",
            ai_caption="",
            has_human=False,
            wallpaper_score=0.3,
            photography_reference_score=0.9,
            vector_score=0.7,
            fts_score=0.0,
            hybrid_score=0.7,
        ),
    ]

    ranked = reranker.rank(
        candidates=candidates,
        mode="wallpaper",
        filters=RetrievalFilters(),
        soft_signals={},
        limit=5,
    )

    assert ranked[0].unsplash_photo_id == "high-wallpaper"


def test_rerank_metadata_match_orientation() -> None:
    reranker = RetrievalReranker()
    candidates = [
        FusedRetrievalCandidate(
            id=1,
            unsplash_photo_id="portrait-match",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="",
            ai_caption="",
            has_human=False,
            wallpaper_score=0.5,
            photography_reference_score=0.5,
            vector_score=0.5,
            fts_score=0.0,
            hybrid_score=0.5,
        ),
        FusedRetrievalCandidate(
            id=2,
            unsplash_photo_id="landscape-mismatch",
            unsplash_user_id=None,
            orientation="landscape",
            search_text="",
            ai_caption="",
            has_human=False,
            wallpaper_score=0.5,
            photography_reference_score=0.5,
            vector_score=0.5,
            fts_score=0.0,
            hybrid_score=0.5,
        ),
    ]

    ranked = reranker.rank(
        candidates=candidates,
        mode="auto",
        filters=RetrievalFilters(orientation="portrait"),
        soft_signals={},
        limit=5,
    )

    assert ranked[0].unsplash_photo_id == "portrait-match"


def test_rerank_has_score_breakdown() -> None:
    reranker = RetrievalReranker()
    candidates = [
        FusedRetrievalCandidate(
            id=1,
            unsplash_photo_id="photo-1",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="test",
            ai_caption="Test",
            has_human=False,
            wallpaper_score=0.5,
            photography_reference_score=0.5,
            vector_score=0.8,
            fts_score=0.6,
            hybrid_score=0.7,
        ),
    ]

    ranked = reranker.rank(
        candidates=candidates,
        mode="auto",
        filters=RetrievalFilters(),
        soft_signals={},
        limit=5,
    )

    assert ranked[0].score_breakdown.vector_score == 0.8
    assert ranked[0].score_breakdown.fts_score == 0.6
    assert ranked[0].score_breakdown.final_score > 0


def test_rerank_prefers_candidates_matching_more_user_explicit_terms() -> None:
    reranker = RetrievalReranker()
    candidates = [
        FusedRetrievalCandidate(
            id=1,
            unsplash_photo_id="beach-sunset",
            unsplash_user_id=None,
            orientation="landscape",
            search_text="beach sunset ocean golden sky",
            ai_caption="A beach sunset scene.",
            has_human=False,
            wallpaper_score=0.6,
            photography_reference_score=0.3,
            vector_score=0.6,
            fts_score=0.01,
            hybrid_score=0.02,
        ),
        FusedRetrievalCandidate(
            id=2,
            unsplash_photo_id="beach-only",
            unsplash_user_id=None,
            orientation="landscape",
            search_text="beach ocean shore calm",
            ai_caption="A calm beach scene.",
            has_human=False,
            wallpaper_score=0.6,
            photography_reference_score=0.3,
            vector_score=0.6,
            fts_score=0.01,
            hybrid_score=0.02,
        ),
    ]

    ranked = reranker.rank(
        candidates=candidates,
        mode="auto",
        filters=RetrievalFilters(),
        soft_signals={
            "user_explicit_terms": ["beach", "sunset"],
            "supporting_terms": ["calm", "golden"],
        },
        limit=5,
    )

    assert ranked[0].unsplash_photo_id == "beach-sunset"
    assert (
        ranked[0].score_breakdown.explicit_term_match_score
        > ranked[1].score_breakdown.explicit_term_match_score
    )
