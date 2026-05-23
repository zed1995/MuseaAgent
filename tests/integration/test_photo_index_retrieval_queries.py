import pytest

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.records import PhotoRetrievalCandidate


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_repository_can_recall_candidates_with_orientation_and_has_human_filters(
    session,
) -> None:
    repository = PhotoIndexRepository(session)

    candidates = repository.search_full_text(
        query_text="dark wallpaper",
        orientation="portrait",
        has_human=False,
        limit=10,
    )

    assert candidates
    assert all(item.orientation == "portrait" for item in candidates)
    assert all(item.has_human is False for item in candidates)


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_repository_can_recall_vector_candidates(session) -> None:
    repository = PhotoIndexRepository(session)

    candidates = repository.search_vector(
        query_embedding=[0.0] * 1536,
        orientation=None,
        has_human=None,
        limit=10,
    )

    assert isinstance(candidates, list)
    assert all(isinstance(c, PhotoRetrievalCandidate) for c in candidates)
    assert all(c.vector_score >= 0 for c in candidates)
