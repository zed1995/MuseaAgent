import pytest
from sqlalchemy import create_engine, event
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
def session(postgres_url):
    """Isolate each test in a savepoint that always rolls back.

    Tests may call ``session.commit()`` freely — the outer transaction
    is rolled back after the test regardless, leaving the database clean.
    """
    engine = create_engine(postgres_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)()

    session.begin_nested()

    @event.listens_for(session, "after_transaction_create")
    def _recreate_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            connection.begin_nested()

    yield session

    event.remove(session, "after_transaction_create", _recreate_savepoint)
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()
