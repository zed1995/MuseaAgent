# MuseaAgent Phase 2 Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2 persistence foundation for MuseaAgent using PostgreSQL, pgvector, SQLAlchemy, and Alembic, with stable schema, repository boundaries, and transaction ownership.

**Architecture:** This phase builds the persistence layer from the outside in. First establish database infrastructure and migration scaffolding, then define the first schema, then add persistence models, then add repository records and repository implementations, and finally lock transaction boundaries and integration tests. The retrieval, agent, and API layers remain consumers of this persistence contract rather than participants in its internal design.

**Tech Stack:** Python 3.14, PostgreSQL, pgvector, SQLAlchemy 2.x, Alembic, pytest

---

## File Structure

### New files to create

- `backend/core/db.py`
- `backend/core/id_generator.py`
- `backend/core/settings_models.py`
- `backend/repositories/photo_index_repository.py`
- `backend/repositories/conversation_repository.py`
- `backend/repositories/message_repository.py`
- `backend/repositories/search_log_repository.py`
- `backend/repositories/records.py`
- `backend/repositories/write_models.py`
- `backend/repositories/unit_of_work.py`
- `backend/models/__init__.py`
- `backend/models/base.py`
- `backend/models/photo_index.py`
- `backend/models/conversation.py`
- `backend/models/message.py`
- `backend/models/search_log.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/20260523_0001_phase_2_persistence_foundation.py`
- `tests/conftest.py`
- `tests/integration/test_alembic_migration.py`
- `tests/integration/test_photo_index_repository.py`
- `tests/integration/test_conversation_and_message_repositories.py`
- `tests/integration/test_search_log_repository.py`
- `tests/unit/test_id_generator.py`
- `tests/unit/test_repository_records.py`

### Existing files to modify

- `pyproject.toml`
- `backend/core/config.py`
- `backend/repositories/__init__.py`
- `Makefile`

### Optional helper files if implementation prefers explicit helpers

- `tests/integration/helpers.py`

---

## Task 1: Database Infrastructure and Dependency Wiring

**Files:**
- Create: `backend/core/db.py`
- Create: `backend/core/id_generator.py`
- Create: `backend/core/settings_models.py`
- Modify: `backend/core/config.py`
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Test: `tests/unit/test_id_generator.py`

- [ ] **Step 1: Write the failing unit test for Snowflake-style IDs**

```python
from backend.core.id_generator import IdGenerator


def test_id_generator_returns_increasing_bigints() -> None:
    generator = IdGenerator(machine_id=1)

    first = generator.next_id()
    second = generator.next_id()

    assert isinstance(first, int)
    assert isinstance(second, int)
    assert second > first
```

- [ ] **Step 2: Run the unit test to verify it fails**

Run: `make test`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `backend.core.id_generator`

- [ ] **Step 3: Add persistence dependencies and database-oriented dev commands**

Update `pyproject.toml` dependencies to include:

```toml
dependencies = [
    "alembic>=1.16.0,<2.0.0",
    "fastapi>=0.115.0,<1.0.0",
    "pgvector>=0.4.0,<1.0.0",
    "psycopg[binary]>=3.2.0,<4.0.0",
    "pydantic-settings>=2.6.0,<3.0.0",
    "sqlalchemy>=2.0.0,<3.0.0",
    "uvicorn>=0.32.0,<1.0.0",
]
```

Add `make` targets for migrations:

```make
migrate:
	$(VENV_BIN)/alembic upgrade head

revision:
	$(VENV_BIN)/alembic revision --autogenerate -m "$(MSG)"
```

- [ ] **Step 4: Implement database settings and engine/session wiring**

Create `backend/core/settings_models.py`:

```python
from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    url: str
    echo: bool = False
```

Create `backend/core/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings


def create_engine_from_settings(settings: Settings):
    return create_engine(settings.database.url, echo=settings.database.echo, future=True)


def create_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
```

Modify `backend/core/config.py` to add database config:

```python
from backend.core.settings_models import DatabaseSettings


class Settings(BaseSettings):
    app_name: str = "MuseaAgent API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    database: DatabaseSettings = DatabaseSettings(
        url="postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent",
        echo=False,
    )
```

- [ ] **Step 5: Implement the ID generator**

Create `backend/core/id_generator.py`:

```python
import threading
import time


class IdGenerator:
    def __init__(self, machine_id: int) -> None:
        self._machine_id = machine_id & 0x3FF
        self._lock = threading.Lock()
        self._last_ms = -1
        self._sequence = 0

    def next_id(self) -> int:
        with self._lock:
            current_ms = int(time.time() * 1000)
            if current_ms == self._last_ms:
                self._sequence = (self._sequence + 1) & 0xFFF
            else:
                self._sequence = 0
                self._last_ms = current_ms

            return ((current_ms - 1_700_000_000_000) << 22) | (self._machine_id << 12) | self._sequence
```

- [ ] **Step 6: Run the targeted unit test to verify it passes**

Run: `.venv/bin/pytest tests/unit/test_id_generator.py -v`
Expected: PASS

- [ ] **Step 7: Commit the infrastructure slice**

```bash
git add pyproject.toml Makefile backend/core/config.py backend/core/db.py backend/core/id_generator.py backend/core/settings_models.py tests/unit/test_id_generator.py
git commit -m "feat: add phase 2 database infrastructure"
```

---

## Task 2: Alembic Bootstrap and First Schema Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/20260523_0001_phase_2_persistence_foundation.py`
- Create: `backend/models/base.py`
- Create: `tests/conftest.py`
- Test: `tests/integration/test_alembic_migration.py`

- [ ] **Step 1: Write the failing migration smoke test**

```python
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


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
```

- [ ] **Step 2: Run the migration smoke test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_alembic_migration.py -v`
Expected: FAIL because Alembic config, metadata bootstrap, and migrated tables do not exist yet

- [ ] **Step 3: Create the minimal metadata bootstrap needed by Alembic**

Create `backend/models/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 4: Create Alembic bootstrap files**

Create `alembic.ini` with script location and SQLAlchemy URL placeholder:

```ini
[alembic]
script_location = alembic

[loggers]
keys = root,sqlalchemy,alembic
```

Create `alembic/env.py`:

```python
from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.models.base import Base

target_metadata = Base.metadata
```

- [ ] **Step 5: Create the shared database test fixtures needed by integration tests**

Create `tests/conftest.py`:

```python
import pytest


@pytest.fixture
def postgres_url() -> str:
    return "postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent_test"
```

- [ ] **Step 6: Choose the first embedding dimension before writing schema code**

Record the first implementation choice explicitly:

- choose the initial embedding model
- record its vector dimension in the migration and ORM model
- do not proceed with `Vector(...)` declarations until the dimension is concrete

For example, if the first model dimension is `1536`, use:

```python
VECTOR_DIMENSION = 1536
```

- [ ] **Step 7: Write the first migration by hand**

Create `alembic/versions/20260523_0001_phase_2_persistence_foundation.py` with:

```python
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

VECTOR_DIMENSION = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "photo_index",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="unsplash"),
        sa.Column("unsplash_photo_id", sa.Text(), nullable=False),
        sa.Column("unsplash_user_id", sa.Text(), nullable=True),
        sa.Column("orientation", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(VECTOR_DIMENSION), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("unsplash_photo_id", name="uq_photo_index_unsplash_photo_id"),
    )
```

Continue the migration with `conversations`, `messages`, and `search_logs`, plus indexes for:

```python
op.create_index("ix_photo_index_unsplash_user_id", "photo_index", ["unsplash_user_id"])
op.create_index("ix_photo_index_orientation", "photo_index", ["orientation"])
op.execute(
    "CREATE INDEX ix_photo_index_search_text_fts ON photo_index "
    "USING GIN (to_tsvector('english', search_text))"
)
```

- [ ] **Step 8: Add the vector index using the chosen concrete dimension**

After the implementation chooses the first dimension, add a concrete vector index instead of leaving a placeholder:

```python
op.execute(
    "CREATE INDEX ix_photo_index_embedding_hnsw ON photo_index "
    "USING hnsw (embedding vector_cosine_ops)"
)
```

- [ ] **Step 9: Run the migration smoke test again**

Run: `.venv/bin/pytest tests/integration/test_alembic_migration.py -v`
Expected: PASS and inspector shows all four tables

- [ ] **Step 10: Commit the migration slice**

```bash
git add alembic.ini alembic alembic/versions backend/models/base.py tests/conftest.py tests/integration/test_alembic_migration.py
git commit -m "feat: add phase 2 persistence migration"
```

---

## Task 3: SQLAlchemy Persistence Models

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/photo_index.py`
- Create: `backend/models/conversation.py`
- Create: `backend/models/message.py`
- Create: `backend/models/search_log.py`
- Test: `tests/integration/test_alembic_migration.py`

- [ ] **Step 1: Write the failing metadata consistency test**

Add this to `tests/integration/test_alembic_migration.py`:

```python
from backend.models.base import Base


def test_sqlalchemy_metadata_contains_phase_2_tables() -> None:
    table_names = set(Base.metadata.tables)

    assert table_names == {"photo_index", "conversations", "messages", "search_logs"}
```

- [ ] **Step 2: Run the metadata test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_alembic_migration.py::test_sqlalchemy_metadata_contains_phase_2_tables -v`
Expected: FAIL because the concrete ORM table models do not exist yet

- [ ] **Step 3: Implement the persistence models**

Create `backend/models/photo_index.py`:

```python
from sqlalchemy import BigInteger, Text, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from backend.models.base import Base

VECTOR_DIMENSION = 1536


class PhotoIndexOrmModel(Base):
    __tablename__ = "photo_index"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unsplash'"))
    unsplash_photo_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    unsplash_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    orientation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(VECTOR_DIMENSION), nullable=True)
```

Create analogous models for `ConversationOrmModel`, `MessageOrmModel`, and `SearchLogOrmModel`.

- [ ] **Step 4: Register model imports**

Create `backend/models/__init__.py`:

```python
from backend.models.conversation import ConversationOrmModel
from backend.models.message import MessageOrmModel
from backend.models.photo_index import PhotoIndexOrmModel
from backend.models.search_log import SearchLogOrmModel

__all__ = [
    "ConversationOrmModel",
    "MessageOrmModel",
    "PhotoIndexOrmModel",
    "SearchLogOrmModel",
]
```

- [ ] **Step 5: Run the metadata consistency test again**

Run: `.venv/bin/pytest tests/integration/test_alembic_migration.py::test_sqlalchemy_metadata_contains_phase_2_tables -v`
Expected: PASS

- [ ] **Step 6: Commit the model slice**

```bash
git add backend/models tests/integration/test_alembic_migration.py
git commit -m "feat: add persistence models for phase 2"
```

---

## Task 4: Repository Records, Write Models, and Repository Implementations

**Files:**
- Create: `backend/repositories/records.py`
- Create: `backend/repositories/write_models.py`
- Create: `backend/repositories/photo_index_repository.py`
- Create: `backend/repositories/conversation_repository.py`
- Create: `backend/repositories/message_repository.py`
- Create: `backend/repositories/search_log_repository.py`
- Modify: `backend/repositories/__init__.py`
- Test: `tests/unit/test_repository_records.py`
- Test: `tests/integration/test_photo_index_repository.py`
- Test: `tests/integration/test_conversation_and_message_repositories.py`
- Test: `tests/integration/test_search_log_repository.py`

- [ ] **Step 1: Write the failing unit test for repository records**

```python
from backend.repositories.records import PhotoIndexRecord


def test_photo_index_record_keeps_persistence_boundary_clean() -> None:
    record = PhotoIndexRecord(
        id=123,
        source="unsplash",
        unsplash_photo_id="abc",
        unsplash_user_id=None,
        orientation="portrait",
        source_text="原始文本",
        search_text="calm dark wallpaper",
        status="indexed",
        last_error=None,
    )

    assert record.unsplash_photo_id == "abc"
    assert record.search_text == "calm dark wallpaper"
```

- [ ] **Step 2: Run the unit test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_repository_records.py -v`
Expected: FAIL because repository record models do not exist yet

- [ ] **Step 3: Implement repository-facing records and write models**

Create `backend/repositories/records.py`:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PhotoIndexRecord:
    id: int
    source: str
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    source_text: str | None
    search_text: str
    status: str
    last_error: str | None
    indexed_at: datetime | None = None
```

Create `backend/repositories/write_models.py`:

```python
from dataclasses import dataclass


@dataclass(slots=True)
class PhotoIndexWriteModel:
    id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    source_text: str | None
    search_text: str
    embedding: list[float] | None
    status: str


@dataclass(slots=True)
class SearchLogWriteModel:
    id: int
    request_id: str
    user_id: str | None
    query: str
```

- [ ] **Step 4: Implement `PhotoIndexRepository`**

Create `backend/repositories/photo_index_repository.py`:

```python
from sqlalchemy import select

from backend.models.photo_index import PhotoIndexOrmModel
from backend.repositories.records import PhotoIndexRecord


class PhotoIndexRepository:
    def __init__(self, session) -> None:
        self._session = session

    def get_by_id(self, id: int) -> PhotoIndexRecord | None:
        row = self._session.get(PhotoIndexOrmModel, id)
        if row is None:
            return None
        return PhotoIndexRecord(
            id=row.id,
            source=row.source,
            unsplash_photo_id=row.unsplash_photo_id,
            unsplash_user_id=row.unsplash_user_id,
            orientation=row.orientation,
            source_text=row.source_text,
            search_text=row.search_text,
            status=row.status,
            last_error=row.last_error,
            indexed_at=row.indexed_at,
        )
```

Add `get_by_unsplash_photo_id`, `upsert_index_entry`, `bulk_upsert_index_entries`, `mark_indexed`, and `mark_failed`.

- [ ] **Step 5: Implement the remaining repositories**

Create:

- `ConversationRepository`
- `MessageRepository`
- `SearchLogRepository`

Each should:

- accept a session in the constructor
- return record objects rather than ORM rows
- avoid calling `commit()` internally

`SearchLogRepository` should include at least:

- `create(entry: SearchLogWriteModel)`
- `get_by_request_id(request_id: str)`

- [ ] **Step 6: Write and run integration tests for repository behavior**

Use tests like:

```python
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
```

Run:

```bash
.venv/bin/pytest tests/unit/test_repository_records.py tests/integration/test_photo_index_repository.py tests/integration/test_conversation_and_message_repositories.py tests/integration/test_search_log_repository.py -v
```

Expected: PASS

- [ ] **Step 7: Commit the repository slice**

```bash
git add backend/repositories tests/unit/test_repository_records.py tests/integration/test_photo_index_repository.py tests/integration/test_conversation_and_message_repositories.py tests/integration/test_search_log_repository.py
git commit -m "feat: add phase 2 repositories"
```

---

## Task 5: Unit of Work, Transaction Boundaries, and End-to-End Persistence Verification

**Files:**
- Create: `backend/repositories/unit_of_work.py`
- Modify: `tests/conftest.py`
- Modify: `backend/repositories/__init__.py`
- Modify: `tests/integration/test_photo_index_repository.py`
- Modify: `tests/integration/test_conversation_and_message_repositories.py`
- Modify: `tests/integration/test_search_log_repository.py`

- [ ] **Step 1: Write the failing test for coordinated multi-repository commit behavior**

Add this test:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_photo_index_repository.py::test_unit_of_work_commits_photo_and_search_log_together -v`
Expected: FAIL because `SqlAlchemyUnitOfWork` and the coordinated repository commit flow do not exist yet

- [ ] **Step 3: Implement a minimal unit-of-work abstraction**

Create `backend/repositories/unit_of_work.py`:

```python
from contextlib import AbstractContextManager

from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.message_repository import MessageRepository
from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.search_log_repository import SearchLogRepository


class SqlAlchemyUnitOfWork(AbstractContextManager):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def __enter__(self):
        self.session = self._session_factory()
        self.photo_indexes = PhotoIndexRepository(self.session)
        self.conversations = ConversationRepository(self.session)
        self.messages = MessageRepository(self.session)
        self.search_logs = SearchLogRepository(self.session)
        return self

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.session.rollback()
        self.session.close()
```

- [ ] **Step 4: Extend the shared test fixtures with session helpers**

Modify `tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def session_factory(postgres_url: str):
    engine = create_engine(postgres_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def session(session_factory):
    with session_factory() as session:
        yield session
        session.rollback()
```

- [ ] **Step 5: Re-run the transaction-boundary test**

Run: `.venv/bin/pytest tests/integration/test_photo_index_repository.py::test_unit_of_work_commits_photo_and_search_log_together -v`
Expected: PASS

- [ ] **Step 6: Run the full Phase 2 persistence test suite**

Run:

```bash
.venv/bin/pytest tests/unit/test_id_generator.py tests/unit/test_repository_records.py tests/integration/test_alembic_migration.py tests/integration/test_photo_index_repository.py tests/integration/test_conversation_and_message_repositories.py tests/integration/test_search_log_repository.py -v
```

Expected: PASS for the full persistence suite

- [ ] **Step 7: Commit the transaction and verification slice**

```bash
git add backend/repositories/unit_of_work.py tests/conftest.py tests/integration/test_photo_index_repository.py tests/integration/test_conversation_and_message_repositories.py tests/integration/test_search_log_repository.py
git commit -m "feat: add phase 2 transaction boundaries"
```

---

## Plan Self-Review

### Spec Coverage

This plan covers:

- PostgreSQL + `pgvector`
- Alembic migration setup
- first-generation schema for `photo_index`, `conversations`, `messages`, and `search_logs`
- SQLAlchemy persistence models
- repository contracts and implementations
- storage record and write-model separation
- caller-owned transaction boundaries

This plan intentionally does not implement:

- retrieval algorithms
- translation logic
- embedding generation
- agent graph behavior

### Placeholder Scan

The only intentionally deferred decision is which first embedding model to adopt. This plan now requires that decision to be made before writing the migration and ORM vector column declarations, so no placeholder vector dimension should remain in implementation code.

### Type Consistency

The plan consistently uses:

- `BIGINT id`
- `PhotoIndexWriteModel`
- `PhotoIndexRecord`
- repository-owned record mapping
- caller-owned commit behavior

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-23-museaagent-phase-2-persistence-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
