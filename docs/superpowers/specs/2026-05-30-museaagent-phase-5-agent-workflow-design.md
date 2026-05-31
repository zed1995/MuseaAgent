# MuseaAgent Phase 5 Agent Workflow Design

> Scope: LangGraph orchestration for agentic photo search built on top of Phase 4 primitives

---

## 1. Goal

Phase 5 turns the Phase 4 debug-oriented search primitives into a real agent workflow.

The key design decision is:

- Phase 4 provides reusable atomic capabilities and a debug surface
- Phase 5 composes those capabilities into an explicit LangGraph workflow

This phase is not about replacing the retrieval core or hiding all prior work behind one large search node.

It is about making the system capable of:

- understanding a request as a search task
- extracting structured constraints
- planning one or more search attempts
- executing those attempts through reusable search primitives
- judging result quality
- retrying once in a controlled way when needed
- returning final items with a short explanation

The outcome of Phase 5 should be the first true MuseaAgent workflow that can automatically decide what to do next instead of relying on a manually stitched debug path.

---

## 2. Scope

Phase 5 covers:

- the responsibility boundary between Phase 4 and Phase 5
- graph state design for agent workflow execution
- graph node boundaries and their input/output contracts
- use of Phase 4 primitives as graph-executed search capabilities
- controlled conditional routing
- single-retry policy
- final response composition for product-facing use
- traceability needed for debugging and evaluation

Phase 5 does not cover:

- reimplementation of vector search, FTS, fusion, or deterministic retrieval rerank
- conversation persistence or full multi-turn memory
- SSE streaming transport details
- photographer discovery workflow
- unrestricted autonomous planning
- multi-step tool loops beyond one controlled retry

---

## 3. Relationship to Phase 4

### 3.1 Phase 4 Is Not the Final Agent

Phase 4 should be treated as:

- `agent primitives`
- `retrieval-facing helpers`
- `debug interfaces`

It is intentionally useful before a full graph exists.

That means a debug endpoint such as `/api/search/photos` may manually run a subset of atomic capabilities to inspect:

- request understanding quality
- extracted constraints
- rewritten queries
- search candidate quality
- score breakdowns
- basic critic outcomes

This debug path is valuable and should remain available even after Phase 5 is complete.

### 3.2 Phase 5 Consumes Primitives Instead of Wrapping the Whole Phase

Phase 5 should not treat the entire Phase 4 flow as one black-box node.

That would create two architecture problems:

- the graph would become a thin shell with no real decision boundary
- responsibilities such as planning and critique would remain hidden inside services

Instead, Phase 5 should promote orchestration concerns into the graph and reuse Phase 4 only where it already provides stable execution capability.

### 3.3 Recommended Boundary

Phase 4 should continue to own these reusable capabilities:

- retrieval preparation primitives for single-request understanding and rewrite
- embedding generation
- vector recall
- FTS recall
- minimal hard-filter application
- candidate fusion
- deterministic retrieval rerank
- retrieval result normalization
- debug-focused trace output

Phase 5 should own:

- task-level intent handling
- hard-vs-soft constraint separation for agent routing
- multi-attempt search planning
- plan selection and retry decisions
- workflow state transitions
- final result packaging and explanation

In short:

- Phase 4 answers: `How do we execute one search well?`
- Phase 5 answers: `How does the system decide which search to run next?`

---

## 4. Design Principles

### 4.1 Explicit Orchestration

The graph must represent actual decision boundaries, not just service calls renamed as nodes.

Each node should have one clear purpose, and that purpose should be understandable without reading downstream internals.

### 4.2 Reuse Over Reimplementation

Phase 5 should maximize reuse of Phase 4 primitives.

The graph is not the place to reimplement:

- query rewriting internals
- SQL recall logic
- fusion logic
- deterministic score formulas

### 4.3 Search Execution Is Not Planning

The workflow must distinguish between:

- deciding how to search
- actually executing the search

This prevents the search node from becoming an implicit agent inside the graph.

### 4.4 Controlled Agent Behavior

Phase 5 is a real agent workflow, but it is intentionally narrow and controlled.

The system should:

- plan multiple search attempts
- inspect outcomes
- retry once if needed

The system should not:

- run open-ended loops
- invent arbitrary retry behavior
- silently drop hard constraints

### 4.5 Traceability Is Required

The graph must emit structured intermediate artifacts that later support:

- debugging
- prompt iteration
- evaluation
- regression analysis

Agent behavior that cannot be traced is not acceptable for this phase.

---

## 5. Phase 5 Architecture

Phase 5 introduces an explicit LangGraph workflow above the Phase 4 execution layer.

The recommended top-level shape is:

```text
User Query
  -> Intent Node
  -> Constraint Node
  -> Planner Node
  -> Search Execution Node
  -> Critic Node
  -> Response Node
```

This graph should be the first product-facing orchestration layer.

It does not replace the debug path. Instead:

- the debug path remains useful for manual inspection of atomic capabilities
- the graph becomes the formal runtime that composes those capabilities into agent behavior

---

## 6. Node Responsibilities

### 6.1 Intent Node

**Purpose:** Classify the request at task level.

**Inputs:**

- `original_query`
- optional lightweight prior context

**Outputs:**

- `mode`
- `topic_action`

**Responsibilities:**

- determine whether the user is searching for `wallpaper`, `reference`, `photographer`, or `auto`
- decide whether the request is a new task, a refinement, or a reset

**Non-responsibilities:**

- detailed constraint extraction
- search planning
- query rewriting

### 6.2 Constraint Node

**Purpose:** Convert the request into structured constraints.

**Inputs:**

- `original_query`
- `mode`

**Outputs:**

- `hard_constraints`
- `soft_preferences`

**Responsibilities:**

- separate objective constraints from aesthetic preferences
- preserve negative constraints such as “no people”
- normalize outputs into a stable internal shape

**Non-responsibilities:**

- deciding search attempt count
- executing retrieval

### 6.3 Planner Node

**Purpose:** Generate a controlled set of search attempts.

**Inputs:**

- `mode`
- `hard_constraints`
- `soft_preferences`

**Outputs:**

- `search_specs`

**Responsibilities:**

- create one or more search specs that represent:
  - `strict`
  - `balanced`
  - `exploratory`
- preserve all hard constraints in every initial spec
- decide how much soft preference compression is allowed in each spec

**Non-responsibilities:**

- direct search execution
- direct result judgment

### 6.4 Search Execution Node

**Purpose:** Execute search specs using reusable Phase 4 capabilities.

**Inputs:**

- `search_specs`

**Outputs:**

- `search_results`

**Responsibilities:**

- call existing retrieval and search primitives
- gather per-spec result summaries
- normalize results into graph-consumable artifacts

**Non-responsibilities:**

- LLM reasoning
- free-form planning
- critique
- retry decisions

This node may call a complex service, but it should remain a thin execution boundary.

### 6.5 Critic Node

**Purpose:** Decide whether current results are good enough or whether one retry is justified.

**Inputs:**

- `search_results`
- `hard_constraints`
- `soft_preferences`
- `retry_count`

**Outputs:**

- `critic_result`

**Responsibilities:**

- judge result sufficiency
- detect likely over-narrow search plans
- choose one fixed retry strategy when appropriate

**Non-responsibilities:**

- writing new free-form search plans from scratch
- altering hard constraints
- unlimited iteration

### 6.6 Response Node

**Purpose:** Produce the final result payload.

**Inputs:**

- `search_results`
- `critic_result`

**Outputs:**

- `final_items`
- `response_reason`

**Responsibilities:**

- select the final result slice
- generate a short explanation summary
- shape the output for product-facing API layers

**Non-responsibilities:**

- reranking from first principles
- additional search execution

---

## 7. State Design

Phase 5 should introduce an explicit workflow state rather than relying on hidden service-local flow.

```python
class VisualSearchState(TypedDict):
    request_id: str
    conversation_id: str | None
    user_id: str | None

    original_query: str
    conversation_history: list[dict]

    mode: Literal["wallpaper", "reference", "photographer", "auto"]
    topic_action: Literal["new", "refine", "reset"] | None

    hard_constraints: dict
    soft_preferences: dict

    search_specs: list[SearchSpec]
    search_results: list[SearchResult]

    critic_result: CriticResult | None
    retry_count: int

    final_items: list[CandidateItem]
    response_reason: str | None

    errors: list[str]
```

The important property of this state is that it makes graph progression explicit:

- what the system understood
- what it planned
- what it executed
- what it judged
- what it returned

---

## 8. Contracts Between the Graph and Search Primitives

Phase 5 should consume Phase 4 capabilities through stable contracts.

### 8.1 SearchSpec

`SearchSpec` is the planner output consumed by the Search Execution node.

```python
class SearchSpec(TypedDict):
    spec_id: str
    query_text: str
    query_mode: Literal["strict", "balanced", "exploratory"]
    filters: dict
    limit: int
```

Semantics:

- `strict` preserves hard constraints and as many soft preferences as possible
- `balanced` preserves hard constraints and compresses some soft preferences
- `exploratory` preserves hard constraints and keeps only the most important soft signals

### 8.2 SearchResult

`SearchResult` is the graph-facing artifact returned by the Search Execution node.

```python
class SearchResult(TypedDict):
    spec_id: str
    total_hits: int
    items: list[CandidateItem]
    debug: dict
```

Each `SearchResult` should allow the graph to compare whether one search spec clearly outperformed another.

### 8.3 CandidateItem

The graph does not need every storage field, but each candidate item must preserve enough information for:

- final result selection
- score inspection
- critic judgment
- evaluation

Recommended fields include:

```python
class CandidateItem(TypedDict):
    unsplash_photo_id: str
    orientation: str | None
    vector_score: float | None
    fts_score: float | None
    hybrid_score: float | None
    metadata_match_score: float | None
    use_case_score: float | None
    final_score: float
    matched_constraints: dict
    source_spec_id: str
```

### 8.4 CriticResult

`CriticResult` controls conditional routing.

```python
class CriticResult(TypedDict):
    passed: bool
    reason_code: Literal[
        "ok",
        "too_few_results",
        "hard_constraint_violation",
        "low_relevance",
        "overly_narrow_query",
    ]
    retry_strategy: Literal[
        "none",
        "switch_to_balanced",
        "switch_to_exploratory",
        "relax_soft_preferences",
    ]
    preferred_spec_id: str | None
    summary: str
```

This result must stay structured. Free-form prose is not a sufficient graph contract.

---

## 9. Reuse Strategy for Phase 4

Phase 5 should reuse Phase 4 in a decomposed way.

### 9.1 What Should Be Reused Directly

The Search Execution node should call stable primitives or services that already exist for:

- request-to-search preparation where still appropriate
- vector retrieval
- FTS retrieval
- hard-filter application
- fusion
- deterministic retrieval rerank
- trace generation

### 9.2 What Should Not Stay Hidden Inside Search Execution

The following should not remain buried inside a monolithic retrieval call if they are meant to drive workflow behavior:

- task-level planning
- retry policy
- plan comparison decisions
- final quality judgment

Those belong to graph orchestration, not to the underlying retrieval service.

### 9.3 Long-Term Interpretation

The recommended interpretation of the two phases is:

- Phase 4 builds the atomic search machinery and debug entrypoints
- Phase 5 turns that machinery into a formal agent workflow

This lets the team keep the debug interface as an inspection surface while evolving the graph as the real runtime.

---

## 10. Routing and Retry Policy

Phase 5 should support one controlled retry only.

The routing shape is:

```text
Intent
  -> Constraint
  -> Planner
  -> Search Execution
  -> Critic
      -> pass => Response
      -> fail and retry_count == 0 => Planner or Search Execution with controlled retry strategy
      -> fail and retry_count >= 1 => Response
```

### 10.1 Allowed Retry Strategies

Only these retry strategies are allowed in this phase:

- `switch_to_balanced`
- `switch_to_exploratory`
- `relax_soft_preferences`

### 10.2 Disallowed Behavior

The workflow must not:

- drop hard constraints
- remove negative constraints silently
- enter open-ended loops
- let the critic emit arbitrary new plans with no structural control

### 10.3 Retry Philosophy

The retry should be interpreted as:

- switching or relaxing within a known plan family

not as:

- starting the whole reasoning process over from scratch

This makes the workflow easier to test and easier to compare in evaluation.

---

## 11. API Interpretation

The Phase 4 debug interface and the Phase 5 workflow interface should have distinct meanings.

### 11.1 Debug Interface

The debug-facing search route should remain available as a surface for:

- prompt iteration
- retrieval inspection
- search quality benchmarking
- regression testing
- failure isolation when the graph behaves unexpectedly

It is acceptable for this route to manually invoke atomic capabilities for observability purposes.

### 11.2 Product-Facing Agent Interface

The formal Phase 5 workflow should become the preferred execution path for product behavior.

That workflow should:

- consume the user query
- execute the full graph
- return final items and explanation

This distinction helps the team avoid conflating:

- `manual debug execution`
- `real agent orchestration`

---

## 12. Testing and Observability Expectations

Phase 5 should be testable at the node and graph levels.

The minimum verification surface should include:

- unit tests for intent and constraint output normalization
- unit tests for planner search-spec generation
- unit tests for critic pass/fail and retry selection logic
- graph-flow tests for pass path and one-retry path
- trace assertions that intermediate artifacts are preserved in state

Observability should include structured capture of:

- selected search specs
- result counts per spec
- critic reason codes
- retry strategy used
- final chosen spec

This information is required for later evaluation and not optional metadata.

---

## 13. Acceptance Criteria

Phase 5 is complete when:

- the graph consumes reusable Phase 4 atomic capabilities rather than wrapping the entire prior phase as one black-box node
- a Chinese natural-language request produces explicit intermediate artifacts for:
  - intent
  - constraints
  - search specs
  - search results
  - critic result
- the Search Execution node performs execution only and does not act as a hidden planner
- the workflow supports exactly one controlled retry
- hard constraints remain preserved across retry
- the debug search interface remains useful as a benchmark and inspection surface
- the new workflow can serve as the formal product-facing agent runtime

---

## 14. Summary

Phase 5 should be understood as the point where MuseaAgent stops being a set of manually chained search primitives and becomes an explicit agent workflow.

The correct architectural move is not to wrap Phase 4 in one large retrieval node.

The correct move is to:

- preserve Phase 4 as reusable atomic search capability
- expose graph-visible planning and critique boundaries
- compose those boundaries through explicit state and routing

That gives MuseaAgent its first real agent runtime while keeping retrieval execution stable, debuggable, and reusable.
