from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.search_log_repository import SearchLogRepository
from backend.repositories.unit_of_work import SqlAlchemyUnitOfWork
from backend.repositories.write_models import PhotoIndexWriteModel, SearchLogWriteModel


_TEST_IDS = {
    "photo_index": [1001, 1002, 1003, 2001],
    "search_logs": [3001],
}


@pytest.fixture
def clean_test_data(postgres_url):
    """Remove test data with known IDs before and after the test."""
    engine = create_engine(postgres_url)
    with engine.begin() as conn:
        _remove_test_data(conn)
    yield
    with engine.begin() as conn:
        _remove_test_data(conn)
    engine.dispose()


def _remove_test_data(conn):
    conn.execute(text("DELETE FROM messages WHERE conv_id = 5001"))
    conn.execute(text("DELETE FROM conversations WHERE id = 5001"))
    conn.execute(text("DELETE FROM search_logs WHERE id IN (3001, 7001)"))
    conn.execute(text("DELETE FROM photo_index WHERE id IN (1001, 1002, 1003, 2001)"))


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


def test_photo_index_repository_mark_indexed(session) -> None:
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


@pytest.mark.usefixtures("clean_test_data")
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
