# MuseaAgent Retrieval Preparation Design

> Scope: Two-pass retrieval preparation for single-request photo search only

---

## 1. Goal

This design defines the ideal retrieval-facing preparation layer that sits in front of the Phase 4 retrieval execution core.

Its purpose is to turn a raw user search request into a stable internal retrieval request before vector recall, full-text recall, fusion, and rerank run.

The key design decision is:

- retrieval owns single-request understanding and rewrite
- agent orchestration owns multi-step planning, retry, and conversation behavior

This layer therefore replaces the current lightweight `query normalization` concept with a stronger two-pass architecture:

1. `Understanding Pass`
2. `Rewrite Pass`

The outcome of this design should be a retrieval front door that is:

- structurally explicit
- English-output consistent
- debuggable by stage
- reusable by both retrieval-only flows and later agent flows

---

## 2. Scope

This design covers:

- the responsibility boundary of retrieval preparation
- the two-pass model architecture
- the input and output contracts for each pass
- hard-filter extraction policy
- soft-preference extraction policy
- generation of embedding-friendly and FTS-friendly rewrites
- fallback behavior when model calls fail
- traceability requirements
- integration with the existing retrieval execution service

This design does not cover:

- vector recall SQL details
- full-text ranking formulas
- fusion algorithms
- rerank formulas
- multi-turn conversation memory
- multi-query planning
- critic or retry logic
- user-facing chat response generation

---

## 3. Design Principles

### 3.1 Retrieval Preparation Belongs to Retrieval

Single-request query understanding is not agent orchestration.

If a user sends one natural-language request, the retrieval system itself must be able to:

- understand the request well enough to extract stable constraints
- represent the request in retrieval-friendly English
- generate the right inputs for vector and FTS recall

This should work even when no agent graph is involved.

### 3.2 Understanding and Rewrite Are Different Jobs

The current normalization problem comes from mixing these concerns:

- understanding what the user means
- deciding how to express that meaning for retrieval

These should be separated into two explicit passes.

### 3.3 Hard Filters Must Remain Conservative

Only stable, objective constraints should become hard filters in this layer.

The approved hard filters remain:

- `orientation`
- `has_human`

Other semantics such as mood, style, color, or “cinematic” remain soft preferences and retrieval hints, not hard exclusion filters.

### 3.4 Retrieval Preparation Produces Internal Meaning First

This layer should first build a stable internal semantic representation.

Only after that should it derive:

- an embedding rewrite
- an FTS rewrite
- lexical terms

The internal representation is the real contract. Rewrites are derived artifacts.

### 3.5 FTS and Embedding Do Not Want the Same Query Shape

One query string should not be forced to serve both channels equally.

The preparation layer should generate:

- a compact semantic rewrite for embeddings
- a lexical rewrite for FTS

This keeps each retrieval path aligned with its strengths.

### 3.6 Failure Must Degrade Gracefully

This layer will eventually call models. That means it must fail in stages rather than as an all-or-nothing step.

The system must be able to:

- fall back from rewrite generation to rule-built rewrites
- fall back from full two-pass preparation to a minimal deterministic preparation path

---

## 4. Retrieval Preparation Boundary

Retrieval preparation is the layer between raw user input and retrieval execution.

It accepts:

- the raw query string
- optional explicit request filters
- retrieval mode hints

It returns:

- a structured understanding result
- a structured rewrite result
- a prepared retrieval request for execution

It does not:

- plan multiple searches
- decide whether to retry
- inherit prior conversation constraints
- judge result quality

Those belong to later agent orchestration.

---

## 5. Two-Pass Architecture

### 5.1 Pass 1: Understanding

The Understanding Pass reads the raw user request and produces a structured semantic representation.

Its only job is to answer:

- what the user is looking for
- which stable hard constraints are present
- which soft preferences are present
- which negative constraints are present
- what use-case mode is implied

It must not generate the final retrieval query text.

### 5.2 Pass 2: Rewrite

The Rewrite Pass consumes the Understanding Pass output and generates retrieval-friendly English expressions.

Its only job is to answer:

- how this request should be expressed for embedding retrieval
- how this request should be expressed for FTS retrieval
- which lexical terms should be explicitly retained
- which negative terms should be preserved for traceability

It must not re-interpret the raw query from scratch.

### 5.3 Why Two Passes

Two passes are preferred because they create clean failure boundaries:

- understanding can be evaluated independently of rewrite quality
- rewrite can be improved without changing semantic extraction logic
- later agent flows can reuse understanding output and generate multiple rewrites from it

This also avoids the current failure mode where one loosely controlled rewrite step is expected to do both understanding and retrieval formatting.

---

## 6. Understanding Pass Contract

### 6.1 Purpose

The Understanding Pass converts the raw query into stable structured meaning.

### 6.2 Output Contract

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
    raw_query: str
    detected_language: Literal["zh", "en", "mixed", "unknown"]
    inferred_mode: Literal["wallpaper", "reference", "generic"]

    hard_filters: HardFilters
    negative_constraints: NegativeConstraints
    soft_preferences: SoftPreferences

    subject_candidates: list[str] = []
    scene_candidates: list[str] = []
    style_candidates: list[str] = []
    mood_candidates: list[str] = []
    color_candidates: list[str] = []

    understanding_notes: list[str] = []
```

### 6.3 Hard Filter Policy

This pass may set:

- `orientation`
- `has_human`

It may infer `orientation="portrait"` only when the query specifically implies mobile-portrait usage, such as:

- `手机壁纸`
- `锁屏`
- `竖屏`

It must not default all wallpaper requests to portrait.

### 6.4 Soft Preference Policy

The following are soft preferences:

- dark
- calm
- minimal
- cinematic
- city night
- abstract
- color families
- composition hints

These should influence rewrite and ranking later, but not become hard filters by default.

### 6.5 Negative Constraint Policy

This pass must explicitly preserve negative constraints such as:

- `不要人物`
- `无人`
- `不要脸`

These constraints must survive later rewrite generation.

### 6.6 Example

Input:

```text
我想找深色安静的 OLED 壁纸，不要人物
```

Output:

```json
{
  "raw_query": "我想找深色安静的 OLED 壁纸，不要人物",
  "detected_language": "zh",
  "inferred_mode": "wallpaper",
  "hard_filters": {
    "orientation": null,
    "has_human": false
  },
  "negative_constraints": {
    "exclude_people": true,
    "exclude_faces": false
  },
  "soft_preferences": {
    "moods": ["calm"],
    "styles": ["minimal"],
    "scenes": [],
    "subjects": [],
    "lighting": [],
    "colors": ["dark"],
    "qualities": ["oled"]
  },
  "subject_candidates": [],
  "scene_candidates": [],
  "style_candidates": ["minimal"],
  "mood_candidates": ["calm"],
  "color_candidates": ["dark"],
  "understanding_notes": [
    "wallpaper use case inferred",
    "exclude-people constraint extracted"
  ]
}
```

---

## 7. Rewrite Pass Contract

### 7.1 Purpose

The Rewrite Pass converts the understanding result into retrieval-friendly English representations.

### 7.2 Output Contract

```python
class RetrievalRewriteResult(BaseModel):
    rewrite_for_embedding: str
    rewrite_for_fts: str
    lexical_terms: list[str]
    negative_terms: list[str]
    rewrite_notes: list[str] = []
```

### 7.3 Rewrite Rules

`rewrite_for_embedding` should:

- be compact
- remain semantically natural
- preserve important constraints
- avoid becoming a noisy keyword dump

`rewrite_for_fts` should:

- preserve key lexical tokens
- make stable search terms explicit
- favor recall-friendly wording for `search_text`

`lexical_terms` should:

- be English
- be deduplicated
- exclude filler words
- preserve nouns, modifiers, and stable scene/style terms

`negative_terms` should preserve excluded concepts for debugging and future filter evolution, even when they are not directly used by SQL filters.

### 7.4 Example

Input:

- the Understanding Pass result above

Output:

```json
{
  "rewrite_for_embedding": "dark calm minimal oled wallpaper with no people",
  "rewrite_for_fts": "dark calm minimal oled wallpaper no people",
  "lexical_terms": ["dark", "calm", "minimal", "oled", "wallpaper"],
  "negative_terms": ["people"],
  "rewrite_notes": [
    "embedding rewrite kept compact semantic phrasing",
    "fts rewrite emphasized lexical recall"
  ]
}
```

---

## 8. Prepared Retrieval Request Contract

The output of the full preparation layer should be:

```python
class PreparedRetrievalRequest(BaseModel):
    understanding: QueryUnderstandingResult
    rewrite: RetrievalRewriteResult
```

This becomes the input contract for retrieval execution.

Retrieval execution should then consume:

- `understanding.hard_filters`
- `rewrite.rewrite_for_embedding`
- `rewrite.rewrite_for_fts`
- `understanding.soft_preferences`

---

## 9. Prompt and Model Behavior Rules

### 9.1 Understanding Pass Rules

The Understanding Pass model must:

- output schema-conforming JSON only
- avoid prose explanations outside the schema
- avoid generating final retrieval query text
- prefer uncertainty to false precision
- keep unstable aesthetics in soft preferences rather than hard filters

### 9.2 Rewrite Pass Rules

The Rewrite Pass model must:

- consume only the structured understanding result
- not reinterpret the raw query from scratch
- output schema-conforming JSON only
- preserve negative constraints explicitly
- keep `rewrite_for_embedding` and `rewrite_for_fts` distinct in style

### 9.3 Validation

Both pass outputs must be schema-validated before use.

If validation fails, the layer must degrade through fallback behavior rather than passing raw model text downstream.

---

## 10. Fallback Strategy

This layer should support three operational paths.

### 10.1 Primary Path

- Understanding Pass succeeds
- Rewrite Pass succeeds
- full prepared request returned

### 10.2 Partial Fallback

- Understanding Pass succeeds
- Rewrite Pass fails

Behavior:

- retain the understanding result
- build conservative rewrites from local deterministic rules
- record a rewrite-fallback note in trace

### 10.3 Full Fallback

- Understanding Pass fails

Behavior:

- fall back to minimal deterministic preparation
- extract only supported hard filters
- generate a simple English retrieval rewrite
- record an understanding-fallback note in trace

The goal is graceful degradation, not all-or-nothing failure.

---

## 11. Traceability Contract

Preparation trace should make it possible to inspect:

- detected language
- inferred mode
- extracted hard filters
- extracted negative constraints
- extracted soft preferences
- understanding notes
- rewrite outputs
- rewrite notes
- which fallback path was used if any

This trace should later feed:

- search logs
- evaluation workflows
- agent debugging

---

## 12. Integration With Existing Retrieval Core

The current retrieval service uses one normalization step before recall.

This design changes that integration to:

1. call preparation service
2. use `rewrite_for_embedding` for query embedding generation
3. use `rewrite_for_fts` for FTS search
4. use `hard_filters` for SQL filtering
5. use `soft_preferences` for rerank alignment
6. include understanding and rewrite traces in retrieval response trace

This keeps retrieval execution unchanged in role, while upgrading the quality and explicitness of its front door.

---

## 13. Testing Strategy

Testing should be separated by concern.

### 13.1 Understanding Pass Tests

Cover:

- schema validation
- hard-filter extraction
- negative-constraint preservation
- mode inference
- Chinese and mixed-language requests

### 13.2 Rewrite Pass Tests

Cover:

- schema validation
- separation between embedding and FTS rewrites
- negative term preservation
- lexical-term generation quality

### 13.3 Fallback Tests

Cover:

- rewrite-pass failure fallback
- understanding-pass failure fallback
- trace markers for degraded paths

### 13.4 Retrieval Integration Tests

Cover:

- prepared request flowing into vector and FTS recall
- hard filters reaching repository queries
- score trace including preparation outputs

---

## 14. Acceptance Criteria

This design is successfully implemented when:

- retrieval preparation is a distinct layer rather than a single normalization helper
- understanding and rewrite are separate passes with separate contracts
- hard filters are preserved even when rewrite generation uses a model
- wallpaper requests are not globally forced to portrait orientation
- retrieval receives distinct embedding and FTS rewrites
- preparation can fall back partially or fully without collapsing the request
- traces make it possible to inspect both understanding and rewrite stages
- the layer can be consumed directly by retrieval-only flows and later agent flows

---

## 15. Non-Goals

This design intentionally does not solve:

- multi-query planning
- conversation-aware refinement
- critique-driven retry
- photographer search preparation
- user-facing answer generation

Those are later orchestration concerns.

The purpose of this design is to make single-request retrieval preparation strong enough that later agent logic can build on it instead of compensating for it.
