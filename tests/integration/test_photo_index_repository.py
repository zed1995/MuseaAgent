from datetime import UTC, datetime, timezone

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
            ai_caption="A quiet dark portrait wallpaper.",
            ai_short_caption="Quiet portrait wallpaper",
            embedding=None,
        )
    )
    session.commit()

    record = repository.get_by_unsplash_photo_id("photo_1")

    assert record is not None
    assert record.search_text == "quiet dark portrait wallpaper"
    assert record.index_status == "indexed"


def test_photo_index_repository_upsert_sets_indexed_status(session) -> None:
    repository = PhotoIndexRepository(session)
    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1002,
            unsplash_photo_id="photo_2",
            unsplash_user_id=None,
            orientation=None,
            source_text=None,
            search_text="test image",
            ai_caption="A test image.",
            ai_short_caption="Test image",
            embedding=None,
        )
    )
    session.commit()

    record = repository.get_by_id(1002)
    assert record is not None
    assert record.index_status == "indexed"


def test_photo_index_repository_upsert_with_completed_fields(session) -> None:
    repository = PhotoIndexRepository(session)
    now = datetime.now(UTC)
    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1003,
            unsplash_photo_id="photo_3",
            unsplash_user_id=None,
            orientation=None,
            source_text=None,
            search_text="rich image",
            ai_caption="A rich detailed image with scenic mountains.",
            ai_short_caption="Scenic mountains",
            scene_tags=["mountain", "lake"],
            style_tags=["natural"],
            mood_tags=["peaceful"],
            wallpaper_score=0.95,
            embedding=[0.1] * 1536,
            indexed_at=now,
        )
    )
    session.commit()

    record = repository.get_by_id(1003)
    assert record is not None
    assert record.index_status == "indexed"
    assert record.scene_tags == ["mountain", "lake"]
    assert record.wallpaper_score == 0.95
    assert record.indexed_at is not None


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
                ai_caption="A minimal wallpaper.",
                ai_short_caption="Minimal wallpaper",
                embedding=None,
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
