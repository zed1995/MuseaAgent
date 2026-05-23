import pytest

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.search_log_repository import SearchLogRepository
from backend.repositories.unit_of_work import SqlAlchemyUnitOfWork
from backend.repositories.write_models import PhotoIndexWriteModel, SearchLogWriteModel


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_photo_index_repository_round_trip(session) -> None:
    repository = PhotoIndexRepository(session)
    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1001,
            unsplash_photo_id="photo_1",
            unsplash_user_id="user_1",
            orientation="portrait",
            source_text="中文原文",
            search_text="quiet dark portrait wallpaper",
            embedding=None,
            status="pending",
        )
    )
    session.commit()

    record = repository.get_by_unsplash_photo_id("photo_1")

    assert record is not None
    assert record.search_text == "quiet dark portrait wallpaper"


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_photo_index_repository_mark_indexed(session) -> None:
    from datetime import datetime, timezone

    repository = PhotoIndexRepository(session)
    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1002,
            unsplash_photo_id="photo_2",
            unsplash_user_id=None,
            orientation=None,
            source_text=None,
            search_text="test image",
            embedding=None,
            status="pending",
        )
    )
    session.commit()

    now = datetime.now(timezone.utc)
    repository.mark_indexed(1002, now)
    session.commit()

    record = repository.get_by_id(1002)
    assert record is not None
    assert record.status == "indexed"
    assert record.indexed_at is not None


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_photo_index_repository_mark_failed(session) -> None:
    repository = PhotoIndexRepository(session)
    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1003,
            unsplash_photo_id="photo_3",
            unsplash_user_id=None,
            orientation=None,
            source_text=None,
            search_text="failing image",
            embedding=None,
            status="pending",
        )
    )
    session.commit()

    repository.mark_failed(1003, "connection timeout")
    session.commit()

    record = repository.get_by_id(1003)
    assert record is not None
    assert record.status == "failed"
    assert record.last_error == "connection timeout"


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_unit_of_work_commits_photo_and_search_log_together(session_factory) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.photo_indexes.upsert_index_entry(
            PhotoIndexWriteModel(
                id=2001,
                unsplash_photo_id="photo_uow",
                unsplash_user_id=None,
                orientation=None,
                source_text=None,
                search_text="minimal wallpaper",
                embedding=None,
                status="pending",
            )
        )
        uow.search_logs.create(
            SearchLogWriteModel(
                id=3001,
                request_id="req_uow",
                user_id=None,
                query="minimal wallpaper",
            )
        )
        uow.commit()

    with session_factory() as session:
        photo_repository = PhotoIndexRepository(session)
        log_repository = SearchLogRepository(session)

        assert photo_repository.get_by_unsplash_photo_id("photo_uow") is not None
        assert log_repository.get_by_request_id("req_uow") is not None
