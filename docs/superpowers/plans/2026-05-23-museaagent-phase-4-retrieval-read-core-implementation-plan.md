# MuseaAgent Phase 4 Retrieval Read Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4 retrieval read core that can normalize Chinese photo-search requests, run vector and full-text recall over Phase 3 indexed records, fuse candidates, and return deterministic ranked results with score breakdowns.

**Architecture:** This phase builds the retrieval core from the inside out. First define retrieval-facing contracts, then add repository-level read primitives for vector and FTS candidate recall, then implement query normalization, then add fusion and rerank, and finally assemble a standalone retrieval service with integration tests. API routes, agent graph nodes, and chat behavior remain outside this phase.

**Tech Stack:** Python 3.14, Pydantic v2, SQLAlchemy 2.x, PostgreSQL/pgvector, pytest

---

## File Structure

### New files to create

- `backend/services/retrieval/__init__.py`
- `backend/services/retrieval/contracts.py`
- `backend/services/retrieval/query_normalization.py`
- `backend/services/retrieval/fusion.py`
- `backend/services/retrieval/rerank.py`
- `backend/services/retrieval/service.py`
- `backend/services/retrieval/factory.py`
- `backend/schemas/search.py`
- `tests/unit/test_query_normalization.py`
- `tests/unit/test_retrieval_fusion.py`
- `tests/unit/test_retrieval_rerank.py`
- `tests/integration/test_photo_index_retrieval_queries.py`
- `tests/integration/test_retrieval_service.py`

### Existing files to modify

- `backend/repositories/photo_index_repository.py`
- `backend/repositories/records.py`
- `backend/repositories/__init__.py`
- `backend/core/config.py`
- `backend/core/settings_models.py`
- `backend/models/photo_index.py`
- `Makefile`

### Optional files if implementation prefers dedicated query helpers

- `backend/services/retrieval/sql.py`
- `tests/integration/fixtures/photo_index_samples.py`

---

### Task 1: Define Retrieval Contracts and Configuration Boundaries

**Files:**
- Create: `backend/services/retrieval/contracts.py`
- Create: `backend/schemas/search.py`
- Modify: `backend/core/settings_models.py`
- Modify: `backend/core/config.py`
- Test: `tests/unit/test_query_normalization.py`

- [ ] **Step 1: Write the failing unit test for the normalization contract**

```python
from backend.services.retrieval.query_normalization import QueryNormalizationService


def test_normalization_extracts_supported_filters_from_chinese_wallpaper_query() -> None:
    service = QueryNormalizationService()

    result = service.normalize(
        query="我想找深色安静的 OLED 壁纸，不要人物",
        mode="wallpaper",
    )

    assert result.normalized_query_text == "dark calm oled wallpaper minimal"
    assert result.filters.orientation == "portrait"
    assert result.filters.has_human is False
    assert "dark" in result.rewritten_terms
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_query_normalization.py -v`
Expected: FAIL because the retrieval contracts and normalization service do not exist yet

- [ ] **Step 3: Add retrieval-facing contracts**

Create `backend/services/retrieval/contracts.py` with Pydantic or dataclass contracts for:

```python
class RetrievalFilters(BaseModel):
    orientation: Literal["portrait", "landscape", "squarish"] | None = None
    has_human: bool | None = None


class NormalizedQuery(BaseModel):
    original_query: str
    normalized_query_text: str
    rewritten_terms: list[str]
    filters: RetrievalFilters
    soft_signals: dict[str, bool | float | str]
    normalization_notes: list[str]


class RetrievalRequest(BaseModel):
    query: str
    mode: Literal["wallpaper", "reference", "auto"] = "auto"
    limit: int = 20
    filters: RetrievalFilters = RetrievalFilters()
    debug: bool = False
```

Create `backend/schemas/search.py` with service-facing response models:

```python
class RetrievalScoreBreakdown(BaseModel):
    vector_score: float = 0.0
    fts_score: float = 0.0
    hybrid_score: float = 0.0
    metadata_match_score: float = 0.0
    use_case_score: float = 0.0
    final_score: float = 0.0


class RetrievalTrace(BaseModel):
    original_query: str
    normalized_query_text: str
    normalization_notes: list[str]
    rewritten_terms: list[str]
    applied_filters: RetrievalFilters
    vector_candidate_count: int = 0
    fts_candidate_count: int = 0
    fused_candidate_count: int = 0
    dropped_candidate_reasons: list[str] = []
```

- [ ] **Step 4: Add retrieval configuration settings**

Extend `backend/core/settings_models.py` with:

```python
class RetrievalSettings(BaseModel):
    vector_candidate_limit: int = 100
    fts_candidate_limit: int = 60
    fused_candidate_limit: int = 80
    default_result_limit: int = 20
```

Wire it into `backend/core/config.py`:

```python
from backend.core.settings_models import RetrievalSettings


class Settings(BaseSettings):
    ...
    retrieval: RetrievalSettings = RetrievalSettings()
```

- [ ] **Step 5: Run the targeted test to confirm the contract slice still fails for the missing implementation**

Run: `.venv/bin/pytest tests/unit/test_query_normalization.py -v`
Expected: FAIL with an import or attribute error for `QueryNormalizationService`, confirming the contract layer is in place but logic is not yet implemented

- [ ] **Step 6: Commit the retrieval contract slice**

```bash
git add backend/services/retrieval/contracts.py backend/schemas/search.py backend/core/settings_models.py backend/core/config.py tests/unit/test_query_normalization.py
git commit -m "feat: add phase 4 retrieval contracts"
```

---

### Task 2: Add Repository Read Primitives for Vector and Full-Text Recall

**Files:**
- Modify: `backend/repositories/photo_index_repository.py`
- Modify: `backend/repositories/records.py`
- Modify: `backend/repositories/__init__.py`
- Modify: `backend/models/photo_index.py`
- Create: `tests/integration/test_photo_index_retrieval_queries.py`

- [ ] **Step 1: Write the failing integration test for filtered vector and FTS recall**

```python
from backend.repositories.photo_index_repository import PhotoIndexRepository


def test_repository_can_recall_candidates_with_orientation_and_has_human_filters(session) -> None:
    repository = PhotoIndexRepository(session)

    candidates = repository.search_full_text(
        query_text="dark wallpaper",
        orientation="portrait",
        has_human=False,
        limit=10,
    )

    assert candidates
    assert all(item.orientation == "portrait" for item in candidates)
    assert all(item.has_human is False for item in candidates)
```

- [ ] **Step 2: Run the integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_photo_index_retrieval_queries.py -v`
Expected: FAIL because retrieval-oriented repository read methods do not exist yet

- [ ] **Step 3: Extend the repository record used by retrieval**

Update `backend/repositories/records.py` to add a retrieval-facing record:

```python
@dataclass(slots=True)
class PhotoRetrievalCandidate:
    id: int
    unsplash_photo_id: str
    unsplash_user_id: str | None
    orientation: str | None
    search_text: str
    ai_caption: str
    has_human: bool
    wallpaper_score: float
    photography_reference_score: float
    vector_score: float = 0.0
    fts_score: float = 0.0
```

- [ ] **Step 4: Implement repository read methods for vector and FTS recall**

Add to `backend/repositories/photo_index_repository.py`:

```python
def search_vector(
    self,
    query_embedding: list[float],
    orientation: str | None,
    has_human: bool | None,
    limit: int,
) -> list[PhotoRetrievalCandidate]:
    ...


def search_full_text(
    self,
    query_text: str,
    orientation: str | None,
    has_human: bool | None,
    limit: int,
) -> list[PhotoRetrievalCandidate]:
    ...
```

Both methods should:

- restrict to `index_status = "indexed"`
- apply `orientation` when provided
- apply `has_human` when provided
- return retrieval candidates with the path-specific score populated

- [ ] **Step 5: Make sure `photo_index` still exposes the fields retrieval needs**

Verify `backend/models/photo_index.py` keeps these columns available to read queries:

```python
orientation
search_text
ai_caption
has_human
wallpaper_score
photography_reference_score
embedding
index_status
```

No schema migration is expected in this phase unless Phase 3 implementation diverged from the accepted design.

- [ ] **Step 6: Run the integration test to verify repository recall works**

Run: `.venv/bin/pytest tests/integration/test_photo_index_retrieval_queries.py -v`
Expected: PASS

- [ ] **Step 7: Commit the repository read slice**

```bash
git add backend/repositories/photo_index_repository.py backend/repositories/records.py backend/repositories/__init__.py backend/models/photo_index.py tests/integration/test_photo_index_retrieval_queries.py
git commit -m "feat: add retrieval repository read primitives"
```

---

### Task 3: Implement Deterministic Query Normalization

**Files:**
- Create: `backend/services/retrieval/query_normalization.py`
- Test: `tests/unit/test_query_normalization.py`

- [ ] **Step 1: Expand the unit test suite to cover the supported normalization cases**

Add tests for:

```python
def test_normalization_infers_portrait_for_mobile_wallpaper_terms() -> None:
    ...


def test_normalization_extracts_has_human_false_from_no_people_phrase() -> None:
    ...


def test_normalization_keeps_reference_mode_without_forcing_orientation() -> None:
    ...
```

- [ ] **Step 2: Run the normalization tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_query_normalization.py -v`
Expected: FAIL because the service logic is not implemented yet

- [ ] **Step 3: Implement a rule-based normalization service**

Create `backend/services/retrieval/query_normalization.py`:

```python
class QueryNormalizationService:
    def normalize(self, query: str, mode: str) -> NormalizedQuery:
        cleaned = self._clean_query(query)
        filters = self._extract_filters(cleaned, mode)
        rewritten_terms = self._rewrite_terms(cleaned, mode, filters)
        return NormalizedQuery(
            original_query=query,
            normalized_query_text=" ".join(rewritten_terms),
            rewritten_terms=rewritten_terms,
            filters=filters,
            soft_signals=self._soft_signals(cleaned, rewritten_terms),
            normalization_notes=self._notes(cleaned, filters, rewritten_terms),
        )
```

The implementation should support deterministic handling for:

- `壁纸`, `手机壁纸`, `锁屏`, `竖屏`
- `不要人物`, `无人`, `no people`
- common descriptive terms such as `深色`, `安静`, `极简`, `电影感`, `夜景`

- [ ] **Step 4: Merge user-supplied request filters with extracted filters**

When the retrieval request already contains explicit filters, implement merge rules:

- explicit request filters win over inferred filters
- inferred filters fill missing values only
- note overrides in `normalization_notes`

- [ ] **Step 5: Run the normalization unit tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_query_normalization.py -v`
Expected: PASS

- [ ] **Step 6: Commit the normalization slice**

```bash
git add backend/services/retrieval/query_normalization.py tests/unit/test_query_normalization.py
git commit -m "feat: add deterministic retrieval query normalization"
```

---

### Task 4: Implement Fusion and Deterministic Rerank

**Files:**
- Create: `backend/services/retrieval/fusion.py`
- Create: `backend/services/retrieval/rerank.py`
- Create: `tests/unit/test_retrieval_fusion.py`
- Create: `tests/unit/test_retrieval_rerank.py`

- [ ] **Step 1: Write the failing unit test for reciprocal-rank fusion**

```python
from backend.services.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_merges_vector_and_fts_candidates_without_duplicates() -> None:
    fused = reciprocal_rank_fusion(
        vector_results=[("photo-1", 0.91), ("photo-2", 0.82)],
        fts_results=[("photo-2", 0.60), ("photo-3", 0.55)],
        k=60,
    )

    ids = [item.photo_id for item in fused]

    assert ids[0] == "photo-2"
    assert len(ids) == 3
    assert len(set(ids)) == 3
```

- [ ] **Step 2: Write the failing unit test for rerank ordering**

```python
from backend.services.retrieval.rerank import RetrievalReranker


def test_rerank_prefers_wallpaper_fit_when_mode_is_wallpaper() -> None:
    reranker = RetrievalReranker()
    ranked = reranker.rank(...)

    assert ranked[0].unsplash_photo_id == "wallpaper-like-result"
    assert ranked[0].score_breakdown.use_case_score > ranked[1].score_breakdown.use_case_score
```

- [ ] **Step 3: Run the fusion and rerank tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_retrieval_fusion.py tests/unit/test_retrieval_rerank.py -v`
Expected: FAIL because the fusion and rerank implementations do not exist yet

- [ ] **Step 4: Implement reciprocal-rank fusion**

Create `backend/services/retrieval/fusion.py`:

```python
def reciprocal_rank_fusion(
    vector_results: list[PhotoRetrievalCandidate],
    fts_results: list[PhotoRetrievalCandidate],
    k: int = 60,
) -> list[FusedRetrievalCandidate]:
    ...
```

The implementation should:

- deduplicate by `unsplash_photo_id`
- preserve path provenance
- retain per-path scores
- compute `hybrid_score`

- [ ] **Step 5: Implement the deterministic reranker**

Create `backend/services/retrieval/rerank.py`:

```python
class RetrievalReranker:
    def rank(
        self,
        candidates: list[FusedRetrievalCandidate],
        mode: str,
        filters: RetrievalFilters,
        soft_signals: dict[str, bool | float | str],
        limit: int,
    ) -> list[RankedRetrievalItem]:
        ...
```

The implementation should:

- compute `metadata_match_score` from `orientation` and `has_human`
- compute `use_case_score` from `wallpaper_score` or `photography_reference_score`
- compute a small `normalization_alignment_score`
- produce `final_score`
- sort descending by `final_score`

- [ ] **Step 6: Run the fusion and rerank tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_retrieval_fusion.py tests/unit/test_retrieval_rerank.py -v`
Expected: PASS

- [ ] **Step 7: Commit the ranking slice**

```bash
git add backend/services/retrieval/fusion.py backend/services/retrieval/rerank.py tests/unit/test_retrieval_fusion.py tests/unit/test_retrieval_rerank.py
git commit -m "feat: add retrieval fusion and rerank"
```

---

### Task 5: Assemble the Retrieval Service and Fallback Behavior

**Files:**
- Create: `backend/services/retrieval/service.py`
- Create: `backend/services/retrieval/factory.py`
- Modify: `Makefile`
- Create: `tests/integration/test_retrieval_service.py`

- [ ] **Step 1: Write the failing integration test for end-to-end retrieval**

```python
from backend.services.retrieval.service import RetrievalService


def test_retrieval_service_returns_ranked_results_for_chinese_wallpaper_query(session) -> None:
    service = RetrievalService(...)

    response = service.retrieve(
        query="我想找深色安静的 OLED 壁纸，不要人物",
        mode="wallpaper",
        limit=5,
    )

    assert response.items
    assert response.applied_filters.has_human is False
    assert response.trace.vector_candidate_count > 0
    assert response.trace.fts_candidate_count > 0
```

- [ ] **Step 2: Write the failing integration test for one-path fallback**

```python
def test_retrieval_service_falls_back_to_fts_when_vector_path_errors(session) -> None:
    service = RetrievalService(... failing_embedder ...)

    response = service.retrieve(
        query="深色壁纸",
        mode="wallpaper",
        limit=5,
    )

    assert response.items
    assert "vector_path_failed" in response.trace.dropped_candidate_reasons
```

- [ ] **Step 3: Run the service integration tests to verify they fail**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py -v`
Expected: FAIL because the retrieval service and composition wiring do not exist yet

- [ ] **Step 4: Implement the retrieval service orchestration**

Create `backend/services/retrieval/service.py`:

```python
class RetrievalService:
    def __init__(self, repository, normalizer, embedder, reranker, settings) -> None:
        ...

    def retrieve(self, query: str, mode: str = "auto", limit: int = 20, filters=None, debug: bool = False):
        normalized = self._normalize(...)
        vector_candidates = self._run_vector_path(normalized)
        fts_candidates = self._run_fts_path(normalized)
        fused = reciprocal_rank_fusion(vector_candidates, fts_candidates)
        ranked = self._rerank(...)
        return self._build_response(...)
```

The service should:

- normalize once per request
- isolate vector and FTS path errors
- fail only when both paths fail
- return trace counts and path failure markers

- [ ] **Step 5: Add a factory helper for later dependency injection**

Create `backend/services/retrieval/factory.py`:

```python
def build_retrieval_service(session: Session, settings: Settings) -> RetrievalService:
    ...
```

This keeps later API and agent integration simple without pulling those layers into this phase.

- [ ] **Step 6: Add a narrow test command to `Makefile`**

Add:

```make
test-retrieval:
	$(VENV_BIN)/pytest tests/unit/test_query_normalization.py tests/unit/test_retrieval_fusion.py tests/unit/test_retrieval_rerank.py tests/integration/test_photo_index_retrieval_queries.py tests/integration/test_retrieval_service.py -v
```

- [ ] **Step 7: Run the full retrieval test slice**

Run: `make test-retrieval`
Expected: PASS

- [ ] **Step 8: Commit the retrieval service slice**

```bash
git add backend/services/retrieval/service.py backend/services/retrieval/factory.py Makefile tests/integration/test_retrieval_service.py
git commit -m "feat: add phase 4 retrieval service"
```

---

## Self-Review

- Spec coverage: this plan covers the accepted Phase 4 scope only: contracts, normalization, vector recall, FTS recall, fusion, rerank, traceability, and fallback behavior.
- Placeholder scan: no step says “TBD”, “handle appropriately”, or “similar to above”; each task names files, tests, commands, and the intended implementation slice.
- Type consistency: the plan uses one consistent vocabulary for `RetrievalFilters`, `NormalizedQuery`, retrieval candidates, fused candidates, ranked items, and retrieval response/trace objects.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-23-museaagent-phase-4-retrieval-read-core-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
