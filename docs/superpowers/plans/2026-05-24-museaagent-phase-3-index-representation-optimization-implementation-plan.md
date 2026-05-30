# MuseaAgent Phase 3 Index Representation Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Phase 3 indexing pipeline and the Phase 4 retrieval execution path together so richer retrieval-facing representations are persisted and actively consumed in production without curated vocabularies or code-level hardcoded semantic mappings.

**Architecture:** This work keeps the current Phase 3 and Phase 4 boundaries intact while expanding the write-path representation bundle and updating the read path to consume it. First extend the persistence contract with stored representation fields, then add a representation composer inside the indexing pipeline, then route embedding generation through the richer `embedding_text`, then upgrade FTS to search weighted multi-field representations, then update retrieval candidates, traces, and deterministic rerank to consume more structured Phase 3 outputs, and finally add production-oriented verification around logging and fallback behavior. The implementation should reuse existing enrichment output rather than adding handcrafted semantic layers.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2.x, PostgreSQL full-text search, pgvector, pytest

---

## File Structure

### New files to create

- `alembic/versions/20260524_0003_phase_3_index_representation_fields.py`
- `backend/services/indexing/representation.py`
- `tests/unit/test_indexing_representation.py`
- `tests/integration/test_phase_3_index_representation_repository.py`

### Existing files to modify

- `backend/models/photo_index.py`
- `backend/repositories/write_models.py`
- `backend/repositories/records.py`
- `backend/repositories/photo_index_repository.py`
- `backend/services/indexing/contracts.py`
- `backend/services/indexing/pipeline.py`
- `backend/services/indexing/embedding.py`
- `backend/services/indexing/validation.py`
- `backend/services/retrieval/fusion.py`
- `backend/services/retrieval/rerank.py`
- `backend/services/retrieval/service.py`
- `backend/repositories/search_log_repository.py`
- `backend/api/routes/search_debug.py`
- `tests/integration/test_indexing_pipeline.py`
- `tests/integration/test_photo_index_retrieval_queries.py`
- `tests/integration/test_retrieval_service.py`
- `tests/integration/test_search_debug.py`

---

### Task 1: Extend the `photo_index` Persistence Contract With Stored Representation Fields

**Files:**
- Create: `alembic/versions/20260524_0003_phase_3_index_representation_fields.py`
- Modify: `backend/models/photo_index.py`
- Modify: `backend/repositories/write_models.py`
- Modify: `backend/repositories/records.py`
- Test: `tests/integration/test_phase_3_index_representation_repository.py`

- [ ] **Step 1: Write the failing integration test for stored representation fields**

```python
from datetime import UTC, datetime

from backend.repositories.photo_index_repository import PhotoIndexRepository
from backend.repositories.write_models import PhotoIndexWriteModel


def test_repository_persists_phase_3_representation_fields(session) -> None:
    repository = PhotoIndexRepository(session)

    repository.upsert_index_entry(
        PhotoIndexWriteModel(
            id=3101,
            unsplash_photo_id="rep-photo-1",
            unsplash_user_id="user-1",
            orientation="portrait",
            source_text="quiet dark mountain wallpaper",
            search_text="dark mountain wallpaper quiet minimal",
            ai_caption="A quiet dark mountain wallpaper with minimal composition.",
            ai_short_caption="Dark mountain wallpaper",
            scene_tags=["mountain"],
            mood_tags=["quiet"],
            style_tags=["minimal"],
            composition_tags=["negative space"],
            lighting_tags=["low light"],
            color_tags=["dark blue"],
            subject_tags=["mountain"],
            use_case_tags=["wallpaper"],
            dominant_colors=["#111111", "#203040"],
            has_human=False,
            has_face=False,
            is_abstract=False,
            is_minimal=True,
            is_dark=True,
            wallpaper_score=0.95,
            photography_reference_score=0.42,
            retrieval_caption_text="Dark mountain wallpaper. A quiet dark mountain wallpaper with minimal composition.",
            retrieval_tag_text="mountain quiet minimal negative space low light dark blue wallpaper",
            retrieval_document_text="Dark mountain wallpaper. A quiet dark mountain wallpaper with minimal composition. mountain quiet minimal negative space low light dark blue wallpaper.",
            embedding_text="Dark mountain wallpaper. A quiet dark mountain wallpaper with minimal composition. mountain quiet minimal negative space low light dark blue wallpaper.",
            embedding=[0.1] * 1536,
            indexed_at=datetime.now(UTC),
        )
    )
    session.commit()

    stored = repository.get_by_unsplash_photo_id("rep-photo-1")

    assert stored is not None
    assert stored.retrieval_caption_text.startswith("Dark mountain wallpaper")
    assert "negative space" in stored.retrieval_tag_text
    assert stored.embedding_text == stored.retrieval_document_text
```

- [ ] **Step 2: Run the repository integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_phase_3_index_representation_repository.py -v`
Expected: FAIL because the write model, ORM model, and repository record do not yet include stored representation fields

- [ ] **Step 3: Add a new append-only migration for the representation columns**

Create `alembic/versions/20260524_0003_phase_3_index_representation_fields.py` so the `photo_index` table adds:

```python
op.add_column("photo_index", sa.Column("retrieval_caption_text", sa.Text(), nullable=False))
op.add_column("photo_index", sa.Column("retrieval_tag_text", sa.Text(), nullable=False))
op.add_column("photo_index", sa.Column("retrieval_document_text", sa.Text(), nullable=False))
op.add_column("photo_index", sa.Column("embedding_text", sa.Text(), nullable=False))
```

Keep this migration aligned with the existing completed-record assumption: rows may be rebuilt by reindexing rather than preserved as partially compatible placeholders.

- [ ] **Step 4: Update ORM, record, and write model contracts**

Add these fields to `backend/models/photo_index.py`:

```python
retrieval_caption_text: Mapped[str] = mapped_column(Text, nullable=False)
retrieval_tag_text: Mapped[str] = mapped_column(Text, nullable=False)
retrieval_document_text: Mapped[str] = mapped_column(Text, nullable=False)
embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
```

Add matching fields to `PhotoIndexWriteModel` in `backend/repositories/write_models.py` and `PhotoIndexRecord` in `backend/repositories/records.py`.

- [ ] **Step 5: Run the repository integration test to verify it still fails in repository mapping**

Run: `.venv/bin/pytest tests/integration/test_phase_3_index_representation_repository.py -v`
Expected: FAIL because `PhotoIndexRepository.upsert_index_entry()` and record mapping still do not persist or return the new fields

- [ ] **Step 6: Commit the persistence contract update after repository support is complete in Task 4**

```bash
git add alembic/versions/20260524_0003_phase_3_index_representation_fields.py backend/models/photo_index.py backend/repositories/write_models.py backend/repositories/records.py tests/integration/test_phase_3_index_representation_repository.py
git commit -m "feat: extend photo index with retrieval representation fields"
```

---

### Task 2: Add a Generic Representation Composer to the Indexing Layer

**Files:**
- Create: `backend/services/indexing/representation.py`
- Modify: `backend/services/indexing/contracts.py`
- Test: `tests/unit/test_indexing_representation.py`

- [ ] **Step 1: Write the failing unit test for representation assembly**

```python
from backend.services.indexing.contracts import SemanticArtifacts, TextArtifacts
from backend.services.indexing.representation import compose_retrieval_representation


def test_compose_retrieval_representation_builds_all_text_surfaces() -> None:
    text_artifacts = TextArtifacts(
        source_text="quiet dark mountain wallpaper",
        analysis_text="quiet dark mountain wallpaper",
        search_text="dark mountain wallpaper quiet minimal",
    )
    semantic_artifacts = SemanticArtifacts(
        ai_caption="A quiet dark mountain wallpaper with minimal composition.",
        ai_short_caption="Dark mountain wallpaper",
        scene_tags=["mountain"],
        mood_tags=["quiet"],
        style_tags=["minimal"],
        composition_tags=["negative space"],
        lighting_tags=["low light"],
        color_tags=["dark blue"],
        subject_tags=["mountain"],
        use_case_tags=["wallpaper"],
        has_human=False,
        has_face=False,
        is_dark=True,
        is_minimal=True,
    )

    result = compose_retrieval_representation(
        text_artifacts=text_artifacts,
        semantic_artifacts=semantic_artifacts,
        orientation="portrait",
    )

    assert result.retrieval_caption_text.startswith("Dark mountain wallpaper")
    assert "quiet" in result.retrieval_tag_text
    assert "negative space" in result.retrieval_document_text
    assert result.embedding_text
```

- [ ] **Step 2: Run the unit test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_indexing_representation.py -v`
Expected: FAIL because the representation composer does not exist yet

- [ ] **Step 3: Extend indexing contracts with a representation artifact**

Add a new dataclass to `backend/services/indexing/contracts.py`:

```python
@dataclass(slots=True)
class RepresentationArtifacts:
    retrieval_caption_text: str | None = None
    retrieval_tag_text: str | None = None
    retrieval_document_text: str | None = None
    embedding_text: str | None = None
```

Then attach it to `EnrichmentContext`:

```python
representation_artifacts: RepresentationArtifacts = field(default_factory=RepresentationArtifacts)
```

- [ ] **Step 4: Implement a generic representation composer**

Create `backend/services/indexing/representation.py` with:

```python
from backend.services.indexing.contracts import RepresentationArtifacts


def _normalize_fragments(values: list[str | None]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        stripped = " ".join(value.split())
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered in {item.lower() for item in normalized}:
            continue
        normalized.append(stripped)
    return normalized


def _join_fragments(values: list[str | None], separator: str = " ") -> str:
    fragments = _normalize_fragments(values)
    return separator.join(fragments)


def compose_retrieval_representation(*, text_artifacts, semantic_artifacts, orientation: str | None) -> RepresentationArtifacts:
    retrieval_caption_text = _join_fragments(
        [semantic_artifacts.ai_short_caption, semantic_artifacts.ai_caption],
        separator=". ",
    )
    retrieval_tag_text = _join_fragments(
        [
            *semantic_artifacts.scene_tags,
            *semantic_artifacts.mood_tags,
            *semantic_artifacts.style_tags,
            *semantic_artifacts.composition_tags,
            *semantic_artifacts.lighting_tags,
            *semantic_artifacts.color_tags,
            *semantic_artifacts.subject_tags,
            *semantic_artifacts.use_case_tags,
        ]
    )
    retrieval_document_text = _join_fragments(
        [
            text_artifacts.search_text,
            retrieval_caption_text,
            retrieval_tag_text,
        ],
        separator=". ",
    )
    embedding_text = retrieval_document_text
    return RepresentationArtifacts(
        retrieval_caption_text=retrieval_caption_text,
        retrieval_tag_text=retrieval_tag_text,
        retrieval_document_text=retrieval_document_text,
        embedding_text=embedding_text,
    )
```

This is allowed because it defines structural assembly rules only. It does not map terms through any curated vocabulary and does not synthesize semantic phrases from boolean flags in code.

- [ ] **Step 5: Run the unit test to verify it passes**

Run: `.venv/bin/pytest tests/unit/test_indexing_representation.py -v`
Expected: PASS

- [ ] **Step 6: Commit the representation composer**

```bash
git add backend/services/indexing/contracts.py backend/services/indexing/representation.py tests/unit/test_indexing_representation.py
git commit -m "feat: add phase 3 retrieval representation composer"
```

---

### Task 3: Route the Indexing Pipeline Through the Representation Bundle

**Files:**
- Modify: `backend/services/indexing/pipeline.py`
- Modify: `backend/services/indexing/validation.py`
- Modify: `tests/integration/test_indexing_pipeline.py`

- [ ] **Step 1: Write the failing indexing integration test for representation persistence**

Add this test to `tests/integration/test_indexing_pipeline.py`:

```python
def test_indexing_pipeline_builds_retrieval_representation_fields(pipeline) -> None:
    payload = {
        "id": "photo-representation-1",
        "description": "Quiet dark mountain wallpaper",
        "alt_description": "Dark minimal mountain wallpaper",
        "user": {"id": "user-1"},
        "width": 1920,
        "height": 1080,
        "urls": {"regular": "https://images.example/photo-representation-1.jpg"},
    }

    record = pipeline.process_photo(payload)

    assert record.retrieval_caption_text
    assert record.retrieval_tag_text
    assert record.retrieval_document_text
    assert record.embedding_text
```

- [ ] **Step 2: Run the indexing integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py::test_indexing_pipeline_builds_retrieval_representation_fields -v`
Expected: FAIL because the pipeline does not yet compose or persist the representation bundle

- [ ] **Step 3: Update the pipeline to compose representations before embedding**

In `backend/services/indexing/pipeline.py`, import and use the composer:

```python
from backend.services.indexing.representation import compose_retrieval_representation


context.representation_artifacts = compose_retrieval_representation(
    text_artifacts=context.text_artifacts,
    semantic_artifacts=context.semantic_artifacts,
    orientation=context.source.orientation,
)
context.retrieval_artifacts.embedding = self._embedder.embed(
    search_text=context.representation_artifacts.embedding_text or "",
    caption=context.semantic_artifacts.ai_caption or "",
    tags=[],
)
```

The point here is not the parameter names themselves. The point is that the actual semantic embedding input now comes from `embedding_text`.

- [ ] **Step 4: Expand validation to require the representation bundle**

Update `backend/services/indexing/validation.py` to reject missing:

```python
if not context.representation_artifacts.retrieval_caption_text:
    raise ValueError("retrieval_caption_text is required")
if not context.representation_artifacts.retrieval_tag_text:
    raise ValueError("retrieval_tag_text is required")
if not context.representation_artifacts.retrieval_document_text:
    raise ValueError("retrieval_document_text is required")
if not context.representation_artifacts.embedding_text:
    raise ValueError("embedding_text is required")
```

Then persist those values into `PhotoIndexWriteModel`.

- [ ] **Step 5: Run the indexing integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py::test_indexing_pipeline_builds_retrieval_representation_fields -v`
Expected: PASS

- [ ] **Step 6: Commit the pipeline representation flow**

```bash
git add backend/services/indexing/pipeline.py backend/services/indexing/validation.py tests/integration/test_indexing_pipeline.py
git commit -m "feat: route indexing pipeline through retrieval representation bundle"
```

---

### Task 4: Persist and Return the New Representation Fields From the Repository

**Files:**
- Modify: `backend/repositories/photo_index_repository.py`
- Test: `tests/integration/test_phase_3_index_representation_repository.py`

- [ ] **Step 1: Run the repository integration test to confirm repository mapping still fails**

Run: `.venv/bin/pytest tests/integration/test_phase_3_index_representation_repository.py -v`
Expected: FAIL because `upsert_index_entry()` and `_to_record()` do not yet handle the new fields

- [ ] **Step 2: Update repository persistence and read mapping**

In `backend/repositories/photo_index_repository.py`, update `upsert_index_entry()`:

```python
existing.retrieval_caption_text = entry.retrieval_caption_text
existing.retrieval_tag_text = entry.retrieval_tag_text
existing.retrieval_document_text = entry.retrieval_document_text
existing.embedding_text = entry.embedding_text
```

And in the insert path:

```python
retrieval_caption_text=entry.retrieval_caption_text,
retrieval_tag_text=entry.retrieval_tag_text,
retrieval_document_text=entry.retrieval_document_text,
embedding_text=entry.embedding_text,
```

Also return them from `_to_record()` and `_to_retrieval_candidate()` as needed.

- [ ] **Step 3: Run the repository integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_phase_3_index_representation_repository.py -v`
Expected: PASS

- [ ] **Step 4: Commit the repository mapping changes**

```bash
git add backend/repositories/photo_index_repository.py tests/integration/test_phase_3_index_representation_repository.py
git commit -m "feat: persist retrieval representation fields in photo repository"
```

---

### Task 5: Upgrade FTS Recall to Search a Weighted Multi-Field Document

**Files:**
- Modify: `backend/repositories/photo_index_repository.py`
- Modify: `tests/integration/test_photo_index_retrieval_queries.py`

- [ ] **Step 1: Write the failing retrieval repository test for multi-field FTS**

Add this test to `tests/integration/test_photo_index_retrieval_queries.py`:

```python
@pytest.mark.postgres
def test_repository_fts_matches_representation_fields_beyond_search_text(session) -> None:
    repository = PhotoIndexRepository(session)
    repository.bulk_upsert_index_entries(
        [
            PhotoIndexWriteModel(
                id=3201,
                unsplash_photo_id="caption-match",
                unsplash_user_id="user-1",
                orientation="portrait",
                source_text="source",
                search_text="mountain wallpaper",
                ai_caption="A dark minimalist wallpaper with negative space.",
                ai_short_caption="Dark minimalist wallpaper",
                composition_tags=["negative space"],
                color_tags=["dark blue"],
                retrieval_caption_text="Dark minimalist wallpaper. A dark minimalist wallpaper with negative space.",
                retrieval_tag_text="negative space dark blue minimalist wallpaper",
                retrieval_document_text="Dark minimalist wallpaper. A dark minimalist wallpaper with negative space. negative space dark blue minimalist wallpaper.",
                embedding_text="Dark minimalist wallpaper. A dark minimalist wallpaper with negative space. negative space dark blue minimalist wallpaper.",
                has_human=False,
                wallpaper_score=0.9,
                photography_reference_score=0.2,
                embedding=[0.1] * 1536,
                indexed_at=datetime.now(UTC),
            ),
        ]
    )
    session.commit()

    candidates = repository.search_full_text(
        query_text="negative space dark blue wallpaper",
        orientation=None,
        has_human=None,
        limit=10,
    )

    assert candidates
    assert candidates[0].unsplash_photo_id == "caption-match"
```

- [ ] **Step 2: Run the retrieval repository test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_photo_index_retrieval_queries.py::test_repository_fts_matches_representation_fields_beyond_search_text -v`
Expected: FAIL because FTS still searches only `search_text`

- [ ] **Step 3: Replace single-column FTS with a weighted document expression**

In `backend/repositories/photo_index_repository.py`, build a weighted `tsvector` like:

```python
tsvector = (
    func.setweight(func.to_tsvector("english", func.coalesce(PhotoIndexOrmModel.search_text, "")), "A")
    .op("||")(func.setweight(func.to_tsvector("english", func.coalesce(PhotoIndexOrmModel.retrieval_caption_text, "")), "A"))
    .op("||")(func.setweight(func.to_tsvector("english", func.coalesce(PhotoIndexOrmModel.retrieval_tag_text, "")), "B"))
    .op("||")(func.setweight(func.to_tsvector("english", func.coalesce(PhotoIndexOrmModel.retrieval_document_text, "")), "C"))
)
```

Keep the query side generic. Do not add hand-maintained expansion lists.

- [ ] **Step 4: Run the retrieval repository test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_photo_index_retrieval_queries.py::test_repository_fts_matches_representation_fields_beyond_search_text -v`
Expected: PASS

- [ ] **Step 5: Commit the FTS upgrade**

```bash
git add backend/repositories/photo_index_repository.py tests/integration/test_photo_index_retrieval_queries.py
git commit -m "feat: upgrade retrieval fts to weighted multi-field documents"
```

---

### Task 6: Make the Retrieval Candidate and Reranker Consume More Phase 3 Structure

**Files:**
- Modify: `backend/repositories/records.py`
- Modify: `backend/repositories/photo_index_repository.py`
- Modify: `backend/services/retrieval/fusion.py`
- Modify: `backend/services/retrieval/rerank.py`
- Modify: `tests/integration/test_retrieval_service.py`

- [ ] **Step 1: Write the failing rerank-focused integration test**

Add this test to `tests/integration/test_retrieval_service.py`:

```python
def test_retrieval_service_prefers_candidates_matching_structured_phase_3_features() -> None:
    repository = FakeRepository(
        vector_candidates=[
            _candidate(
                id=10,
                photo_id="dark-minimal-match",
                search_text="wallpaper",
                vector_score=0.4,
                wallpaper_score=0.8,
            ),
            _candidate(
                id=11,
                photo_id="generic-wallpaper",
                search_text="wallpaper",
                vector_score=0.4,
                wallpaper_score=0.8,
            ),
        ]
    )
```

Complete it so the first candidate carries `is_dark=True`, `is_minimal=True`, and matching tag arrays while the second does not, then assert the first ranks higher for a dark minimal wallpaper request.

- [ ] **Step 2: Run the retrieval integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py::test_retrieval_service_prefers_candidates_matching_structured_phase_3_features -v`
Expected: FAIL because retrieval candidates and rerank do not yet carry or score these structured fields

- [ ] **Step 3: Extend retrieval candidate shapes with structured Phase 3 fields**

Add these to `PhotoRetrievalCandidate` in `backend/repositories/records.py` and propagate them through:

```python
retrieval_caption_text: str = ""
retrieval_tag_text: str = ""
is_dark: bool = False
is_minimal: bool = False
has_face: bool = False
dominant_colors: list[str] | None = None
scene_tags: list[str] | None = None
style_tags: list[str] | None = None
color_tags: list[str] | None = None
subject_tags: list[str] | None = None
use_case_tags: list[str] | None = None
```

Then update repository mapping and `FusedRetrievalCandidate` to carry them through fusion.

- [ ] **Step 4: Add structured-feature scoring to rerank**

In `backend/services/retrieval/rerank.py`, introduce an additional helper:

```python
def _compute_structured_match_score(candidate, prepared_trace) -> float:
    score = 0.0

    if prepared_trace.get("prefers_dark") and candidate.is_dark:
        score += 0.25
    if prepared_trace.get("prefers_minimal") and candidate.is_minimal:
        score += 0.25
    if prepared_trace.get("exclude_faces") and candidate.has_face is False:
        score += 0.25

    candidate_tag_text = " ".join(
        [
            *(candidate.scene_tags or []),
            *(candidate.style_tags or []),
            *(candidate.color_tags or []),
            *(candidate.subject_tags or []),
            *(candidate.use_case_tags or []),
        ]
    ).lower()
    explicit_terms = [term.lower() for term in prepared_trace.get("user_explicit_terms", [])]
    if explicit_terms and any(term in candidate_tag_text for term in explicit_terms):
        score += 0.25

    return min(score, 1.0)
```

Then blend that score into `final_score`.

This remains compliant with the constraint because the reranker is consuming structured preparation output and stored structured fields directly, not generating semantic expansions in code.

- [ ] **Step 5: Run the retrieval integration test to verify it passes**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py::test_retrieval_service_prefers_candidates_matching_structured_phase_3_features -v`
Expected: PASS

- [ ] **Step 6: Commit the rerank structure upgrade**

```bash
git add backend/repositories/records.py backend/repositories/photo_index_repository.py backend/services/retrieval/fusion.py backend/services/retrieval/rerank.py tests/integration/test_retrieval_service.py
git commit -m "feat: use structured phase 3 signals in retrieval rerank"
```

---

### Task 7: Land the Richer Retrieval Path in Production Traces and Search Logs

**Files:**
- Modify: `backend/services/retrieval/service.py`
- Modify: `backend/api/routes/search_debug.py`
- Modify: `backend/repositories/search_log_repository.py`
- Modify: `tests/integration/test_search_debug.py`
- Modify: `tests/integration/test_retrieval_service.py`

- [ ] **Step 1: Write the failing integration test for production trace visibility**

Add a test to `tests/integration/test_retrieval_service.py` that asserts the retrieval trace shows the new path explicitly:

```python
def test_retrieval_service_trace_reports_representation_driven_execution() -> None:
    repository = FakeRepository(
        fts_candidates=[_candidate(id=21, photo_id="trace-hit", fts_score=0.8)]
    )
    service = RetrievalService(
        repository=repository,
        preparation_service=RetrievalPreparationService(
            understanding_service=_understanding_service(),
            rewrite_service=RetrievalRewriteService(),
        ),
        embedder=FakeEmbedder(),
        reranker=RetrievalReranker(),
        settings=RetrievalSettings(),
    )

    response = service.retrieve(query="深色极简壁纸", mode="wallpaper", limit=5)

    assert response.trace.representation_bundle_used is True
```

- [ ] **Step 2: Run the trace integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py::test_retrieval_service_trace_reports_representation_driven_execution -v`
Expected: FAIL because the trace schema and service output do not yet expose representation-path usage

- [ ] **Step 3: Extend retrieval trace and debug output for production verification**

Update `backend/services/retrieval/service.py` and any trace schema it depends on so the response trace includes:

```python
representation_bundle_used: bool = True
fts_document_version: str = "multi_field_weighted_v1"
rerank_features_used: list[str] = ["structured_phase_3_signals"]
```

Also make `backend/api/routes/search_debug.py` return those fields through the debug surface.

- [ ] **Step 4: Extend search-log persistence so production debugging can confirm the new path**

Update `backend/repositories/search_log_repository.py` and the retrieval-side write path so logged retrieval metadata stores:

```python
{
    "representation_bundle_used": True,
    "fts_document_version": "multi_field_weighted_v1",
    "vector_candidate_count": response.trace.vector_candidate_count,
    "fts_candidate_count": response.trace.fts_candidate_count,
    "fallback_path": response.trace.fallback_path,
}
```

Keep this additive. Do not redesign the logging model.

- [ ] **Step 5: Run the retrieval and debug integration tests to verify they pass**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py tests/integration/test_search_debug.py -v`
Expected: PASS

- [ ] **Step 6: Commit the production trace and logging changes**

```bash
git add backend/services/retrieval/service.py backend/api/routes/search_debug.py backend/repositories/search_log_repository.py tests/integration/test_retrieval_service.py tests/integration/test_search_debug.py
git commit -m "feat: expose representation-driven retrieval behavior in production traces"
```

---

### Task 8: Add End-to-End Regression Coverage for the Richer Representation Path

**Files:**
- Modify: `tests/integration/test_indexing_pipeline.py`
- Modify: `tests/integration/test_photo_index_retrieval_queries.py`
- Modify: `tests/integration/test_retrieval_service.py`

- [ ] **Step 1: Run the focused retrieval and indexing test suite before adding final assertions**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py tests/integration/test_photo_index_retrieval_queries.py tests/integration/test_retrieval_service.py -v`
Expected: PASS on the new slices, with any remaining failures exposing gaps in representation propagation

- [ ] **Step 2: Add regression assertions for no-hardcode representation behavior**

Update the tests so they explicitly assert:

- representation fields are assembled from actual enrichment output rather than static canned phrases
- FTS hits can come from caption/tag/document fields even when `search_text` alone is insufficient
- rerank prefers candidates with stored structured matches for dark/minimal/use-case requests
- vector-only and FTS-only fallback behavior still works after the new production path lands

Use assertions like:

```python
assert "negative space" in record.retrieval_document_text
assert candidates[0].unsplash_photo_id == "caption-match"
assert response.items[0].unsplash_photo_id == "dark-minimal-match"
assert "vector_path_failed" in response.trace.dropped_candidate_reasons
```

- [ ] **Step 3: Run the focused regression suite again**

Run: `.venv/bin/pytest tests/integration/test_indexing_pipeline.py tests/integration/test_photo_index_retrieval_queries.py tests/integration/test_retrieval_service.py -v`
Expected: PASS

- [ ] **Step 4: Commit the regression coverage**

```bash
git add tests/integration/test_indexing_pipeline.py tests/integration/test_photo_index_retrieval_queries.py tests/integration/test_retrieval_service.py
git commit -m "test: cover phase 3 representation-driven retrieval behavior"
```

---

## Self-Review

### Spec Coverage

- Stored retrieval-facing representation fields: covered in Tasks 1, 3, and 4.
- Generic representation composer with no curated vocabulary: covered in Task 2.
- Improved embedding input: covered in Task 3.
- Weighted multi-field FTS: covered in Task 5.
- Structured rerank consumption: covered in Task 6.
- Production trace and logging rollout safety: covered in Task 7.
- Regression coverage and fallback safety: covered in Task 8.

### Placeholder Scan

- No `TODO` or `TBD` placeholders remain.
- Each task names exact files.
- Each verification step includes a concrete command and expected outcome.

### Type Consistency

- `retrieval_caption_text`, `retrieval_tag_text`, `retrieval_document_text`, and `embedding_text` are used consistently across schema, models, pipeline, and tests.
- Structured retrieval fields named in rerank are propagated from repository records through fusion before use.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-24-museaagent-phase-3-index-representation-optimization-implementation-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
