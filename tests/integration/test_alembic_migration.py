from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from backend.models.base import Base


@pytest.mark.skip(reason="requires PostgreSQL with pgvector")
def test_phase_2_migration_creates_core_tables(postgres_url: str) -> None:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", postgres_url)

    command.upgrade(config, "head")

    engine = create_engine(postgres_url)
    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())

    assert "photo_index" in table_names
    assert "conversations" in table_names
    assert "messages" in table_names
    assert "search_logs" in table_names


def test_sqlalchemy_metadata_contains_phase_2_tables() -> None:
    table_names = set(Base.metadata.tables)

    assert table_names == {"photo_index", "conversations", "messages", "search_logs"}
