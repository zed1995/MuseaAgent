from datetime import UTC, datetime

import pytest

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.records import PhotoRetrievalCandidate
from backend.repositories.write_models import PhotoIndexWriteModel


@pytest.mark.postgres
def test_repository_can_recall_candidates_with_orientation_and_has_human_filters(
    session,
) -> None:
    repository = PhotoIndexRepository(session)
    repository.bulk_upsert_index_entries(
        [
            PhotoIndexWriteModel(
                id=2001,
                unsplash_photo_id="portrait-dark-no-human",
                unsplash_user_id="user-1",
                orientation="portrait",
                source_text="dark wallpaper source",
                search_text="dark calm oled wallpaper minimal",
                ai_caption="A dark calm minimal wallpaper.",
                ai_short_caption="Dark wallpaper",
                has_human=False,
                is_minimal=True,
                is_dark=True,
                wallpaper_score=0.95,
                photography_reference_score=0.2,
                embedding=[1.0] * 1536,
                indexed_at=datetime.now(UTC),
            ),
            PhotoIndexWriteModel(
                id=2002,
                unsplash_photo_id="landscape-human",
                unsplash_user_id="user-2",
                orientation="landscape",
                source_text="city night source",
                search_text="dark city night wallpaper",
                ai_caption="A dark city scene with people.",
                ai_short_caption="City at night",
                has_human=True,
                wallpaper_score=0.5,
                photography_reference_score=0.7,
                embedding=[0.3] * 1536,
                indexed_at=datetime.now(UTC),
            ),
        ]
    )
    session.commit()

    candidates = repository.search_full_text(
        query_text="dark wallpaper",
        orientation="portrait",
        has_human=False,
        limit=10,
    )

    assert candidates
    assert all(item.orientation == "portrait" for item in candidates)
    assert all(item.has_human is False for item in candidates)


@pytest.mark.postgres
def test_repository_can_recall_vector_candidates(session) -> None:
    repository = PhotoIndexRepository(session)
    repository.bulk_upsert_index_entries(
        [
            PhotoIndexWriteModel(
                id=2101,
                unsplash_photo_id="closest-vector",
                unsplash_user_id="user-1",
                orientation="portrait",
                source_text="mountain wallpaper source",
                search_text="mountain dark wallpaper",
                ai_caption="A dark mountain wallpaper.",
                ai_short_caption="Mountain wallpaper",
                has_human=False,
                wallpaper_score=0.9,
                photography_reference_score=0.2,
                embedding=[1.0] * 1536,
                indexed_at=datetime.now(UTC),
            ),
            PhotoIndexWriteModel(
                id=2102,
                unsplash_photo_id="farther-vector",
                unsplash_user_id="user-2",
                orientation="portrait",
                source_text="beach wallpaper source",
                search_text="beach bright wallpaper",
                ai_caption="A bright beach wallpaper.",
                ai_short_caption="Beach wallpaper",
                has_human=False,
                wallpaper_score=0.4,
                photography_reference_score=0.4,
                embedding=[0.1] * 1536,
                indexed_at=datetime.now(UTC),
            ),
        ]
    )
    session.commit()

    candidates = repository.search_vector(
        query_embedding=[1.0] * 1536,
        orientation=None,
        has_human=None,
        limit=10,
    )

    assert isinstance(candidates, list)
    assert candidates
    assert all(isinstance(c, PhotoRetrievalCandidate) for c in candidates)
    assert all(c.vector_score >= 0 for c in candidates)
    assert candidates[0].unsplash_photo_id == "closest-vector"
