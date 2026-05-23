import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def postgres_url() -> str:
    return "postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent_test"


@pytest.fixture
def session_factory(postgres_url: str):
    engine = create_engine(postgres_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def session(session_factory):
    with session_factory() as session:
        yield session
        session.rollback()
