# MuseaAgent Phase 4 Retrieval Read Core Design

> Scope: Photo retrieval read core for Phase 4 only

---

## 1. Goal

Phase 4 defines the first standalone retrieval core that reads completed `photo_index` records and turns a user photo-search request into ranked candidates.

This phase is about making retrieval a stable application service before agent orchestration or chat is added on top.

The outcome of Phase 4 should be:

- a clear retrieval request contract
- a retrieval preparation contract for Chinese natural-language requests
- independent vector and full-text recall paths
- a minimal hard-filter contract
- deterministic fusion and rerank behavior
- traceable score breakdowns that later phases can consume

Phase 4 is the first point where MuseaAgent can answer the question:

`Given completed indexed photos, can the backend retrieve reasonable ranked candidates from a Chinese request without depending on the agent graph?`

---

## 2. Scope

Phase 4 covers:

- application-facing retrieval request and response contracts
- retrieval-facing query preparation for photo retrieval
- vector recall from `photo_index.embedding`
- English FTS recall from `photo_index.search_text`
- minimal hard filters for retrieval-time narrowing
- reciprocal-rank fusion of multi-path candidates
- deterministic first-pass rerank
- score breakdowns and retrieval trace artifacts
- service-level error handling for retrieval failures
- unit and integration test expectations for retrieval behavior

Phase 4 does not cover:

- HTTP route design for `/api/search/photos`
- LangGraph node orchestration
- intent classification beyond what retrieval preparation needs
- multi-turn conversation state
- SSE streaming
- critic or retry policy
- photographer search
- LLM rerank
- broad semantic hard filtering over mood, style, color, or composition

---

## 3. Design Principles

### 3.1 Retrieval Must Stand Alone

The retrieval core is a first-class service, not an internal helper buried inside a future agent graph.

Later phases should call retrieval as a stable dependency. They should not reimplement:

- query rewriting
- candidate recall
- score fusion
- deterministic reranking

### 3.2 Hard Filters Stay Minimal

Phase 4 only promotes highly stable constraints into hard filters.

The approved hard filters for this phase are:

- `orientation`
- `has_human`

These are included because they behave closer to objective constraints than aesthetic judgments.

Phase 4 intentionally does not use these as hard filters:

- `mood_tags`
- `style_tags`
- `color_tags`
- `composition_tags`
- `is_dark`
- `is_minimal`

Those signals remain useful, but they belong in query rewrite, FTS matching, or rerank rather than hard exclusion.

### 3.3 English Retrieval Representation

The read path assumes the Phase 3 write path already produced:

- English `search_text`
- embeddings
- stable structured fields

Phase 4 therefore prepares the user request into an English retrieval representation before vector or FTS execution.

### 3.4 Preparation Is a Dedicated Layer

The retrieval core should treat request preparation as a first-class boundary rather than an ad hoc helper.

That means:

- structured request understanding
- rewrite generation for embedding and FTS
- deterministic fallback behavior
- deterministic fusion
- deterministic rerank
- deterministic score breakdowns

This keeps Phase 4 debuggable and makes later agent retries easier to reason about.

### 3.5 Traceability Is a Product Requirement

The retrieval core must return enough structured trace information that later phases can:

- log retrieval behavior
- inspect missed constraints
- compare retrieval variants
- feed critic and evaluation workflows

Traceability is not an implementation detail. It is part of the Phase 4 contract.

---

## 4. Retrieval Core Boundaries

Phase 4 introduces a dedicated retrieval layer with four units:

1. `Retrieval preparation`
2. `Candidate recall`
3. `Fusion`
4. `Deterministic rerank`

The retrieval core accepts one retrieval request and returns one ranked retrieval response.

It does not:

- generate human-facing chat prose
- manage retries
- decide whether the user started a new topic
- persist conversation state

---

## 5. Request Contract

### 5.1 Retrieval Request

The retrieval service should consume a request object with the following fields:

- `query: str`
- `mode: Literal["wallpaper", "reference", "auto"]`
- `limit: int`
- `filters: RetrievalFilterInput`
- `debug: bool`

`mode` remains in the contract even though Phase 4 focuses on photo retrieval only. This allows the rerank layer to adjust use-case preference without adding agent logic.

`limit` is the requested final result count, not the internal candidate count.

`debug` controls whether deeper traces are returned to callers. The service should still compute internal traces consistently regardless of whether all traces are exposed externally.

### 5.2 Retrieval Filter Input

The only supported hard filters in Phase 4 are:

- `orientation: Literal["portrait", "landscape", "squarish"] | None`
- `has_human: bool | None`

Semantics:

- `orientation=None` means do not filter by orientation
- `has_human=False` means explicitly exclude photos tagged as containing people
- `has_human=True` means require photos tagged as containing people
- `has_human=None` means do not filter by human presence

No other hard filter fields should exist in the Phase 4 application contract.

---

## 6. Response Contract

### 6.1 Retrieval Response

The retrieval service returns:

- `normalized_query`
- `applied_filters`
- `candidates_considered`
- `items`
- `trace`

### 6.2 Retrieval Item

Each returned item should include:

- `photo_id`
- `unsplash_photo_id`
- `unsplash_user_id`
- `orientation`
- `search_text`
- `ai_caption`
- `thumbnail_fields_needed_by_later_api_layers`
- `score_breakdown`

Phase 4 is not responsible for the final external API schema, but the retrieval item must already carry enough fields for:

- ranking inspection
- later response generation
- later API payload adaptation

### 6.3 Score Breakdown

Each result item should expose a deterministic score breakdown with these fields:

- `vector_score`
- `fts_score`
- `hybrid_score`
- `metadata_match_score`
- `use_case_score`
- `final_score`

Fields may be `0.0` when a path did not contribute.

### 6.4 Trace

The response trace should include:

- `original_query`
- `normalized_query_text`
- `normalization_notes`
- `rewritten_terms`
- `applied_filters`
- `vector_candidate_count`
- `fts_candidate_count`
- `fused_candidate_count`
- `dropped_candidate_reasons`

This trace is meant for service consumers and logs, not for direct end-user display.

---

## 7. Retrieval Preparation Design

> Note: the original one-step normalization direction in this section has been superseded by the newer two-pass design in [2026-05-24-museaagent-retrieval-preparation-design.md](/Users/zed/Codes/MuseaAgent/docs/superpowers/specs/2026-05-24-museaagent-retrieval-preparation-design.md).

### 7.1 Preparation Objective

Phase 4 preparation is not full intent understanding. Its job is to produce a retrieval-friendly representation for retrieval execution.

It should transform a user query into:

- supported hard filters
- soft preference hints for rerank
- retrieval-friendly English rewrites
- traceable preparation outputs for downstream recall

### 7.2 Input Assumptions

User requests are expected to be:

- frequently Chinese
- colloquial
- sometimes underspecified
- often expressed with visual mood words rather than exact nouns

Examples:

- `我想找深色安静的 OLED 壁纸，不要人物`
- `找一点电影感的城市夜景参考图`
- `适合手机锁屏的极简山景`

### 7.3 Preparation Output

The preparation layer should produce a structure with:

- retrieval filters
- preparation notes
- embedding-friendly rewrite
- FTS-friendly rewrite
- soft signals for rerank

Example:

```text
Input:
我想找深色安静的 OLED 壁纸，不要人物

Output:
normalized_query_text = "dark calm oled wallpaper minimal"
rewritten_terms = ["dark", "calm", "oled", "wallpaper", "minimal"]
filters = {"orientation": "portrait", "has_human": false}
soft_signals = {"prefer_dark": true, "prefer_minimal": true}
```

### 7.4 Preparation Rules

Phase 4 should prefer explicit deterministic rules for:

- removing filler language
- mapping known Chinese retrieval concepts into English terms
- extracting `不要人物` into `has_human=False`
- inferring `portrait` for mobile-wallpaper phrasing such as `手机壁纸`, `锁屏`, `竖屏`

The original Phase 4 direction assumed mostly deterministic behavior. The newer retrieval-preparation design upgrades this into explicit understanding and rewrite stages with deterministic fallback.

### 7.5 Preparation Non-Goals

The preparation layer should not:

- classify deep user intent
- create 2-5 exploratory queries
- decide whether to retry retrieval
- invent unsupported hard filters

Those behaviors belong to later agent phases.

---

## 8. Candidate Recall Design

### 8.1 Shared Preconditions

Both recall paths operate only on rows where:

- `index_status = 'indexed'`
- required retrieval fields are present

### 8.2 Vector Recall

Vector recall uses the normalized English query text to produce one query embedding and search `photo_index.embedding`.

Responsibilities:

- generate one query embedding
- apply supported hard filters in SQL
- return a bounded candidate list with raw similarity scores

Vector recall is responsible for semantic coverage, not exact phrase precision.

### 8.3 Full-Text Recall

FTS recall uses the normalized English query text against `photo_index.search_text`.

Responsibilities:

- generate one English `tsquery`-compatible search input
- apply the same supported hard filters
- return a bounded candidate list with rank scores

FTS is responsible for lexical precision, not broad semantic generalization.

### 8.4 Candidate Limits

Phase 4 should over-fetch internal candidates relative to the final `limit`.

Recommended defaults:

- vector top-k: 80 to 120
- fts top-k: 40 to 80
- fused pool before rerank: 60 to 100

The exact values may be tuned in implementation, but the service must clearly separate:

- internal candidate counts
- final returned item count

---

## 9. Fusion Design

### 9.1 Fusion Method

Phase 4 uses reciprocal-rank fusion as the only fusion method.

Reasons:

- stable across heterogeneous score scales
- easy to reason about
- easy to debug
- good enough for first-pass hybrid retrieval

### 9.2 Fusion Inputs

Fusion consumes:

- ordered vector candidates
- ordered FTS candidates

Fusion does not consume:

- raw aesthetic soft signals
- downstream critique results

### 9.3 Fusion Output

Fusion returns a unique candidate list with:

- merged candidate identity
- inherited path scores
- `hybrid_score`
- provenance markers showing whether the result came from vector, FTS, or both

---

## 10. Deterministic Rerank Design

### 10.1 Purpose

Rerank exists to convert fused candidates into product-oriented results without introducing a second model dependency.

### 10.2 Inputs

Rerank consumes:

- fused hybrid candidates
- applied hard filters
- retrieval `mode`
- preparation soft signals

### 10.3 Score Layers

Phase 4 keeps the following score layers distinct:

- `vector_score`
- `fts_score`
- `hybrid_score`
- `metadata_match_score`
- `use_case_score`
- `final_score`

### 10.4 Metadata Match Score

`metadata_match_score` should only reward satisfaction of supported hard filters and stable structural fit.

In Phase 4 this means:

- exact orientation match
- exact `has_human` match

It should not attempt to numerically encode all semantic tags.

### 10.5 Use-Case Score

`use_case_score` is a lightweight product preference score driven by existing indexed fields:

- prefer higher `wallpaper_score` when `mode="wallpaper"`
- prefer higher `photography_reference_score` when `mode="reference"`
- remain neutral when `mode="auto"`

### 10.6 Final Ranking

The final score should remain deterministic and explainable.

An acceptable first-pass structure is:

```text
final_score =
  0.55 * hybrid_score +
  0.20 * use_case_score +
  0.15 * metadata_match_score +
  0.10 * normalization_alignment_score
```

`normalization_alignment_score` is the place where preparation-derived soft preferences such as `dark`, `minimal`, or `calm` may have small influence through indexed tags or search-text term presence.

The exact coefficients may be tuned during implementation, but the design constraint is:

- hybrid recall remains dominant
- hard-filter satisfaction remains visible
- product-mode fit influences tie-breaking
- soft aesthetic hints must not dominate ranking

---

## 11. Failure and Fallback Behavior

### 11.1 Normalization Failure

If preparation cannot extract supported filters, retrieval should proceed without those filters rather than fail the request.

If preparation cannot produce strong rewrites, it should fall back through deterministic preparation behavior rather than fail the whole request.

### 11.2 Vector Path Failure

If embedding generation or vector search fails:

- do not fail the whole retrieval request immediately
- proceed with FTS-only retrieval
- mark the trace with `vector_path_failed`

### 11.3 FTS Path Failure

If FTS execution fails:

- do not fail the whole retrieval request immediately
- proceed with vector-only retrieval
- mark the trace with `fts_path_failed`

### 11.4 Dual Failure

If both recall paths fail, the retrieval service should return a typed retrieval failure rather than an empty “successful” response.

This distinction matters because later agent layers need to know the difference between:

- no relevant candidates found
- retrieval infrastructure failure

---

## 12. Observability and Logging Contract

Phase 4 should not yet own full evaluation workflows, but it must emit enough structure for later logging.

At minimum, the retrieval response and internal tracing should make it possible to record:

- original query
- normalized query
- applied filters
- vector candidate ids
- fts candidate ids
- fused candidate ids
- final ranked ids
- score breakdowns for top results
- path failure markers
- latency by retrieval stage

This contract allows Phase 5 and later phases to persist `search_logs` without redesigning retrieval internals.

---

## 13. Testing Strategy

Phase 4 requires three levels of tests.

### 13.1 Unit Tests

Unit tests should cover:

- preparation behavior for representative Chinese inputs
- hard-filter extraction
- RRF fusion correctness
- deterministic rerank score ordering

### 13.2 Repository or Query-Layer Tests

Integration tests should cover:

- vector retrieval with hard filters
- FTS retrieval with hard filters
- merged retrieval using indexed fixture rows

### 13.3 Service-Level Tests

Service tests should cover:

- Chinese request to final ranked candidates
- `has_human=False` exclusion behavior
- `orientation=portrait` filtering
- one-path fallback when vector or FTS is unavailable

---

## 14. Acceptance Criteria

Phase 4 is complete when all of the following are true:

- retrieval can be invoked independently of any API route or agent graph
- a Chinese photo-search query can be normalized into an English retrieval representation
- vector and FTS recall both work against Phase 3 indexed records
- the service supports `orientation` and `has_human` as hard filters
- fusion produces one merged candidate set without duplicate final items
- rerank returns explicit score breakdowns for the top results
- retrieval can degrade gracefully when one recall path fails
- test coverage demonstrates end-to-end ranking behavior for representative queries

---

## 15. Out of Scope Follow-Ups

The following belong to later phases and should not be pulled into Phase 4 implementation:

- multi-query planning
- critic-driven retry
- chat response composition
- conversation inheritance of prior constraints
- photographer retrieval
- LLM-based rerank
- broad hard-filter taxonomy over stylistic tags

Keeping these out of Phase 4 is intentional. The goal of this phase is a stable, inspectable retrieval foundation, not an early half-agent.
