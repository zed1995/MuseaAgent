# MuseaAgent Phase 3 Ingestion Write Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 3 write path that processes Unsplash source photos through a shared single-photo enrichment pipeline and persists only completed `photo_index` records.

**Architecture:** This phase extends the Phase 2 persistence base into a retrieval-ready indexing write path. First update the persistence contract so `photo_index` can hold completed enrichment outputs, then define the in-memory pipeline contracts, then implement model-facing adapters for translation, semantic enrichment, and embedding behind clear service boundaries, then add a simple orchestrator that atomically writes completed records, and finally expose lightweight operational triggers for cold-start and incremental scheduling.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL/pgvector, pytest

---

## File Structure

### New files to create

- `backend/services/indexing/__init__.py`
- `backend/services/indexing/contracts.py`
- `backend/services/indexing/source_normalizer.py`
- `backend/services/indexing/text_assembly.py`
- `backend/services/indexing/provider_models.py`
- `backend/services/indexing/translation.py`
- `backend/services/indexing/semantic_enrichment.py`
- `backend/services/indexing/scoring.py`
- `backend/services/indexing/embedding.py`
- `backend/services/indexing/validation.py`
- `backend/services/indexing/pipeline.py`
- `backend/services/indexing/scheduler.py`
- `backend/services/indexing/logging.py`
- `backend/services/indexing/factory.py`
- `backend/api/routes/internal_ingestion.py`
- `backend/schemas/internal_ingestion.py`
- `tests/unit/test_indexing_contracts.py`
- `tests/unit/test_source_normalizer.py`
- `tests/unit/test_text_assembly.py`
- `tests/unit/test_validation.py`
- `tests/unit/test_scheduler.py`
- `tests/integration/test_phase_3_photo_index_repository.py`
- `tests/integration/test_indexing_pipeline.py`
- `tests/integration/test_internal_ingestion_routes.py`

### Existing files to modify

- `backend/models/photo_index.py`
- `backend/repositories/records.py`
- `backend/repositories/write_models.py`
- `backend/repositories/photo_index_repository.py`
- `backend/repositories/__init__.py`
- `backend/api/router.py`
- `backend/core/config.py`
- `Makefile`

### New migration file

- `alembic/versions/20260523_0002_phase_3_ingestion_write_path.py`

---

### Task 1: Expand the Completed `photo_index` Contract

**Files:**
- Modify: `backend/models/photo_index.py`
- Modify: `backend/repositories/records.py`
- Modify: `backend/repositories/write_models.py`
- Modify: `backend/repositories/photo_index_repository.py`
- Create: `alembic/versions/20260523_0002_phase_3_ingestion_write_path.py`
- Test: `tests/integration/test_phase_3_photo_index_repository.py`

- [ ] **Step 1: Write the failing integration test for a completed Phase 3 index record**

```python
from datetime import UTC, datetime

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.write_models import PhotoIndexWriteModel


def test_upsert_index_entry_persists_phase_3_completed_fields(session) -> None:
    repository = PhotoIndexRepository(session)

    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=1001,
            unsplash_photo_id="photo-1",
            unsplash_user_id="user-1",
            orientation="landscape",
            source_text="raw source text",
            search_text="dark minimal wallpaper",
            ai_caption="A dark and minimal mountain wallpaper.",
            ai_short_caption="Dark mountain wallpaper",
            scene_tags=["mountain", "night"],
            mood_tags=["calm"],
            style_tags=["minimal"],
            composition_tags=["wide"],
            lighting_tags=["low-light"],
            color_tags=["black", "blue"],
            subject_tags=["mountain"],
            use_case_tags=["wallpaper"],
            dominant_colors=["#000000", "#1d3557"],
            has_human=False,
            has_face=False,
            is_abstract=False,
            is_minimal=True,
            is_dark=True,
            wallpaper_score=0.94,
            photography_reference_score=0.51,
            embedding=[0.1] * 1536,
            indexed_at=datetime.now(UTC),
        )
    )
    session.commit()

    stored = repository.get_by_unsplash_photo_id("photo-1")

    assert stored is not None
    assert stored.ai_caption == "A dark and minimal mountain wallpaper."
    assert stored.scene_tags == ["mountain", "night"]
    assert stored.wallpaper_score == 0.94
    assert stored.indexed_at is not None
```

- [ ] **Step 2: Run the repository test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_phase_3_photo_index_repository.py -v`
Expected: FAIL because the Phase 2 ORM model, write model, record, and repository do not yet support Phase 3 completed fields

- [ ] **Step 3: Add the Phase 3 schema migration for completed enrichment fields**

Create `alembic/versions/20260523_0002_phase_3_ingestion_write_path.py` with an upgrade that adds:

```python
op.add_column("photo_index", sa.Column("ai_caption", sa.Text(), nullable=False))
op.add_column("photo_index", sa.Column("ai_short_caption", sa.Text(), nullable=False))
op.add_column("photo_index", sa.Column("scene_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("mood_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("style_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("composition_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("lighting_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("color_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("subject_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("use_case_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("dominant_colors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
op.add_column("photo_index", sa.Column("has_human", sa.Boolean(), nullable=False, server_default=sa.false()))
op.add_column("photo_index", sa.Column("has_face", sa.Boolean(), nullable=False, server_default=sa.false()))
op.add_column("photo_index", sa.Column("is_abstract", sa.Boolean(), nullable=False, server_default=sa.false()))
op.add_column("photo_index", sa.Column("is_minimal", sa.Boolean(), nullable=False, server_default=sa.false()))
op.add_column("photo_index", sa.Column("is_dark", sa.Boolean(), nullable=False, server_default=sa.false()))
op.add_column("photo_index", sa.Column("wallpaper_score", sa.Float(), nullable=False, server_default="0"))
op.add_column("photo_index", sa.Column("photography_reference_score", sa.Float(), nullable=False, server_default="0"))
```

Also remove Phase 2 process-state coupling from the schema:

```python
op.drop_column("photo_index", "last_error")
op.alter_column("photo_index", "status", new_column_name="index_status")
```

Assume for this migration that existing `photo_index` contents may be rebuilt from source data rather than preserved as in-place completed records. The migration should therefore favor a clean Phase 3 contract over backward compatibility with placeholder rows.

- [ ] **Step 4: Update ORM, repository records, and write models to match the completed record contract**

Update `backend/models/photo_index.py` to expose the new completed-record fields:

```python
ai_caption: Mapped[str] = mapped_column(Text, nullable=False)
ai_short_caption: Mapped[str] = mapped_column(Text, nullable=False)
scene_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
mood_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
style_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
composition_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
lighting_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
color_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
subject_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
use_case_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
dominant_colors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
has_human: Mapped[bool] = mapped_column(Boolean, nullable=False)
has_face: Mapped[bool] = mapped_column(Boolean, nullable=False)
is_abstract: Mapped[bool] = mapped_column(Boolean, nullable=False)
is_minimal: Mapped[bool] = mapped_column(Boolean, nullable=False)
is_dark: Mapped[bool] = mapped_column(Boolean, nullable=False)
wallpaper_score: Mapped[float] = mapped_column(Float, nullable=False)
photography_reference_score: Mapped[float] = mapped_column(Float, nullable=False)
indexed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
```

Update `backend/repositories/write_models.py` and `backend/repositories/records.py` so `PhotoIndexWriteModel` and `PhotoIndexRecord` carry the same fields.

- [ ] **Step 5: Rewrite the repository upsert to persist completed records only**

Update `backend/repositories/photo_index_repository.py` so `upsert_index_entry()` writes the full completed payload in one path:

```python
existing.ai_caption = entry.ai_caption
existing.ai_short_caption = entry.ai_short_caption
existing.scene_tags = entry.scene_tags
existing.mood_tags = entry.mood_tags
existing.style_tags = entry.style_tags
existing.composition_tags = entry.composition_tags
existing.lighting_tags = entry.lighting_tags
existing.color_tags = entry.color_tags
existing.subject_tags = entry.subject_tags
existing.use_case_tags = entry.use_case_tags
existing.dominant_colors = entry.dominant_colors
existing.has_human = entry.has_human
existing.has_face = entry.has_face
existing.is_abstract = entry.is_abstract
existing.is_minimal = entry.is_minimal
existing.is_dark = entry.is_dark
existing.wallpaper_score = entry.wallpaper_score
existing.photography_reference_score = entry.photography_reference_score
existing.embedding = entry.embedding
existing.index_status = "indexed"
existing.indexed_at = entry.indexed_at
```

Remove `mark_failed()` from the repository contract in this phase.

- [ ] **Step 6: Run the repository integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_phase_3_photo_index_repository.py -v`
Expected: PASS

- [ ] **Step 7: Commit the persistence contract slice**

```bash
git add alembic/versions/20260523_0002_phase_3_ingestion_write_path.py backend/models/photo_index.py backend/repositories/records.py backend/repositories/write_models.py backend/repositories/photo_index_repository.py tests/integration/test_phase_3_photo_index_repository.py
git commit -m "feat: expand photo index for phase 3 write path"
```

---

### Task 2: Define In-Memory Indexing Contracts and Validation Rules

**Files:**
- Create: `backend/services/indexing/contracts.py`
- Create: `backend/services/indexing/validation.py`
- Create: `tests/unit/test_indexing_contracts.py`
- Create: `tests/unit/test_validation.py`

- [ ] **Step 1: Write the failing unit test for the pipeline context contract**

```python
from backend.services.indexing.contracts import EnrichmentContext, NormalizedSourcePhoto


def test_enrichment_context_starts_with_empty_artifact_sections() -> None:
    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-1",
            unsplash_user_id="user-1",
            raw_title="Night mountains",
            raw_description=None,
            raw_alt_description="Dark mountain landscape",
            orientation="landscape",
            width=3840,
            height=2160,
            regular_url="https://images.example/photo-1.jpg",
        )
    )

    assert context.text_artifacts.source_text is None
    assert context.semantic_artifacts.ai_caption is None
    assert context.retrieval_artifacts.embedding is None
```

- [ ] **Step 2: Run the unit test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_indexing_contracts.py -v`
Expected: FAIL because the indexing contracts module does not exist yet

- [ ] **Step 3: Define normalized source, artifact sections, and the shared context object**

Create `backend/services/indexing/contracts.py`:

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class NormalizedSourcePhoto:
    unsplash_photo_id: str
    unsplash_user_id: str | None
    raw_title: str | None
    raw_description: str | None
    raw_alt_description: str | None
    orientation: str | None
    width: int | None
    height: int | None
    regular_url: str


@dataclass(slots=True)
class TextArtifacts:
    source_text: str | None = None
    analysis_text: str | None = None
    search_text: str | None = None


@dataclass(slots=True)
class SemanticArtifacts:
    ai_caption: str | None = None
    ai_short_caption: str | None = None
    scene_tags: list[str] = field(default_factory=list)
    mood_tags: list[str] = field(default_factory=list)
    style_tags: list[str] = field(default_factory=list)
    composition_tags: list[str] = field(default_factory=list)
    lighting_tags: list[str] = field(default_factory=list)
    color_tags: list[str] = field(default_factory=list)
    subject_tags: list[str] = field(default_factory=list)
    use_case_tags: list[str] = field(default_factory=list)
    dominant_colors: list[str] = field(default_factory=list)
    has_human: bool | None = None
    has_face: bool | None = None
    is_abstract: bool | None = None
    is_minimal: bool | None = None
    is_dark: bool | None = None
    wallpaper_score: float | None = None
    photography_reference_score: float | None = None


@dataclass(slots=True)
class RetrievalArtifacts:
    embedding: list[float] | None = None


@dataclass(slots=True)
class EnrichmentContext:
    source: NormalizedSourcePhoto
    text_artifacts: TextArtifacts = field(default_factory=TextArtifacts)
    semantic_artifacts: SemanticArtifacts = field(default_factory=SemanticArtifacts)
    retrieval_artifacts: RetrievalArtifacts = field(default_factory=RetrievalArtifacts)
```

- [ ] **Step 4: Write the failing unit test for final validation**

```python
import pytest

from backend.services.indexing.contracts import EnrichmentContext, NormalizedSourcePhoto
from backend.services.indexing.validation import build_completed_index_entry


def test_validation_rejects_missing_search_text() -> None:
    context = EnrichmentContext(
        source=NormalizedSourcePhoto(
            unsplash_photo_id="photo-1",
            unsplash_user_id=None,
            raw_title=None,
            raw_description=None,
            raw_alt_description=None,
            orientation="landscape",
            width=1024,
            height=768,
            regular_url="https://images.example/photo-1.jpg",
        )
    )

    with pytest.raises(ValueError, match="search_text"):
        build_completed_index_entry(context=context, entry_id=1001)
```

- [ ] **Step 5: Implement the final validation helper**

Create `backend/services/indexing/validation.py`:

```python
from datetime import UTC, datetime

from backend.repositories.write_models import PhotoIndexWriteModel


def build_completed_index_entry(*, context, entry_id: int) -> PhotoIndexWriteModel:
    if not context.text_artifacts.search_text:
        raise ValueError("search_text is required")
    if not context.semantic_artifacts.ai_caption:
        raise ValueError("ai_caption is required")
    if context.retrieval_artifacts.embedding is None:
        raise ValueError("embedding is required")

    return PhotoIndexWriteModel(
        id=entry_id,
        unsplash_photo_id=context.source.unsplash_photo_id,
        unsplash_user_id=context.source.unsplash_user_id,
        orientation=context.source.orientation,
        source_text=context.text_artifacts.source_text,
        search_text=context.text_artifacts.search_text,
        ai_caption=context.semantic_artifacts.ai_caption,
        ai_short_caption=context.semantic_artifacts.ai_short_caption or context.semantic_artifacts.ai_caption,
        scene_tags=context.semantic_artifacts.scene_tags,
        mood_tags=context.semantic_artifacts.mood_tags,
        style_tags=context.semantic_artifacts.style_tags,
        composition_tags=context.semantic_artifacts.composition_tags,
        lighting_tags=context.semantic_artifacts.lighting_tags,
        color_tags=context.semantic_artifacts.color_tags,
        subject_tags=context.semantic_artifacts.subject_tags,
        use_case_tags=context.semantic_artifacts.use_case_tags,
        dominant_colors=context.semantic_artifacts.dominant_colors,
        has_human=bool(context.semantic_artifacts.has_human),
        has_face=bool(context.semantic_artifacts.has_face),
        is_abstract=bool(context.semantic_artifacts.is_abstract),
        is_minimal=bool(context.semantic_artifacts.is_minimal),
        is_dark=bool(context.semantic_artifacts.is_dark),
        wallpaper_score=float(context.semantic_artifacts.wallpaper_score or 0.0),
        photography_reference_score=float(context.semantic_artifacts.photography_reference_score or 0.0),
        embedding=context.retrieval_artifacts.embedding,
        indexed_at=datetime.now(UTC),
    )
```

- [ ] **Step 6: Run the contract and validation tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_indexing_contracts.py tests/unit/test_validation.py -v`
Expected: PASS

- [ ] **Step 7: Commit the pipeline contract slice**

```bash
git add backend/services/indexing/contracts.py backend/services/indexing/validation.py tests/unit/test_indexing_contracts.py tests/unit/test_validation.py
git commit -m "feat: add phase 3 indexing contracts"
```

---

### Task 3: Implement Source Normalize and Text Assembly Nodes

**Files:**
- Create: `backend/services/indexing/source_normalizer.py`
- Create: `backend/services/indexing/text_assembly.py`
- Create: `tests/unit/test_source_normalizer.py`
- Create: `tests/unit/test_text_assembly.py`

- [ ] **Step 1: Write the failing unit test for source normalization**

```python
from backend.services.indexing.source_normalizer import normalize_unsplash_photo


def test_normalize_unsplash_photo_extracts_required_fields() -> None:
    payload = {
        "id": "photo-1",
        "user": {"id": "user-1"},
        "description": "Snow mountains at dusk",
        "alt_description": "Snowy mountain landscape",
        "width": 1920,
        "height": 1080,
        "urls": {"regular": "https://images.example/photo-1.jpg"},
    }

    normalized = normalize_unsplash_photo(payload)

    assert normalized.unsplash_photo_id == "photo-1"
    assert normalized.unsplash_user_id == "user-1"
    assert normalized.orientation == "landscape"
    assert normalized.regular_url == "https://images.example/photo-1.jpg"
```

- [ ] **Step 2: Run the source-normalizer test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_source_normalizer.py -v`
Expected: FAIL because the source normalizer does not exist yet

- [ ] **Step 3: Implement the source normalization node**

Create `backend/services/indexing/source_normalizer.py`:

```python
from backend.services.indexing.contracts import NormalizedSourcePhoto


def normalize_unsplash_photo(payload: dict) -> NormalizedSourcePhoto:
    width = payload.get("width")
    height = payload.get("height")
    orientation = None
    if width and height:
        orientation = "landscape" if width >= height else "portrait"

    return NormalizedSourcePhoto(
        unsplash_photo_id=payload["id"],
        unsplash_user_id=payload.get("user", {}).get("id"),
        raw_title=payload.get("title"),
        raw_description=payload.get("description"),
        raw_alt_description=payload.get("alt_description"),
        orientation=orientation,
        width=width,
        height=height,
        regular_url=payload["urls"]["regular"],
    )
```

- [ ] **Step 4: Write the failing unit test for text assembly**

```python
from backend.services.indexing.contracts import NormalizedSourcePhoto
from backend.services.indexing.text_assembly import assemble_text_artifacts


def test_assemble_text_artifacts_combines_available_source_fields() -> None:
    normalized = NormalizedSourcePhoto(
        unsplash_photo_id="photo-1",
        unsplash_user_id="user-1",
        raw_title="Night peak",
        raw_description="A dark mountain under the stars",
        raw_alt_description="Dark mountain wallpaper",
        orientation="landscape",
        width=1920,
        height=1080,
        regular_url="https://images.example/photo-1.jpg",
    )

    artifacts = assemble_text_artifacts(normalized)

    assert artifacts.source_text == "Night peak\nA dark mountain under the stars\nDark mountain wallpaper"
    assert artifacts.analysis_text is not None
```

- [ ] **Step 5: Implement the text-assembly node**

Create `backend/services/indexing/text_assembly.py`:

```python
from backend.services.indexing.contracts import NormalizedSourcePhoto, TextArtifacts


def assemble_text_artifacts(source: NormalizedSourcePhoto) -> TextArtifacts:
    fragments = [
        fragment.strip()
        for fragment in (source.raw_title, source.raw_description, source.raw_alt_description)
        if fragment and fragment.strip()
    ]
    source_text = "\n".join(fragments) if fragments else f"unsplash:{source.unsplash_photo_id}"
    return TextArtifacts(
        source_text=source_text,
        analysis_text=source_text,
    )
```

- [ ] **Step 6: Run the node tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_source_normalizer.py tests/unit/test_text_assembly.py -v`
Expected: PASS

- [ ] **Step 7: Commit the normalization and text slice**

```bash
git add backend/services/indexing/source_normalizer.py backend/services/indexing/text_assembly.py tests/unit/test_source_normalizer.py tests/unit/test_text_assembly.py
git commit -m "feat: add phase 3 source normalization and text assembly"
```

---

### Task 4: Add Translation, Semantic Enrichment, Scoring, and Embedding Interfaces

**Files:**
- Create: `backend/services/indexing/provider_models.py`
- Create: `backend/services/indexing/translation.py`
- Create: `backend/services/indexing/semantic_enrichment.py`
- Create: `backend/services/indexing/scoring.py`
- Create: `backend/services/indexing/embedding.py`
- Modify: `backend/core/config.py`
- Modify: `Makefile`
- Test: `tests/integration/test_indexing_pipeline.py`

- [ ] **Step 1: Write the failing integration test for a completed in-memory pipeline**

```python
from backend.core.id_generator import IdGenerator
from backend.services.indexing.pipeline import IndexingPipeline


def test_indexing_pipeline_builds_completed_index_entry(fake_services) -> None:
    pipeline = IndexingPipeline(
        id_generator=IdGenerator(machine_id=1),
        translator=fake_services.translator,
        enricher=fake_services.enricher,
        scorer=fake_services.scorer,
        embedder=fake_services.embedder,
        repository=fake_services.repository,
    )

    payload = {
        "id": "photo-1",
        "description": "Quiet dark mountain wallpaper",
        "alt_description": "Dark mountain wallpaper",
        "user": {"id": "user-1"},
        "width": 1920,
        "height": 1080,
        "urls": {"regular": "https://images.example/photo-1.jpg"},
    }

    record = pipeline.process_photo(payload)

    assert record.unsplash_photo_id == "photo-1"
    assert record.search_text == "quiet dark mountain wallpaper"
    assert record.ai_caption == "A quiet dark mountain wallpaper."
    assert record.embedding is not None
```

- [ ] **Step 2: Run the pipeline integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py -v`
Expected: FAIL because the pipeline and service interfaces do not exist yet

- [ ] **Step 3: Add provider-facing interfaces for translation, enrichment, scoring, and embedding**

Create service modules with narrow interfaces:

```python
class Translator:
    def to_search_text(self, *, analysis_text: str) -> str: ...


class SemanticEnricher:
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts: ...


class Scorer:
    def score(self, *, semantic_artifacts: SemanticArtifacts) -> SemanticArtifacts: ...


class Embedder:
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]: ...
```

Implement stub-first local versions that are deterministic enough for tests and later replaceable by model-backed implementations.

The production-oriented direction for these interfaces is provider-agnostic adapters with provider and model selection injected through configuration.

- [ ] **Step 4: Add explicit provider request and response models for model-backed nodes**

Create `backend/services/indexing/provider_models.py`:

```python
from dataclasses import dataclass


@dataclass(slots=True)
class TranslationRequest:
    analysis_text: str


@dataclass(slots=True)
class TranslationResponse:
    search_text: str


@dataclass(slots=True)
class SemanticEnrichmentRequest:
    image_url: str
    analysis_text: str
    search_text: str


@dataclass(slots=True)
class EmbeddingRequest:
    search_text: str
    caption: str
    tags: list[str]
```

Use these request and response types inside the adapter modules so model I/O is visible in the design rather than implied.

- [ ] **Step 5: Add configuration placeholders for external enrichment providers**

Update `backend/core/config.py` with provider-friendly settings:

```python
class IndexingSettings(BaseModel):
    translation_provider: str = "stub"
    enrichment_provider: str = "stub"
    embedding_provider: str = "stub"
    translation_model: str = "stub-translation"
    enrichment_model: str = "stub-vision"
    embedding_model: str = "stub-embedding"
    translation_timeout_seconds: float = 10.0
    enrichment_timeout_seconds: float = 20.0
    embedding_timeout_seconds: float = 10.0


class Settings(BaseSettings):
    indexing: IndexingSettings = IndexingSettings()
```

- [ ] **Step 6: Make the model-backed responsibilities concrete in each adapter**

Implement the adapters so their role in external model invocation is explicit:

```python
class StubTranslator(Translator):
    def to_search_text(self, *, analysis_text: str) -> str:
        request = TranslationRequest(analysis_text=analysis_text)
        response = TranslationResponse(search_text=request.analysis_text.strip().lower())
        return response.search_text


class StubSemanticEnricher(SemanticEnricher):
    def enrich(self, *, image_url: str, analysis_text: str, search_text: str) -> SemanticArtifacts:
        request = SemanticEnrichmentRequest(
            image_url=image_url,
            analysis_text=analysis_text,
            search_text=search_text,
        )
        ...


class StubEmbedder(Embedder):
    def embed(self, *, search_text: str, caption: str, tags: list[str]) -> list[float]:
        request = EmbeddingRequest(search_text=search_text, caption=caption, tags=tags)
        ...
```

Production implementations will later be the place where:

- provider SDKs are called
- prompts are assembled
- response payloads are parsed
- auth and timeout settings are applied

- [ ] **Step 7: Encode the recommended Phase 3 model-call topology in the adapter layer**

Implement Task 4 with these fixed assumptions:

- translation is a dedicated text transformation call
- semantic enrichment is a dedicated multimodal call
- scoring remains deterministic local logic
- embedding is a dedicated embedding-model call
- semantic enrichment consumes the normalized Unsplash image URL rather than downloaded image bytes
- embedding consumes `search_text`, `ai_caption`, and selected high-value tags
- provider and model selection are resolved from configuration rather than hard-coded inside the pipeline

Reflect that design directly in the adapter signatures and usage.

- [ ] **Step 8: Add the in-memory pipeline orchestration module**

Create `backend/services/indexing/pipeline.py` with a `process_photo()` method that sequences:

```python
source = normalize_unsplash_photo(payload)
context = EnrichmentContext(source=source)
context.text_artifacts = assemble_text_artifacts(source)
context.text_artifacts.search_text = translator.to_search_text(
    analysis_text=context.text_artifacts.analysis_text or ""
)
context.semantic_artifacts = enricher.enrich(
    image_url=source.regular_url,
    analysis_text=context.text_artifacts.analysis_text or "",
    search_text=context.text_artifacts.search_text or "",
)
context.semantic_artifacts = scorer.score(semantic_artifacts=context.semantic_artifacts)
context.retrieval_artifacts.embedding = embedder.embed(
    search_text=context.text_artifacts.search_text or "",
    caption=context.semantic_artifacts.ai_caption or "",
    tags=context.semantic_artifacts.scene_tags + context.semantic_artifacts.style_tags,
)
entry = build_completed_index_entry(context=context, entry_id=id_generator.next_id())
repository.upsert_index_entry(entry)
return entry
```

- [ ] **Step 9: Run the pipeline integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py -v`
Expected: PASS

- [ ] **Step 10: Commit the enrichment interfaces and pipeline slice**

```bash
git add backend/core/config.py backend/services/indexing/provider_models.py backend/services/indexing/translation.py backend/services/indexing/semantic_enrichment.py backend/services/indexing/scoring.py backend/services/indexing/embedding.py backend/services/indexing/pipeline.py tests/integration/test_indexing_pipeline.py
git commit -m "feat: add phase 3 indexing pipeline orchestration"
```

---

### Task 5: Add Simple Scheduling and Lightweight Run Logging

**Files:**
- Create: `backend/services/indexing/scheduler.py`
- Create: `backend/services/indexing/logging.py`
- Create: `tests/unit/test_scheduler.py`

- [ ] **Step 1: Write the failing unit test for cold-start scheduling**

```python
from backend.services.indexing.scheduler import run_cold_start_import


def test_run_cold_start_import_processes_each_candidate_once(fake_pipeline, caplog) -> None:
    payloads = [{"id": "photo-1"}, {"id": "photo-2"}]

    result = run_cold_start_import(payloads=payloads, pipeline=fake_pipeline)

    assert result.total_candidates == 2
    assert result.succeeded == 2
    assert fake_pipeline.processed_ids == ["photo-1", "photo-2"]
```

- [ ] **Step 2: Run the scheduler test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_scheduler.py -v`
Expected: FAIL because the scheduler module does not exist yet

- [ ] **Step 3: Add lightweight run logging types**

Create `backend/services/indexing/logging.py`:

```python
from dataclasses import dataclass


@dataclass(slots=True)
class IngestionRunResult:
    trigger_type: str
    total_candidates: int
    succeeded: int
    failed: int
```

- [ ] **Step 4: Implement simple cold-start and incremental scheduler helpers**

Create `backend/services/indexing/scheduler.py`:

```python
from backend.services.indexing.logging import IngestionRunResult


def run_cold_start_import(*, payloads: list[dict], pipeline) -> IngestionRunResult:
    succeeded = 0
    failed = 0
    for payload in payloads:
        try:
            pipeline.process_photo(payload)
            succeeded += 1
        except Exception:
            failed += 1
    return IngestionRunResult(
        trigger_type="cold_start",
        total_candidates=len(payloads),
        succeeded=succeeded,
        failed=failed,
    )


def run_incremental_sync(*, payloads: list[dict], pipeline) -> IngestionRunResult:
    succeeded = 0
    failed = 0
    for payload in payloads:
        try:
            pipeline.process_photo(payload)
            succeeded += 1
        except Exception:
            failed += 1
    return IngestionRunResult(
        trigger_type="incremental_sync",
        total_candidates=len(payloads),
        succeeded=succeeded,
        failed=failed,
    )
```

- [ ] **Step 5: Run the scheduler test to verify it passes**

Run: `.venv/bin/pytest tests/unit/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 6: Commit the scheduling slice**

```bash
git add backend/services/indexing/logging.py backend/services/indexing/scheduler.py tests/unit/test_scheduler.py
git commit -m "feat: add phase 3 ingestion scheduling"
```

---

### Task 6: Build the Indexing Pipeline Factory and Dependency Wiring

**Files:**
- Create: `backend/services/indexing/factory.py`
- Modify: `backend/services/__init__.py`
- Modify: `backend/repositories/__init__.py`
- Test: `tests/integration/test_indexing_pipeline.py`

- [ ] **Step 1: Write the failing integration test for building a configured indexing pipeline**

```python
from backend.services.indexing.factory import build_indexing_pipeline


def test_build_indexing_pipeline_returns_pipeline_with_configured_adapters(session_factory, settings) -> None:
    pipeline = build_indexing_pipeline(session_factory=session_factory, settings=settings)

    assert pipeline is not None
    assert pipeline.translator is not None
    assert pipeline.enricher is not None
    assert pipeline.embedder is not None
```

- [ ] **Step 2: Run the factory test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py -v`
Expected: FAIL because the factory module and dependency wiring do not exist yet

- [ ] **Step 3: Add a factory that resolves providers from configuration**

Create `backend/services/indexing/factory.py`:

```python
from backend.services.indexing.embedding import build_embedder
from backend.services.indexing.pipeline import IndexingPipeline
from backend.services.indexing.scoring import build_scorer
from backend.services.indexing.semantic_enrichment import build_semantic_enricher
from backend.services.indexing.translation import build_translator


def build_indexing_pipeline(*, session_factory, settings):
    session = session_factory()
    repository = PhotoIndexRepository(session)

    return IndexingPipeline(
        id_generator=IdGenerator(machine_id=1),
        translator=build_translator(settings.indexing),
        enricher=build_semantic_enricher(settings.indexing),
        scorer=build_scorer(),
        embedder=build_embedder(settings.indexing),
        repository=repository,
    )
```

The factory is the place where:

- provider names are mapped to concrete adapters
- model names are read from configuration
- repository wiring is attached to the pipeline

- [ ] **Step 4: Export the factory through package-level modules if helpful**

Update exports so route modules do not need to know low-level assembly details.

- [ ] **Step 5: Run the factory integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py -v`
Expected: PASS

- [ ] **Step 6: Commit the dependency-wiring slice**

```bash
git add backend/services/indexing/factory.py backend/services/__init__.py backend/repositories/__init__.py tests/integration/test_indexing_pipeline.py
git commit -m "feat: add phase 3 indexing pipeline factory"
```

---

### Task 7: Expose Internal Trigger Routes for Cold Start, Incremental Sync, and Single-Photo Runs

**Files:**
- Create: `backend/api/routes/internal_ingestion.py`
- Create: `backend/schemas/internal_ingestion.py`
- Modify: `backend/api/router.py`
- Create: `tests/integration/test_internal_ingestion_routes.py`

- [ ] **Step 1: Write the failing integration test for internal ingestion routes**

```python
def test_post_internal_ingestion_photo_returns_run_summary(client) -> None:
    response = client.post(
        "/api/internal/ingestion/photo",
        json={
            "payload": {
                "id": "photo-1",
                "description": "Dark mountain wallpaper",
                "alt_description": "Dark mountain wallpaper",
                "user": {"id": "user-1"},
                "width": 1920,
                "height": 1080,
                "urls": {"regular": "https://images.example/photo-1.jpg"},
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["unsplash_photo_id"] == "photo-1"
```

- [ ] **Step 2: Run the route integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_internal_ingestion_routes.py -v`
Expected: FAIL because the internal ingestion route and request schema do not exist yet

- [ ] **Step 3: Add request models for internal ingestion triggers**

Create `backend/schemas/internal_ingestion.py`:

```python
from pydantic import BaseModel


class InternalSinglePhotoRequest(BaseModel):
    payload: dict


class InternalBatchIngestionRequest(BaseModel):
    payloads: list[dict]
```

- [ ] **Step 4: Add internal ingestion routes and attach them to the API router**

Create `backend/api/routes/internal_ingestion.py`:

```python
from fastapi import APIRouter, Depends

from backend.schemas.internal_ingestion import InternalBatchIngestionRequest, InternalSinglePhotoRequest
from backend.services.indexing.factory import build_indexing_pipeline

router = APIRouter(prefix="/internal/ingestion", tags=["internal-ingestion"])


@router.post("/photo")
def ingest_single_photo(request: InternalSinglePhotoRequest, pipeline=Depends(build_indexing_pipeline)):
    return pipeline.process_photo(request.payload)


@router.post("/cold-start")
def start_cold_start(request: InternalBatchIngestionRequest, pipeline=Depends(build_indexing_pipeline)):
    return run_cold_start_import(payloads=request.payloads, pipeline=pipeline)


@router.post("/incremental-sync")
def start_incremental_sync(request: InternalBatchIngestionRequest, pipeline=Depends(build_indexing_pipeline)):
    return run_incremental_sync(payloads=request.payloads, pipeline=pipeline)
```

Update `backend/api/router.py`:

```python
from backend.api.routes.internal_ingestion import router as internal_ingestion_router

api_router.include_router(internal_ingestion_router)
```

- [ ] **Step 5: Run the route integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_internal_ingestion_routes.py -v`
Expected: PASS

- [ ] **Step 6: Commit the internal trigger surface**

```bash
git add backend/api/router.py backend/api/routes/internal_ingestion.py backend/schemas/internal_ingestion.py tests/integration/test_internal_ingestion_routes.py
git commit -m "feat: add phase 3 internal ingestion routes"
```

---

### Task 8: End-to-End Verification and Cleanup

**Files:**
- Modify: `backend/repositories/__init__.py`
- Modify: `backend/services/__init__.py`
- Test: `tests/integration/test_phase_3_photo_index_repository.py`
- Test: `tests/integration/test_indexing_pipeline.py`
- Test: `tests/integration/test_internal_ingestion_routes.py`
- Test: `tests/unit/test_indexing_contracts.py`
- Test: `tests/unit/test_source_normalizer.py`
- Test: `tests/unit/test_text_assembly.py`
- Test: `tests/unit/test_validation.py`
- Test: `tests/unit/test_scheduler.py`

- [ ] **Step 1: Export the new Phase 3 services cleanly**

Update package exports:

```python
from backend.services.indexing.pipeline import IndexingPipeline
from backend.services.indexing.scheduler import run_cold_start_import, run_incremental_sync
```

- [ ] **Step 2: Run the full Phase 3 focused test suite**

Run: `.venv/bin/pytest tests/unit/test_indexing_contracts.py tests/unit/test_source_normalizer.py tests/unit/test_text_assembly.py tests/unit/test_validation.py tests/unit/test_scheduler.py tests/integration/test_phase_3_photo_index_repository.py tests/integration/test_indexing_pipeline.py tests/integration/test_internal_ingestion_routes.py -v`
Expected: PASS

- [ ] **Step 3: Run the broader repository regression suite**

Run: `.venv/bin/pytest tests/integration/test_alembic_migration.py tests/integration/test_photo_index_repository.py tests/integration/test_health.py -v`
Expected: PASS or targeted updates if existing Phase 2 tests still assert outdated `pending` or `failed` process-state behavior

- [ ] **Step 4: Commit the verified Phase 3 slice**

```bash
git add backend/repositories/__init__.py backend/services/__init__.py
git commit -m "feat: finish phase 3 ingestion write path"
```

---

## Self-Review Notes

- Spec coverage:
  - single-photo pipeline nodes are implemented across Tasks 2, 3, and 4
  - model invocation boundaries are made explicit in Task 4
  - completed-record-only persistence is implemented in Task 1 and enforced in Task 2
  - cold start and incremental scheduling are implemented in Task 5
  - lightweight operational logging is implemented in Task 5
  - pipeline dependency wiring is implemented in Task 6
  - internal trigger surfaces are implemented in Task 7
- Placeholder scan:
  - no `TODO` or `TBD` placeholders remain
  - each task names exact files and concrete test commands
- Type consistency:
  - the plan consistently uses `NormalizedSourcePhoto`, `EnrichmentContext`, `PhotoIndexWriteModel`, and `IndexingPipeline`
