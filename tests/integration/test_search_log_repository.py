import pytest

from backend.repositories.search_log_repository import SearchLogRepository
from backend.repositories.write_models import SearchLogWriteModel


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_search_log_create_and_retrieve(session) -> None:
    repository = SearchLogRepository(session)
    entry = repository.create(
        SearchLogWriteModel(id=7001, request_id="req_001", user_id="user_1", query="wallpaper")
    )
    session.commit()

    assert entry.id == 7001
    assert entry.query == "wallpaper"

    retrieved = repository.get_by_request_id("req_001")
    assert retrieved is not None
    assert retrieved.id == 7001
    assert retrieved.query == "wallpaper"


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_search_log_get_by_request_id_returns_none_for_missing(session) -> None:
    repository = SearchLogRepository(session)
    result = repository.get_by_request_id("nonexistent")
    assert result is None
