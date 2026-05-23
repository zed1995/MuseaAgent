from backend.services.retrieval.fusion import FusedRetrievalCandidate, reciprocal_rank_fusion
from backend.repositories.records import PhotoRetrievalCandidate


def test_rrf_merges_vector_and_fts_candidates_without_duplicates() -> None:
    vector_results = [
        PhotoRetrievalCandidate(
            id=1,
            unsplash_photo_id="photo-1",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="dark wallpaper",
            ai_caption="Dark wallpaper",
            has_human=False,
            wallpaper_score=0.9,
            photography_reference_score=0.5,
            vector_score=0.91,
            fts_score=0.0,
        ),
        PhotoRetrievalCandidate(
            id=2,
            unsplash_photo_id="photo-2",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="calm scene",
            ai_caption="Calm scene",
            has_human=False,
            wallpaper_score=0.8,
            photography_reference_score=0.4,
            vector_score=0.82,
            fts_score=0.0,
        ),
    ]
    fts_results = [
        PhotoRetrievalCandidate(
            id=2,
            unsplash_photo_id="photo-2",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="calm scene",
            ai_caption="Calm scene",
            has_human=False,
            wallpaper_score=0.8,
            photography_reference_score=0.4,
            vector_score=0.0,
            fts_score=0.60,
        ),
        PhotoRetrievalCandidate(
            id=3,
            unsplash_photo_id="photo-3",
            unsplash_user_id=None,
            orientation="landscape",
            search_text="mountain view",
            ai_caption="Mountain view",
            has_human=True,
            wallpaper_score=0.3,
            photography_reference_score=0.7,
            vector_score=0.0,
            fts_score=0.55,
        ),
    ]

    fused = reciprocal_rank_fusion(vector_results, fts_results, k=60)

    ids = [item.unsplash_photo_id for item in fused]

    assert ids[0] == "photo-2"  # present in both, should rank highest
    assert len(ids) == 3
    assert len(set(ids)) == 3  # no duplicates


def test_rrf_handles_empty_vector_results() -> None:
    fused = reciprocal_rank_fusion([], [], k=60)
    assert fused == []


def test_rrf_handles_one_empty_path() -> None:
    fts_results = [
        PhotoRetrievalCandidate(
            id=1,
            unsplash_photo_id="photo-1",
            unsplash_user_id=None,
            orientation="portrait",
            search_text="test",
            ai_caption="Test",
            has_human=False,
            wallpaper_score=0.5,
            photography_reference_score=0.5,
            vector_score=0.0,
            fts_score=0.70,
        ),
    ]
    fused = reciprocal_rank_fusion([], fts_results, k=60)
    assert len(fused) == 1
    assert fused[0].unsplash_photo_id == "photo-1"
