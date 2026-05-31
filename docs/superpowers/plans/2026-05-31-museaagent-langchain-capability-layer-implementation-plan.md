# MuseaAgent LangChain Capability Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a provider-agnostic LangChain capability layer into MuseaAgent so that model-driven understanding, rewrite, intent, planning, critic advice, and response explanation flow through standardized chains while LangGraph remains the orchestration layer and retrieval execution remains an application service.

**Architecture:** This migration starts by building a dedicated `backend/llm` layer with provider factories, prompts, schemas, chain wrappers, and invocation helpers. It then migrates the most mature existing model-driven capabilities first, followed by graph-level intelligent nodes, followed by hybrid critic/response upgrades, and finally removes old prompt-plus-JSON parsing patterns from factories and services. LangGraph routing remains in place throughout.

**Tech Stack:** Python 3.14, LangChain Core, provider adapters for OpenAI-compatible and Gemini-style chat models, LangGraph, Pydantic v2, pytest

---

## File Structure

### New files to create

- `backend/llm/__init__.py`
- `backend/llm/providers/__init__.py`
- `backend/llm/providers/base.py`
- `backend/llm/providers/openai.py`
- `backend/llm/providers/gemini.py`
- `backend/llm/providers/openrouter.py`
- `backend/llm/providers/factory.py`
- `backend/llm/prompts/__init__.py`
- `backend/llm/prompts/retrieval_understanding.py`
- `backend/llm/prompts/retrieval_rewrite.py`
- `backend/llm/prompts/intent_classification.py`
- `backend/llm/prompts/search_planning.py`
- `backend/llm/prompts/critic_review.py`
- `backend/llm/prompts/response_reason.py`
- `backend/llm/schemas/__init__.py`
- `backend/llm/schemas/retrieval_understanding.py`
- `backend/llm/schemas/retrieval_rewrite.py`
- `backend/llm/schemas/intent.py`
- `backend/llm/schemas/planner.py`
- `backend/llm/schemas/critic.py`
- `backend/llm/schemas/response.py`
- `backend/llm/chains/__init__.py`
- `backend/llm/chains/retrieval_understanding_chain.py`
- `backend/llm/chains/retrieval_rewrite_chain.py`
- `backend/llm/chains/intent_chain.py`
- `backend/llm/chains/planner_chain.py`
- `backend/llm/chains/critic_chain.py`
- `backend/llm/chains/response_chain.py`
- `backend/llm/runtime/__init__.py`
- `backend/llm/runtime/invocation.py`
- `backend/llm/runtime/structured_output.py`
- `backend/llm/runtime/tracing.py`
- `tests/unit/test_llm_provider_factory.py`
- `tests/unit/test_retrieval_understanding_chain.py`
- `tests/unit/test_retrieval_rewrite_chain.py`
- `tests/unit/test_intent_chain.py`
- `tests/unit/test_planner_chain.py`
- `tests/unit/test_hybrid_critic.py`
- `tests/unit/test_response_reason_chain.py`

### Existing files to modify

- `pyproject.toml`
- `backend/core/settings_models.py`
- `backend/core/config.py`
- `backend/services/retrieval/factory.py`
- `backend/services/retrieval_preparation/factory.py`
- `backend/services/retrieval_preparation/understanding.py`
- `backend/services/retrieval_preparation/rewrite.py`
- `backend/services/retrieval_preparation/service.py`
- `backend/agents/nodes/intent_node.py`
- `backend/agents/nodes/planner_node.py`
- `backend/agents/nodes/critic_node.py`
- `backend/agents/nodes/response_node.py`
- `backend/agents/factory.py`
- `backend/agents/policies/critic_policy.py`
- `tests/integration/test_visual_search_graph.py`
- `tests/integration/test_search_agent.py`
- `tests/integration/test_retrieval_service.py`

### Existing files that may be removed or drastically slimmed down later

- `backend/services/retrieval/factory.py` prompt-heavy provider builders
- `backend/services/retrieval_preparation/understanding.py` manual JSON payload parsing
- `backend/services/retrieval_preparation/rewrite.py` manual JSON payload parsing

These should not be removed immediately. They should be slimmed down only after the new capability layer is proven.

---

### Task 1: Build the LangChain Provider and Runtime Foundation

**Files:**
- Create: `backend/llm/providers/base.py`
- Create: `backend/llm/providers/openai.py`
- Create: `backend/llm/providers/gemini.py`
- Create: `backend/llm/providers/openrouter.py`
- Create: `backend/llm/providers/factory.py`
- Create: `backend/llm/runtime/invocation.py`
- Create: `backend/llm/runtime/structured_output.py`
- Create: `backend/llm/runtime/tracing.py`
- Modify: `backend/core/settings_models.py`
- Modify: `backend/core/config.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/test_llm_provider_factory.py`

- [ ] **Step 1: Write the failing unit test for provider-neutral model creation**

```python
from backend.llm.providers.factory import build_chat_model


def test_provider_factory_can_build_capability_scoped_model_config() -> None:
    model = build_chat_model(
        capability="planner",
        provider_name="openai",
        model_name="gpt-4.1-mini",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
    )

    assert model is not None
```

- [ ] **Step 2: Run the provider test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_llm_provider_factory.py -v`
Expected: FAIL because the `backend.llm` provider layer does not exist yet

- [ ] **Step 3: Add provider settings models**

Extend `backend/core/settings_models.py` with:

```python
class LLMProviderConfig(BaseModel):
    provider: Literal["openai", "gemini", "openrouter"]
    model: str
    api_key: str = ""
    base_url: str = ""


class LLMCapabilitySettings(BaseModel):
    understanding: LLMProviderConfig
    rewrite: LLMProviderConfig
    intent: LLMProviderConfig
    planner: LLMProviderConfig
    critic: LLMProviderConfig
    response: LLMProviderConfig
```

Wire it into `backend/core/config.py`.

- [ ] **Step 4: Add the provider abstraction**

Create `backend/llm/providers/base.py` with:

```python
class ChatModelProvider(Protocol):
    def build(self, model_name: str, api_key: str, base_url: str | None = None):
        ...
```

Create provider adapters for:

- OpenAI-compatible providers
- Gemini
- OpenRouter

- [ ] **Step 5: Add a capability-aware provider factory**

Create `backend/llm/providers/factory.py` with a function like:

```python
def build_chat_model(*, capability: str, provider_name: str, model_name: str, api_key: str, base_url: str = ""):
    ...
```

The goal is to isolate provider selection and make capability-based wiring possible.

- [ ] **Step 6: Add common runtime wrappers**

Create `backend/llm/runtime/structured_output.py` with a wrapper that:

- accepts a chat model
- accepts a prompt template
- accepts a Pydantic schema
- returns validated structured output

Create `backend/llm/runtime/invocation.py` and `backend/llm/runtime/tracing.py` for:

- invocation metadata
- capability labels
- model/provider trace data

- [ ] **Step 7: Add LangChain dependencies to the project manifest**

Update `pyproject.toml` to include:

- `langchain-core`
- provider packages required by the chosen adapter strategy

The dependency set should match the provider-agnostic design, not just an OpenAI-only shortcut.

- [ ] **Step 8: Run the provider test to verify the foundation passes**

Run: `.venv/bin/pytest tests/unit/test_llm_provider_factory.py -v`
Expected: PASS

- [ ] **Step 9: Commit the provider/runtime foundation**

```bash
git add pyproject.toml backend/core/settings_models.py backend/core/config.py backend/llm/providers backend/llm/runtime tests/unit/test_llm_provider_factory.py
git commit -m "feat: add langchain provider foundation"
```

---

### Task 2: Migrate Retrieval Preparation Understanding and Rewrite to LangChain Chains

**Files:**
- Create: `backend/llm/prompts/retrieval_understanding.py`
- Create: `backend/llm/prompts/retrieval_rewrite.py`
- Create: `backend/llm/schemas/retrieval_understanding.py`
- Create: `backend/llm/schemas/retrieval_rewrite.py`
- Create: `backend/llm/chains/retrieval_understanding_chain.py`
- Create: `backend/llm/chains/retrieval_rewrite_chain.py`
- Modify: `backend/services/retrieval_preparation/understanding.py`
- Modify: `backend/services/retrieval_preparation/rewrite.py`
- Modify: `backend/services/retrieval_preparation/factory.py`
- Modify: `backend/services/retrieval_preparation/service.py`
- Test: `tests/unit/test_retrieval_understanding_chain.py`
- Test: `tests/unit/test_retrieval_rewrite_chain.py`

- [ ] **Step 1: Write the failing unit test for structured understanding-chain output**

```python
from backend.llm.chains.retrieval_understanding_chain import RetrievalUnderstandingChain


def test_understanding_chain_returns_structured_understanding_result(fake_chat_model) -> None:
    chain = RetrievalUnderstandingChain(fake_chat_model)

    result = chain.invoke({"query": "我想找深色安静的壁纸，不要人物", "mode": "wallpaper"})

    assert result.inferred_mode == "wallpaper"
    assert result.hard_filters.has_human is False
```

- [ ] **Step 2: Run the retrieval-understanding chain test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_retrieval_understanding_chain.py -v`
Expected: FAIL because the chain module does not exist yet

- [ ] **Step 3: Move understanding prompt and schema into the capability layer**

Add:

- `backend/llm/prompts/retrieval_understanding.py`
- `backend/llm/schemas/retrieval_understanding.py`

The schema should align with the existing `QueryUnderstandingResult` contract.

- [ ] **Step 4: Implement RetrievalUnderstandingChain**

Create `backend/llm/chains/retrieval_understanding_chain.py`:

```python
class RetrievalUnderstandingChain:
    def __init__(self, chat_model) -> None:
        ...

    def invoke(self, payload: dict) -> QueryUnderstandingResult:
        ...
```

This chain should own:

- prompt selection
- structured output invocation
- provider-neutral model calling

It should not own:

- explicit filter merge logic
- service-level fallback normalization

- [ ] **Step 5: Repeat the same migration pattern for retrieval rewrite**

Create:

- `backend/llm/prompts/retrieval_rewrite.py`
- `backend/llm/schemas/retrieval_rewrite.py`
- `backend/llm/chains/retrieval_rewrite_chain.py`

Update `RetrievalRewriteService` so it delegates to the chain and retains only:

- deterministic fallback
- service-level error normalization

- [ ] **Step 6: Run chain tests plus retrieval preparation tests**

Run: `.venv/bin/pytest tests/unit/test_retrieval_understanding_chain.py tests/unit/test_retrieval_rewrite_chain.py tests/unit/test_retrieval_understanding.py tests/unit/test_retrieval_rewrite.py tests/unit/test_retrieval_preparation_fallback.py -v`
Expected: PASS

- [ ] **Step 7: Commit the retrieval-preparation migration**

```bash
git add backend/llm/prompts/retrieval_understanding.py backend/llm/prompts/retrieval_rewrite.py backend/llm/schemas/retrieval_understanding.py backend/llm/schemas/retrieval_rewrite.py backend/llm/chains/retrieval_understanding_chain.py backend/llm/chains/retrieval_rewrite_chain.py backend/services/retrieval_preparation/understanding.py backend/services/retrieval_preparation/rewrite.py backend/services/retrieval_preparation/factory.py backend/services/retrieval_preparation/service.py tests/unit/test_retrieval_understanding_chain.py tests/unit/test_retrieval_rewrite_chain.py
git commit -m "feat: migrate retrieval preparation to langchain"
```

---

### Task 3: Migrate Intent and Planner to LangChain Capability Chains

**Files:**
- Create: `backend/llm/prompts/intent_classification.py`
- Create: `backend/llm/prompts/search_planning.py`
- Create: `backend/llm/schemas/intent.py`
- Create: `backend/llm/schemas/planner.py`
- Create: `backend/llm/chains/intent_chain.py`
- Create: `backend/llm/chains/planner_chain.py`
- Modify: `backend/agents/nodes/intent_node.py`
- Modify: `backend/agents/nodes/planner_node.py`
- Modify: `backend/agents/factory.py`
- Test: `tests/unit/test_intent_chain.py`
- Test: `tests/unit/test_planner_chain.py`
- Test: `tests/unit/test_agent_planner.py`

- [ ] **Step 1: Write the failing unit test for structured intent output**

```python
from backend.llm.chains.intent_chain import IntentClassificationChain


def test_intent_chain_returns_mode_and_topic_action(fake_chat_model) -> None:
    chain = IntentClassificationChain(fake_chat_model)

    result = chain.invoke({"query": "找个摄影师风格", "conversation_history": []})

    assert result.mode == "photographer"
    assert result.topic_action in {"new", "refine", "reset"}
```

- [ ] **Step 2: Write the failing unit test for planner search-spec generation**

```python
from backend.llm.chains.planner_chain import SearchPlannerChain


def test_planner_chain_returns_three_structured_search_specs(fake_chat_model) -> None:
    chain = SearchPlannerChain(fake_chat_model)

    result = chain.invoke(
        {
            "mode": "wallpaper",
            "hard_constraints": {"has_human": False},
            "soft_preferences": {"moods": ["calm"], "colors": ["dark"], "qualities": ["oled"]},
        }
    )

    assert [spec.query_mode for spec in result.search_specs] == ["strict", "balanced", "exploratory"]
```

- [ ] **Step 3: Run the intent/planner tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_intent_chain.py tests/unit/test_planner_chain.py -v`
Expected: FAIL because the chains do not exist yet

- [ ] **Step 4: Add intent and planner prompts plus schemas**

Create:

- `backend/llm/prompts/intent_classification.py`
- `backend/llm/prompts/search_planning.py`
- `backend/llm/schemas/intent.py`
- `backend/llm/schemas/planner.py`

The planner schema must support stable `SearchSpec` generation that matches the graph contract.

- [ ] **Step 5: Implement the LangChain-based intent and planner chains**

Create:

- `backend/llm/chains/intent_chain.py`
- `backend/llm/chains/planner_chain.py`

These chains should return typed schema objects, not raw dicts.

- [ ] **Step 6: Refactor agent nodes to become thin chain adapters**

Update `IntentNode` so it:

- passes state fields to `IntentClassificationChain`
- writes back only `mode` and `topic_action`

Update `PlannerNode` so it:

- passes `mode`, `hard_constraints`, and `soft_preferences`
- writes back `search_specs`

The node files should stop containing embedded planning heuristics.

- [ ] **Step 7: Run the chain and node tests**

Run: `.venv/bin/pytest tests/unit/test_intent_chain.py tests/unit/test_planner_chain.py tests/unit/test_agent_planner.py -v`
Expected: PASS

- [ ] **Step 8: Commit the intent/planner migration**

```bash
git add backend/llm/prompts/intent_classification.py backend/llm/prompts/search_planning.py backend/llm/schemas/intent.py backend/llm/schemas/planner.py backend/llm/chains/intent_chain.py backend/llm/chains/planner_chain.py backend/agents/nodes/intent_node.py backend/agents/nodes/planner_node.py backend/agents/factory.py tests/unit/test_intent_chain.py tests/unit/test_planner_chain.py tests/unit/test_agent_planner.py
git commit -m "feat: migrate intent and planner to langchain"
```

---

### Task 4: Introduce Hybrid Critic and Response Capability Chains

**Files:**
- Create: `backend/llm/prompts/critic_review.py`
- Create: `backend/llm/prompts/response_reason.py`
- Create: `backend/llm/schemas/critic.py`
- Create: `backend/llm/schemas/response.py`
- Create: `backend/llm/chains/critic_chain.py`
- Create: `backend/llm/chains/response_chain.py`
- Modify: `backend/agents/policies/critic_policy.py`
- Modify: `backend/agents/nodes/critic_node.py`
- Modify: `backend/agents/nodes/response_node.py`
- Test: `tests/unit/test_hybrid_critic.py`
- Test: `tests/unit/test_response_reason_chain.py`
- Test: `tests/unit/test_agent_critic_policy.py`

- [ ] **Step 1: Write the failing unit test for hybrid critic advice**

```python
from backend.agents.policies.critic_policy import HybridCriticPolicy


def test_hybrid_critic_preserves_rule_decision_and_adds_model_summary(fake_critic_chain) -> None:
    policy = HybridCriticPolicy(
        base_policy=...,
        advice_chain=fake_critic_chain,
    )

    result = policy.evaluate(search_results=[...], retry_count=0)

    assert result.retry_strategy == "switch_to_balanced"
    assert "strict" in result.summary
```

- [ ] **Step 2: Run the hybrid critic test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_hybrid_critic.py -v`
Expected: FAIL because the hybrid critic layer does not exist yet

- [ ] **Step 3: Add critic and response prompts plus schemas**

Create:

- `backend/llm/prompts/critic_review.py`
- `backend/llm/prompts/response_reason.py`
- `backend/llm/schemas/critic.py`
- `backend/llm/schemas/response.py`

- [ ] **Step 4: Implement CriticAdviceChain and ResponseReasonChain**

Create:

- `backend/llm/chains/critic_chain.py`
- `backend/llm/chains/response_chain.py`

These should not own control flow. They should only provide structured advice and explanation.

- [ ] **Step 5: Refactor the critic layer into a hybrid policy**

Split the current critic into:

- `RuleCriticPolicy`
- `HybridCriticPolicy`

The hybrid policy should:

- preserve deterministic retry decisions from rules
- optionally replace or enrich `summary` using chain output

- [ ] **Step 6: Refactor the response node**

Update `ResponseNode` so final item selection remains deterministic, but explanation generation may delegate to `ResponseReasonChain`.

- [ ] **Step 7: Run hybrid critic and response tests**

Run: `.venv/bin/pytest tests/unit/test_hybrid_critic.py tests/unit/test_response_reason_chain.py tests/unit/test_agent_critic_policy.py -v`
Expected: PASS

- [ ] **Step 8: Commit the hybrid critic/response migration**

```bash
git add backend/llm/prompts/critic_review.py backend/llm/prompts/response_reason.py backend/llm/schemas/critic.py backend/llm/schemas/response.py backend/llm/chains/critic_chain.py backend/llm/chains/response_chain.py backend/agents/policies/critic_policy.py backend/agents/nodes/critic_node.py backend/agents/nodes/response_node.py tests/unit/test_hybrid_critic.py tests/unit/test_response_reason_chain.py tests/unit/test_agent_critic_policy.py
git commit -m "feat: add hybrid langchain critic and response"
```

---

### Task 5: Simplify Factories, Remove Ad Hoc Prompt Plumbing, and Verify End-to-End Integration

**Files:**
- Modify: `backend/services/retrieval/factory.py`
- Modify: `backend/services/retrieval_preparation/factory.py`
- Modify: `backend/agents/factory.py`
- Modify: `tests/integration/test_retrieval_service.py`
- Modify: `tests/integration/test_visual_search_graph.py`
- Modify: `tests/integration/test_search_agent.py`

- [ ] **Step 1: Write a failing integration test that ensures the graph still works with LangChain-backed nodes**

```python
def test_visual_search_graph_runs_with_langchain_backed_capabilities(...) -> None:
    ...
```

- [ ] **Step 2: Run the integration tests to verify the final migration layer is not complete yet**

Run: `.venv/bin/pytest tests/integration/test_visual_search_graph.py tests/integration/test_search_agent.py tests/integration/test_retrieval_service.py -v`
Expected: FAIL or remain incomplete until the factories are rewired

- [ ] **Step 3: Simplify retrieval and retrieval-preparation factories**

Update factories so they:

- assemble provider-aware chains
- inject them into services and nodes
- stop owning prompt strings directly

This is the point where old prompt text should leave the factories entirely.

- [ ] **Step 4: Rewire the agent factory to consume capability-layer chains**

`backend/agents/factory.py` should become a clean dependency assembler for:

- provider-backed chains
- retrieval service
- hybrid critic
- response chain

- [ ] **Step 5: Remove obsolete ad hoc model-calling code paths**

Delete or drastically slim any code that is now redundant, especially:

- manual prompt bodies left in factories
- duplicated JSON parsing helpers no longer used
- chain-internal logic that still leaks into nodes

- [ ] **Step 6: Run the focused end-to-end verification suite**

Run: `.venv/bin/pytest tests/integration/test_retrieval_service.py tests/integration/test_visual_search_graph.py tests/integration/test_search_agent.py tests/unit/test_agent_contracts.py tests/unit/test_agent_planner.py tests/unit/test_agent_critic_policy.py tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 7: Commit the final LangChain integration cleanup**

```bash
git add backend/services/retrieval/factory.py backend/services/retrieval_preparation/factory.py backend/agents/factory.py tests/integration/test_retrieval_service.py tests/integration/test_visual_search_graph.py tests/integration/test_search_agent.py
git commit -m "refactor: unify museaagent capabilities behind langchain"
```

---

## Delivery Notes

- Do not rewrite retrieval SQL or fusion logic into LangChain abstractions.
- Do not let graph nodes absorb prompt logic while doing this migration.
- Keep deterministic control over retry semantics even after critic and response chains are introduced.
- Prefer schema-first structured outputs everywhere; avoid ad hoc parsing in capability consumers.

## Plan Self-Review

- Spec coverage: this plan covers provider abstraction, retrieval-preparation migration, intelligent node migration, hybrid critic/response upgrades, and factory cleanup from the LangChain capability-layer spec.
- Red-flag scan: no task depends on vague “wire it up later” language without file targets or verification steps.
- Type consistency: the plan preserves the existing `SearchSpec`, `SearchResult`, `CriticResult`, and graph-state contracts while moving model execution behind capability chains.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-31-museaagent-langchain-capability-layer-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
