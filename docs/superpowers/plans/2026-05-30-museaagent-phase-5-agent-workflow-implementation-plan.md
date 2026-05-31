# MuseaAgent Phase 5 Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 5 LangGraph-based agent workflow that composes Phase 4 search primitives into a real agent runtime with explicit state, controlled planning, one retry path, and final response composition.

**Architecture:** This phase is implemented as an orchestration layer above the existing retrieval and retrieval-preparation services. First define graph contracts and module boundaries, then add intent/constraint/planner nodes, then wire a thin search-execution node to existing Phase 4 services, then add critic and retry policies, and finally assemble the graph and connect it to a formal agent-facing execution surface. The existing debug search route remains a primitive inspection surface rather than being replaced.

**Tech Stack:** Python 3.14, Pydantic v2, LangGraph, existing retrieval and retrieval-preparation services, pytest

---

## File Structure

### New files to create

- `backend/agents/states.py`
- `backend/agents/contracts.py`
- `backend/agents/visual_search_graph.py`
- `backend/agents/factory.py`
- `backend/agents/nodes/__init__.py`
- `backend/agents/nodes/intent_node.py`
- `backend/agents/nodes/constraint_node.py`
- `backend/agents/nodes/planner_node.py`
- `backend/agents/nodes/search_execution_node.py`
- `backend/agents/nodes/critic_node.py`
- `backend/agents/nodes/response_node.py`
- `backend/agents/policies/__init__.py`
- `backend/agents/policies/critic_policy.py`
- `backend/agents/policies/retry_policy.py`
- `backend/services/agent_runtime.py`
- `tests/unit/test_agent_contracts.py`
- `tests/unit/test_agent_planner.py`
- `tests/unit/test_agent_critic_policy.py`
- `tests/integration/test_visual_search_graph.py`
- `tests/integration/test_agent_runtime.py`

### Existing files to modify

- `backend/agents/__init__.py`
- `backend/services/retrieval/service.py`
- `backend/services/retrieval/contracts.py`
- `backend/services/retrieval_preparation/contracts.py`
- `backend/services/retrieval_preparation/service.py`
- `backend/schemas/search.py`
- `backend/api/routes/search_debug.py`
- `backend/api/router.py`
- `backend/core/settings_models.py`
- `backend/core/config.py`

### Existing files that may be slimmed down later, but not in this phase

- `backend/api/routes/search_debug.py`

The route should remain available, but its role becomes “manual primitive inspection” rather than “formal agent runtime.”

---

### Task 1: Define Agent Contracts, State, and Configuration

**Files:**
- Create: `backend/agents/contracts.py`
- Create: `backend/agents/states.py`
- Modify: `backend/core/settings_models.py`
- Modify: `backend/core/config.py`
- Modify: `backend/schemas/search.py`
- Test: `tests/unit/test_agent_contracts.py`

- [ ] **Step 1: Write the failing unit test for the Phase 5 state and contract surface**

```python
from backend.agents.contracts import CriticResult, SearchSpec
from backend.agents.states import VisualSearchState


def test_agent_contracts_preserve_retry_and_spec_metadata() -> None:
    spec = SearchSpec(
        spec_id="strict-1",
        query_text="dark calm wallpaper no people",
        query_mode="strict",
        filters={"has_human": False},
        limit=20,
    )
    critic = CriticResult(
        passed=False,
        reason_code="too_few_results",
        retry_strategy="switch_to_balanced",
        preferred_spec_id="balanced-1",
        summary="strict search was too narrow",
    )
    state: VisualSearchState = {
        "request_id": "req_123",
        "conversation_id": None,
        "user_id": None,
        "original_query": "我想找深色安静的壁纸，不要人物",
        "conversation_history": [],
        "mode": "wallpaper",
        "topic_action": "new",
        "hard_constraints": {"has_human": False},
        "soft_preferences": {"moods": ["calm"]},
        "search_specs": [spec],
        "search_results": [],
        "critic_result": critic,
        "retry_count": 0,
        "final_items": [],
        "response_reason": None,
        "errors": [],
    }

    assert state["search_specs"][0].query_mode == "strict"
    assert state["critic_result"].retry_strategy == "switch_to_balanced"
```

- [ ] **Step 2: Run the targeted unit test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_agent_contracts.py -v`
Expected: FAIL because the agent contracts and state module do not exist yet

- [ ] **Step 3: Add agent-facing contract models**

Create `backend/agents/contracts.py` with models like:

```python
class SearchSpec(BaseModel):
    spec_id: str
    query_text: str
    query_mode: Literal["strict", "balanced", "exploratory"]
    filters: dict[str, object]
    limit: int = 20


class CandidateItem(BaseModel):
    unsplash_photo_id: str
    orientation: str | None = None
    vector_score: float | None = None
    fts_score: float | None = None
    hybrid_score: float | None = None
    metadata_match_score: float | None = None
    use_case_score: float | None = None
    final_score: float
    matched_constraints: dict[str, object] = Field(default_factory=dict)
    source_spec_id: str


class SearchResult(BaseModel):
    spec_id: str
    total_hits: int
    items: list[CandidateItem]
    debug: dict[str, object] = Field(default_factory=dict)


class CriticResult(BaseModel):
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
    preferred_spec_id: str | None = None
    summary: str
```

- [ ] **Step 4: Add the explicit workflow state**

Create `backend/agents/states.py`:

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

- [ ] **Step 5: Add Phase 5 settings and external schema hooks**

Extend `backend/core/settings_models.py`:

```python
class AgentWorkflowSettings(BaseModel):
    enabled: bool = True
    max_retry_count: int = 1
    min_acceptable_results: int = 6
    hard_constraint_min_match_ratio: float = 0.85
```

Wire it into `backend/core/config.py`, and add response-facing schema types to `backend/schemas/search.py` for:

- `AgentSearchDebugSummary`
- `AgentSearchResponse`

- [ ] **Step 6: Run the contract test to verify the slice passes**

Run: `.venv/bin/pytest tests/unit/test_agent_contracts.py -v`
Expected: PASS

- [ ] **Step 7: Commit the contract slice**

```bash
git add backend/agents/contracts.py backend/agents/states.py backend/core/settings_models.py backend/core/config.py backend/schemas/search.py tests/unit/test_agent_contracts.py
git commit -m "feat: add phase 5 agent contracts"
```

---

### Task 2: Add Intent, Constraint, and Planner Nodes on Top of Phase 4 Primitives

**Files:**
- Create: `backend/agents/nodes/intent_node.py`
- Create: `backend/agents/nodes/constraint_node.py`
- Create: `backend/agents/nodes/planner_node.py`
- Create: `backend/agents/nodes/__init__.py`
- Modify: `backend/services/retrieval_preparation/service.py`
- Modify: `backend/services/retrieval_preparation/contracts.py`
- Test: `tests/unit/test_agent_planner.py`

- [ ] **Step 1: Write the failing unit tests for planner output shape**

```python
from backend.agents.nodes.planner_node import PlannerNode


def test_planner_produces_strict_balanced_and_exploratory_specs() -> None:
    node = PlannerNode()

    result = node.run(
        {
            "mode": "wallpaper",
            "hard_constraints": {"has_human": False},
            "soft_preferences": {"moods": ["calm"], "colors": ["dark"], "qualities": ["oled"]},
        }
    )

    query_modes = [spec.query_mode for spec in result]

    assert query_modes == ["strict", "balanced", "exploratory"]
    assert all(spec.filters["has_human"] is False for spec in result)
```

- [ ] **Step 2: Run the planner tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_agent_planner.py -v`
Expected: FAIL because the new node modules do not exist yet

- [ ] **Step 3: Implement the Intent node**

Create `backend/agents/nodes/intent_node.py`:

```python
class IntentNode:
    def run(self, state: VisualSearchState) -> dict[str, object]:
        query = state["original_query"]
        return {
            "mode": "wallpaper" if "壁纸" in query else "auto",
            "topic_action": "new",
        }
```

Start with deterministic heuristics and leave model-assisted upgrading behind a clean method boundary. The node must not perform rewrite generation.

- [ ] **Step 4: Implement the Constraint node as an adapter over retrieval preparation**

Create `backend/agents/nodes/constraint_node.py`:

```python
class ConstraintNode:
    def __init__(self, retrieval_preparation_service) -> None:
        self._retrieval_preparation_service = retrieval_preparation_service

    def run(self, state: VisualSearchState) -> dict[str, object]:
        prepared = self._retrieval_preparation_service.prepare(
            query=state["original_query"],
            mode=state["mode"],
            filters=None,
        )
        return {
            "hard_constraints": prepared.understanding.hard_filters.model_dump(exclude_none=True),
            "soft_preferences": prepared.understanding.soft_preferences.model_dump(exclude_none=True),
        }
```

This node should reuse Phase 4 understanding output instead of inventing a duplicate extraction stack.

- [ ] **Step 5: Implement the Planner node**

Create `backend/agents/nodes/planner_node.py`:

```python
class PlannerNode:
    def run(self, state: VisualSearchState) -> dict[str, object]:
        hard_constraints = state["hard_constraints"]
        soft_preferences = state["soft_preferences"]

        return {
            "search_specs": [
                SearchSpec(
                    spec_id="strict-1",
                    query_text="dark calm oled wallpaper no people",
                    query_mode="strict",
                    filters=hard_constraints,
                    limit=20,
                ),
                SearchSpec(
                    spec_id="balanced-1",
                    query_text="dark calm wallpaper no people",
                    query_mode="balanced",
                    filters=hard_constraints,
                    limit=20,
                ),
                SearchSpec(
                    spec_id="exploratory-1",
                    query_text="dark moody wallpaper no people",
                    query_mode="exploratory",
                    filters=hard_constraints,
                    limit=20,
                ),
            ]
        }
```

The actual strings should be assembled from the structured soft-preference fields rather than hard-coded, but the logic must preserve all hard constraints in every initial spec.

- [ ] **Step 6: Run the planner tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_agent_planner.py -v`
Expected: PASS

- [ ] **Step 7: Commit the planning slice**

```bash
git add backend/agents/nodes/__init__.py backend/agents/nodes/intent_node.py backend/agents/nodes/constraint_node.py backend/agents/nodes/planner_node.py backend/services/retrieval_preparation/service.py backend/services/retrieval_preparation/contracts.py tests/unit/test_agent_planner.py
git commit -m "feat: add phase 5 planning nodes"
```

---

### Task 3: Implement the Thin Search Execution Node and Agent Runtime Adapter

**Files:**
- Create: `backend/agents/nodes/search_execution_node.py`
- Create: `backend/services/agent_runtime.py`
- Modify: `backend/services/retrieval/service.py`
- Modify: `backend/services/retrieval/contracts.py`
- Test: `tests/integration/test_agent_runtime.py`

- [ ] **Step 1: Write the failing integration test for spec-driven search execution**

```python
from backend.services.agent_runtime import AgentRuntimeService


def test_agent_runtime_executes_multiple_search_specs_and_preserves_source_spec_id(retrieval_service) -> None:
    runtime = AgentRuntimeService(retrieval_service=retrieval_service, graph=None)

    results = runtime.execute_search_specs(
        mode="wallpaper",
        search_specs=[
            {"spec_id": "strict-1", "query_text": "dark calm wallpaper no people", "query_mode": "strict", "filters": {"has_human": False}, "limit": 10},
            {"spec_id": "balanced-1", "query_text": "dark wallpaper no people", "query_mode": "balanced", "filters": {"has_human": False}, "limit": 10},
        ],
    )

    assert len(results) == 2
    assert all(result.spec_id in {"strict-1", "balanced-1"} for result in results)
    assert all(item.source_spec_id == result.spec_id for result in results for item in result.items)
```

- [ ] **Step 2: Run the integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_agent_runtime.py -v`
Expected: FAIL because there is no agent runtime adapter or search execution node yet

- [ ] **Step 3: Extend retrieval output so the graph can consume it directly**

Update `backend/services/retrieval/contracts.py` so retrieval item output preserves:

```python
class RetrievalResultItem(BaseModel):
    unsplash_photo_id: str
    orientation: str | None = None
    vector_score: float | None = None
    fts_score: float | None = None
    hybrid_score: float | None = None
    metadata_match_score: float | None = None
    use_case_score: float | None = None
    final_score: float
    matched_constraints: dict[str, object] = Field(default_factory=dict)
```

Keep retrieval independent, but ensure the graph can adapt its output without inventing fake score fields later.

- [ ] **Step 4: Implement the Search Execution node**

Create `backend/agents/nodes/search_execution_node.py`:

```python
class SearchExecutionNode:
    def __init__(self, retrieval_service) -> None:
        self._retrieval_service = retrieval_service

    def run(self, state: VisualSearchState) -> dict[str, object]:
        results = []
        for spec in state["search_specs"]:
            retrieval_result = self._retrieval_service.search(
                query=spec.query_text,
                mode=state["mode"],
                limit=spec.limit,
                filters=spec.filters,
                debug=True,
            )
            results.append(
                SearchResult(
                    spec_id=spec.spec_id,
                    total_hits=len(retrieval_result.items),
                    items=[
                        CandidateItem(**item.model_dump(), source_spec_id=spec.spec_id)
                        for item in retrieval_result.items
                    ],
                    debug=retrieval_result.trace.model_dump(),
                )
            )
        return {"search_results": results}
```

The node must not call an LLM and must not perform hidden replanning.

- [ ] **Step 5: Add a thin runtime adapter for graph-independent execution**

Create `backend/services/agent_runtime.py`:

```python
class AgentRuntimeService:
    def __init__(self, retrieval_service, graph) -> None:
        self._retrieval_service = retrieval_service
        self._graph = graph

    def execute_search_specs(self, mode: str, search_specs: list[SearchSpec]) -> list[SearchResult]:
        node = SearchExecutionNode(self._retrieval_service)
        return node.run({"mode": mode, "search_specs": search_specs})["search_results"]
```

This adapter gives tests and later API wiring a stable entrypoint before the full graph is assembled.

- [ ] **Step 6: Run the integration test to verify the slice passes**

Run: `.venv/bin/pytest tests/integration/test_agent_runtime.py -v`
Expected: PASS

- [ ] **Step 7: Commit the search-execution slice**

```bash
git add backend/agents/nodes/search_execution_node.py backend/services/agent_runtime.py backend/services/retrieval/contracts.py backend/services/retrieval/service.py tests/integration/test_agent_runtime.py
git commit -m "feat: add phase 5 search execution node"
```

---

### Task 4: Add Critic and Retry Policies Plus the Response Node

**Files:**
- Create: `backend/agents/policies/critic_policy.py`
- Create: `backend/agents/policies/retry_policy.py`
- Create: `backend/agents/nodes/critic_node.py`
- Create: `backend/agents/nodes/response_node.py`
- Create: `backend/agents/policies/__init__.py`
- Test: `tests/unit/test_agent_critic_policy.py`

- [ ] **Step 1: Write the failing unit tests for controlled retry decisions**

```python
from backend.agents.policies.critic_policy import CriticPolicy


def test_critic_switches_to_balanced_when_strict_results_are_too_few() -> None:
    policy = CriticPolicy(min_acceptable_results=6, hard_constraint_min_match_ratio=0.85)

    result = policy.evaluate(
        search_results=[
            {"spec_id": "strict-1", "total_hits": 2, "items": []},
            {"spec_id": "balanced-1", "total_hits": 12, "items": []},
        ],
        retry_count=0,
    )

    assert result.passed is False
    assert result.retry_strategy == "switch_to_balanced"
    assert result.preferred_spec_id == "balanced-1"
```

- [ ] **Step 2: Run the policy tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_agent_critic_policy.py -v`
Expected: FAIL because the critic and retry policies do not exist yet

- [ ] **Step 3: Implement the critic policy**

Create `backend/agents/policies/critic_policy.py`:

```python
class CriticPolicy:
    def __init__(self, min_acceptable_results: int, hard_constraint_min_match_ratio: float) -> None:
        self._min_acceptable_results = min_acceptable_results
        self._hard_constraint_min_match_ratio = hard_constraint_min_match_ratio

    def evaluate(self, search_results: list[SearchResult], retry_count: int) -> CriticResult:
        ...
```

The first version should only inspect:

- result counts per spec
- obvious hard-constraint failures
- whether a broader spec clearly outperformed a narrower one

- [ ] **Step 4: Implement the retry policy**

Create `backend/agents/policies/retry_policy.py` with a helper like:

```python
def apply_retry_strategy(
    search_specs: list[SearchSpec],
    critic_result: CriticResult,
) -> list[SearchSpec]:
    ...
```

This helper must:

- keep hard filters intact
- switch to a preferred spec when one is named
- avoid creating open-ended new strategies

- [ ] **Step 5: Implement the Critic and Response nodes**

Create `backend/agents/nodes/critic_node.py`:

```python
class CriticNode:
    def __init__(self, policy: CriticPolicy) -> None:
        self._policy = policy

    def run(self, state: VisualSearchState) -> dict[str, object]:
        return {
            "critic_result": self._policy.evaluate(
                search_results=state["search_results"],
                retry_count=state["retry_count"],
            )
        }
```

Create `backend/agents/nodes/response_node.py`:

```python
class ResponseNode:
    def run(self, state: VisualSearchState) -> dict[str, object]:
        preferred_spec_id = state["critic_result"].preferred_spec_id
        chosen = next(
            (result for result in state["search_results"] if result.spec_id == preferred_spec_id),
            state["search_results"][0],
        )
        return {
            "final_items": chosen.items[:20],
            "response_reason": state["critic_result"].summary,
        }
```

- [ ] **Step 6: Run the policy tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_agent_critic_policy.py -v`
Expected: PASS

- [ ] **Step 7: Commit the critic slice**

```bash
git add backend/agents/policies/__init__.py backend/agents/policies/critic_policy.py backend/agents/policies/retry_policy.py backend/agents/nodes/critic_node.py backend/agents/nodes/response_node.py tests/unit/test_agent_critic_policy.py
git commit -m "feat: add phase 5 critic and retry policy"
```

---

### Task 5: Assemble the Graph and Wire a Formal Agent Runtime Surface

**Files:**
- Create: `backend/agents/visual_search_graph.py`
- Create: `backend/agents/factory.py`
- Modify: `backend/agents/__init__.py`
- Modify: `backend/api/routes/search_debug.py`
- Modify: `backend/api/router.py`
- Test: `tests/integration/test_visual_search_graph.py`

- [ ] **Step 1: Write the failing integration test for pass-path and one-retry-path graph flow**

```python
from backend.agents.visual_search_graph import build_visual_search_graph


def test_graph_runs_single_retry_then_returns_response(agent_runtime_dependencies) -> None:
    graph = build_visual_search_graph(**agent_runtime_dependencies)

    result = graph.invoke(
        {
            "request_id": "req_123",
            "conversation_id": None,
            "user_id": None,
            "original_query": "我想找深色安静的壁纸，不要人物",
            "conversation_history": [],
            "mode": "auto",
            "topic_action": None,
            "hard_constraints": {},
            "soft_preferences": {},
            "search_specs": [],
            "search_results": [],
            "critic_result": None,
            "retry_count": 0,
            "final_items": [],
            "response_reason": None,
            "errors": [],
        }
    )

    assert result["critic_result"] is not None
    assert result["retry_count"] in {0, 1}
    assert result["final_items"]
```

- [ ] **Step 2: Run the graph integration test to verify it fails**

Run: `.venv/bin/pytest tests/integration/test_visual_search_graph.py -v`
Expected: FAIL because the graph assembly does not exist yet

- [ ] **Step 3: Assemble the LangGraph workflow**

Create `backend/agents/visual_search_graph.py`:

```python
def build_visual_search_graph(
    intent_node: IntentNode,
    constraint_node: ConstraintNode,
    planner_node: PlannerNode,
    search_execution_node: SearchExecutionNode,
    critic_node: CriticNode,
    response_node: ResponseNode,
):
    graph = StateGraph(VisualSearchState)
    graph.add_node("intent", intent_node.run)
    graph.add_node("constraint", constraint_node.run)
    graph.add_node("planner", planner_node.run)
    graph.add_node("search_execution", search_execution_node.run)
    graph.add_node("critic", critic_node.run)
    graph.add_node("response", response_node.run)
    graph.add_edge(START, "intent")
    graph.add_edge("intent", "constraint")
    graph.add_edge("constraint", "planner")
    graph.add_edge("planner", "search_execution")
    graph.add_edge("search_execution", "critic")
    ...
```

Use one conditional branch only:

- `pass -> response`
- `fail with retry_count == 0 -> planner or search_execution after applying retry policy`
- `fail with retry_count >= 1 -> response`

- [ ] **Step 4: Add a factory for runtime construction**

Create `backend/agents/factory.py` so the app can build one consistent workflow from:

- retrieval-preparation service
- retrieval service
- critic policy settings

Avoid constructing node dependencies inside route handlers.

- [ ] **Step 5: Wire the formal runtime surface without deleting the debug route**

Update `backend/api/routes/search_debug.py` and `backend/api/router.py` so the project now supports:

- a debug-oriented path that still exposes primitive traces
- an agent-runtime path that invokes the graph

If the codebase is not ready for a new route yet, the existing debug route may temporarily accept a flag like `use_agent_workflow=True`, but the implementation should keep the runtime boundary explicit.

- [ ] **Step 6: Run the graph integration tests and relevant search route tests**

Run: `.venv/bin/pytest tests/integration/test_visual_search_graph.py tests/integration/test_search_debug.py -v`
Expected: PASS

- [ ] **Step 7: Commit the graph assembly slice**

```bash
git add backend/agents/visual_search_graph.py backend/agents/factory.py backend/agents/__init__.py backend/api/routes/search_debug.py backend/api/router.py tests/integration/test_visual_search_graph.py
git commit -m "feat: assemble phase 5 agent workflow"
```

---

## Delivery Notes

- Keep the Phase 4 debug route as a stable primitive inspection surface.
- Do not move retrieval fusion or deterministic rerank into graph nodes.
- Do not let the Search Execution node hide planning or critique logic.
- Prefer deterministic policies first; model-assisted upgrades can be layered in later behind existing node boundaries.

## Plan Self-Review

- Spec coverage: the plan covers graph state, node boundaries, search-spec execution, critic/retry policy, and the formal runtime surface from the Phase 5 spec.
- Red-flag scan: no task relies on `TODO`, “handle later,” or unbounded “appropriate logic” language without a concrete file target.
- Type consistency: the same `SearchSpec`, `SearchResult`, `CriticResult`, and `VisualSearchState` contracts are used across state, nodes, policies, and graph assembly.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-30-museaagent-phase-5-agent-workflow-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
