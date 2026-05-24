# MuseaAgent Retrieval Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current one-step retrieval normalization layer with a two-pass retrieval preparation layer that performs structured understanding first, rewrite generation second, and feeds distinct embedding and FTS inputs into the existing retrieval core.

**Architecture:** This work is delivered as a focused refactor in front of the existing retrieval execution service. First define the new preparation contracts and service boundary, then add the Understanding Pass, then add the Rewrite Pass, then wire deterministic fallbacks, and finally integrate the prepared request into retrieval execution and tests. Retrieval recall, fusion, and rerank remain downstream consumers rather than being redesigned in this plan.

**Tech Stack:** Python 3.14, Pydantic v2, OpenAI-compatible model adapters, SQLAlchemy 2.x, pytest

---

## File Structure

### New files to create

- `backend/services/retrieval_preparation/__init__.py`
- `backend/services/retrieval_preparation/contracts.py`
- `backend/services/retrieval_preparation/understanding.py`
- `backend/services/retrieval_preparation/rewrite.py`
- `backend/services/retrieval_preparation/fallback.py`
- `backend/services/retrieval_preparation/service.py`
- `tests/unit/test_retrieval_understanding.py`
- `tests/unit/test_retrieval_rewrite.py`
- `tests/unit/test_retrieval_preparation_fallback.py`

### Existing files to modify

- `backend/core/settings_models.py`
- `backend/core/config.py`
- `backend/services/retrieval/service.py`
- `backend/services/retrieval/factory.py`
- `backend/services/retrieval/contracts.py`
- `backend/schemas/search.py`
- `tests/integration/test_retrieval_service.py`
- `Makefile`

### Existing files that may be removed or slimmed down

- `backend/services/retrieval/query_normalization.py`

If removed, its remaining deterministic pieces should move into `backend/services/retrieval_preparation/fallback.py`.

---

### Task 1: Define Retrieval Preparation Contracts and Settings

**Files:**
- Create: `backend/services/retrieval_preparation/contracts.py`
- Modify: `backend/core/settings_models.py`
- Modify: `backend/core/config.py`
- Test: `tests/unit/test_retrieval_understanding.py`

- [ ] **Step 1: Write the failing unit test for the understanding contract**

```python
from backend.services.retrieval_preparation.contracts import QueryUnderstandingResult


def test_query_understanding_result_supports_hard_filters_soft_preferences_and_notes() -> None:
    result = QueryUnderstandingResult(
        raw_query="我想找深色安静的 OLED 壁纸，不要人物",
        detected_language="zh",
        inferred_mode="wallpaper",
        hard_filters={"orientation": None, "has_human": False},
        negative_constraints={"exclude_people": True, "exclude_faces": False},
        soft_preferences={"moods": ["calm"], "styles": ["minimal"], "colors": ["dark"], "qualities": ["oled"]},
        understanding_notes=["wallpaper use case inferred"],
    )

    assert result.hard_filters.has_human is False
    assert result.soft_preferences.colors == ["dark"]
```

- [ ] **Step 2: Run the unit test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_retrieval_understanding.py -v`
Expected: FAIL because the new preparation contracts do not exist yet

- [ ] **Step 3: Add the preparation contracts**

Create `backend/services/retrieval_preparation/contracts.py` with:

```python
class HardFilters(BaseModel):
    orientation: Literal["portrait", "landscape", "squarish"] | None = None
    has_human: bool | None = None


class NegativeConstraints(BaseModel):
    exclude_people: bool = False
    exclude_faces: bool = False


class SoftPreferences(BaseModel):
    moods: list[str] = []
    styles: list[str] = []
    scenes: list[str] = []
    subjects: list[str] = []
    lighting: list[str] = []
    colors: list[str] = []
    qualities: list[str] = []


class QueryUnderstandingResult(BaseModel):
    ...


class RetrievalRewriteResult(BaseModel):
    ...


class PreparedRetrievalRequest(BaseModel):
    understanding: QueryUnderstandingResult
    rewrite: RetrievalRewriteResult
```

- [ ] **Step 4: Add preparation-specific settings**

Extend `backend/core/settings_models.py` with a new settings model:

```python
class RetrievalPreparationSettings(BaseModel):
    enabled: bool = True
    understanding_model: str = "openai/gpt-4.1-mini"
    rewrite_model: str = "openai/gpt-4.1-mini"
    use_model_understanding: bool = True
    use_model_rewrite: bool = True
```

Wire it into `backend/core/config.py`:

```python
class Settings(BaseSettings):
    ...
    retrieval_preparation: RetrievalPreparationSettings = RetrievalPreparationSettings()
```

- [ ] **Step 5: Run the unit test to verify the contract slice passes**

Run: `.venv/bin/pytest tests/unit/test_retrieval_understanding.py -v`
Expected: PASS

- [ ] **Step 6: Commit the contract slice**

```bash
git add backend/services/retrieval_preparation/contracts.py backend/core/settings_models.py backend/core/config.py tests/unit/test_retrieval_understanding.py
git commit -m "feat: add retrieval preparation contracts"
```

---

### Task 2: Implement the Understanding Pass

**Files:**
- Create: `backend/services/retrieval_preparation/understanding.py`
- Test: `tests/unit/test_retrieval_understanding.py`

- [ ] **Step 1: Add failing tests for hard-filter and negative-constraint preservation**

Add tests for:

```python
def test_understanding_extracts_no_people_without_forcing_portrait_wallpaper() -> None:
    ...


def test_understanding_infers_portrait_only_for_mobile_wallpaper_terms() -> None:
    ...


def test_understanding_preserves_soft_preferences_in_structured_fields() -> None:
    ...
```

- [ ] **Step 2: Run the understanding tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_retrieval_understanding.py -v`
Expected: FAIL because the understanding service does not exist yet

- [ ] **Step 3: Implement the Understanding Pass service**

Create `backend/services/retrieval_preparation/understanding.py` with a service like:

```python
class QueryUnderstandingService:
    def __init__(self, model_client=None) -> None:
        self._model_client = model_client

    def understand(self, query: str, mode: str, explicit_filters: RetrievalFilters | None = None) -> QueryUnderstandingResult:
        ...
```

This implementation must:

- preserve `has_human=False` from phrases like `不要人物`
- infer `orientation="portrait"` only for mobile-portrait wording
- infer `inferred_mode`
- preserve mood, style, color, and quality hints as soft preferences

- [ ] **Step 4: Validate and merge explicit request filters**

The Understanding Pass must apply merge rules:

- explicit filters win over inferred filters
- inferred filters fill only missing values
- conflicting override decisions are noted in `understanding_notes`

- [ ] **Step 5: Run the understanding tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_retrieval_understanding.py -v`
Expected: PASS

- [ ] **Step 6: Commit the understanding slice**

```bash
git add backend/services/retrieval_preparation/understanding.py tests/unit/test_retrieval_understanding.py
git commit -m "feat: add retrieval understanding pass"
```

---

### Task 3: Implement the Rewrite Pass

**Files:**
- Create: `backend/services/retrieval_preparation/rewrite.py`
- Test: `tests/unit/test_retrieval_rewrite.py`

- [ ] **Step 1: Write the failing unit test for distinct embedding and FTS rewrites**

```python
from backend.services.retrieval_preparation.rewrite import RetrievalRewriteService
from backend.services.retrieval_preparation.contracts import QueryUnderstandingResult


def test_rewrite_generates_distinct_embedding_and_fts_outputs() -> None:
    service = RetrievalRewriteService()
    understanding = QueryUnderstandingResult(...)

    result = service.rewrite(understanding)

    assert result.rewrite_for_embedding
    assert result.rewrite_for_fts
    assert result.lexical_terms
```

- [ ] **Step 2: Run the rewrite test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_retrieval_rewrite.py -v`
Expected: FAIL because the rewrite service does not exist yet

- [ ] **Step 3: Implement the Rewrite Pass service**

Create `backend/services/retrieval_preparation/rewrite.py`:

```python
class RetrievalRewriteService:
    def __init__(self, model_client=None) -> None:
        self._model_client = model_client

    def rewrite(self, understanding: QueryUnderstandingResult) -> RetrievalRewriteResult:
        ...
```

This implementation must:

- consume the structured understanding result rather than raw query
- produce `rewrite_for_embedding`
- produce `rewrite_for_fts`
- produce `lexical_terms`
- preserve negative constraints in `negative_terms`

- [ ] **Step 4: Add tests for negative-term preservation and lexical deduplication**

Add tests for:

```python
def test_rewrite_preserves_negative_people_constraint() -> None:
    ...


def test_rewrite_lexical_terms_are_english_and_deduplicated() -> None:
    ...
```

- [ ] **Step 5: Run the rewrite tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_retrieval_rewrite.py -v`
Expected: PASS

- [ ] **Step 6: Commit the rewrite slice**

```bash
git add backend/services/retrieval_preparation/rewrite.py tests/unit/test_retrieval_rewrite.py
git commit -m "feat: add retrieval rewrite pass"
```

---

### Task 4: Implement Deterministic Fallbacks

**Files:**
- Create: `backend/services/retrieval_preparation/fallback.py`
- Create: `tests/unit/test_retrieval_preparation_fallback.py`

- [ ] **Step 1: Write the failing test for rewrite-pass fallback**

```python
def test_fallback_can_build_rewrites_from_understanding_result() -> None:
    ...
```

- [ ] **Step 2: Write the failing test for full deterministic fallback**

```python
def test_full_fallback_extracts_supported_filters_and_simple_rewrite() -> None:
    ...
```

- [ ] **Step 3: Run fallback tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_retrieval_preparation_fallback.py -v`
Expected: FAIL because the fallback helpers do not exist yet

- [ ] **Step 4: Implement fallback helpers**

Create `backend/services/retrieval_preparation/fallback.py` with:

```python
def build_rewrite_fallback(understanding: QueryUnderstandingResult) -> RetrievalRewriteResult:
    ...


def build_full_preparation_fallback(query: str, mode: str, explicit_filters: RetrievalFilters | None = None) -> PreparedRetrievalRequest:
    ...
```

These helpers should:

- preserve supported hard filters
- preserve negative constraints
- build simple English rewrites
- mark fallback behavior in notes

- [ ] **Step 5: Run fallback tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_retrieval_preparation_fallback.py -v`
Expected: PASS

- [ ] **Step 6: Commit the fallback slice**

```bash
git add backend/services/retrieval_preparation/fallback.py tests/unit/test_retrieval_preparation_fallback.py
git commit -m "feat: add retrieval preparation fallbacks"
```

---

### Task 5: Add the Unified Preparation Service

**Files:**
- Create: `backend/services/retrieval_preparation/service.py`
- Modify: `backend/services/retrieval/factory.py`
- Test: `tests/integration/test_retrieval_service.py`

- [ ] **Step 1: Write the failing service-level test for successful two-pass preparation**

```python
def test_preparation_service_returns_understanding_and_rewrite() -> None:
    ...
```

- [ ] **Step 2: Write the failing service-level test for partial fallback**

```python
def test_preparation_service_uses_rewrite_fallback_when_rewrite_pass_fails() -> None:
    ...
```

- [ ] **Step 3: Run the relevant tests to verify they fail**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py -v`
Expected: FAIL because retrieval service is still wired to one-step normalization

- [ ] **Step 4: Implement the preparation orchestrator**

Create `backend/services/retrieval_preparation/service.py`:

```python
class RetrievalPreparationService:
    def __init__(self, understanding_service, rewrite_service) -> None:
        ...

    def prepare(self, query: str, mode: str, explicit_filters: RetrievalFilters | None = None) -> PreparedRetrievalRequest:
        ...
```

Behavior:

- run Understanding Pass first
- run Rewrite Pass second
- on rewrite failure, use rewrite fallback
- on understanding failure, use full fallback

- [ ] **Step 5: Wire the factory to build the preparation service**

Update `backend/services/retrieval/factory.py` so retrieval service creation now includes:

```python
preparation_service = RetrievalPreparationService(...)
```

Keep provider wiring localized here rather than leaking raw model clients into retrieval execution code.

- [ ] **Step 6: Run the relevant tests to verify the preparation service passes**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py -v`
Expected: PASS

- [ ] **Step 7: Commit the preparation orchestration slice**

```bash
git add backend/services/retrieval_preparation/service.py backend/services/retrieval/factory.py tests/integration/test_retrieval_service.py
git commit -m "feat: add retrieval preparation service"
```

---

### Task 6: Integrate Preparation Into Retrieval Execution

**Files:**
- Modify: `backend/services/retrieval/service.py`
- Modify: `backend/services/retrieval/contracts.py`
- Modify: `backend/schemas/search.py`
- Test: `tests/integration/test_retrieval_service.py`

- [ ] **Step 1: Write the failing retrieval integration test for dual rewrite usage**

```python
def test_retrieval_service_uses_embedding_and_fts_rewrites_from_prepared_request() -> None:
    ...
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py -v`
Expected: FAIL because retrieval service still assumes one normalized query string

- [ ] **Step 3: Refactor retrieval service to consume prepared requests**

Update `backend/services/retrieval/service.py` so it:

- calls `preparation_service.prepare(...)`
- passes `rewrite_for_embedding` to the embedder
- passes `rewrite_for_fts` to FTS search
- passes `understanding.hard_filters` to both recall paths
- passes `understanding.soft_preferences` to rerank

- [ ] **Step 4: Expand response trace to include preparation-stage visibility**

Update contracts or trace schema to include:

```python
understanding_notes
rewrite_notes
rewrite_for_embedding
rewrite_for_fts
fallback_path
```

- [ ] **Step 5: Run the retrieval integration tests**

Run: `make test-retrieval`
Expected: PASS

- [ ] **Step 6: Commit the retrieval integration slice**

```bash
git add backend/services/retrieval/service.py backend/services/retrieval/contracts.py backend/schemas/search.py tests/integration/test_retrieval_service.py Makefile
git commit -m "feat: integrate retrieval preparation into retrieval execution"
```

---

## Self-Review

- Spec coverage: this plan covers the new two-pass preparation layer, its contracts, fallbacks, and integration with retrieval execution.
- Placeholder scan: each task names files, tests, commands, and concrete responsibilities; no `TBD` or “handle appropriately” placeholders remain.
- Type consistency: `QueryUnderstandingResult`, `RetrievalRewriteResult`, `PreparedRetrievalRequest`, `RetrievalPreparationService`, and retrieval-service integration terminology are used consistently throughout.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-24-museaagent-retrieval-preparation-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
