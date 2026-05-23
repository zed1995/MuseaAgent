import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import get_settings


@pytest.fixture
def postgres_url() -> str:
    settings = get_settings()
    return settings.database.url


@pytest.fixture
def session_factory(postgres_url: str):
    engine = create_engine(postgres_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def session(session_factory):
    with session_factory() as session:
        yield session
        session.rollback()
