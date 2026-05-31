# MuseaAgent LangChain Capability Layer Design

> Scope: Provider-agnostic LangChain integration for MuseaAgent capability execution, with LangGraph retained as the orchestration layer

---

## 1. Goal

This design defines the ideal LangChain integration for MuseaAgent.

The key architectural decision is:

- LangGraph remains the workflow orchestration layer
- LangChain becomes the standardized capability layer for model-driven work

The purpose of this integration is not to "use LangChain somewhere in the stack."

The purpose is to standardize how MuseaAgent performs:

- prompt management
- provider selection
- structured output parsing
- node-internal model execution
- capability-level tracing and fallback boundaries

while keeping retrieval execution, repositories, SQL, fusion, and rerank outside LangChain.

This design aims for the long-term ideal state rather than a minimal incremental patch.

---

## 2. Scope

This design covers:

- architectural boundaries between LangChain, LangGraph, and application services
- provider-agnostic model abstraction
- prompt and schema organization
- LangChain chain boundaries for retrieval preparation and agent nodes
- optional tool wrapping boundaries
- critic and response evolution toward hybrid rule-plus-chain behavior
- migration targets in the current codebase
- tracing and runtime standardization expectations

This design does not cover:

- LangGraph replacement
- SQL retrieval redesign
- repository redesign
- database schema changes
- UI or API contract redesign beyond what is required for capability integration
- LangChain internal implementation details

---

## 3. Current State

MuseaAgent already has a meaningful Phase 4 and Phase 5 split:

- retrieval preparation and retrieval execution exist as reusable services
- LangGraph is now used for explicit orchestration
- Phase 5 nodes and state boundaries already exist

However, model-driven capability execution is still inconsistent.

The current codebase contains several repeated patterns:

- prompt strings embedded directly inside factories
- repeated "return JSON only" prompt instructions
- manual markdown-fence stripping
- manual `json.loads(...)`
- manual `Pydantic.model_validate(...)`
- provider-specific model wiring leaking into application factories

These patterns are visible in:

- `backend/services/retrieval/factory.py`
- `backend/services/retrieval_preparation/understanding.py`
- `backend/services/retrieval_preparation/rewrite.py`

At the same time, some agent nodes are still intentionally simple:

- `IntentNode` is heuristic
- `PlannerNode` is deterministic
- `CriticPolicy` is rules-first

This creates the correct opportunity:

- keep the orchestration structure
- replace ad hoc model-calling patterns with a formal capability layer

---

## 4. Core Design Decision

MuseaAgent should adopt this division of responsibility:

### 4.1 LangGraph Owns Workflow

LangGraph should continue to own:

- explicit state
- node sequencing
- conditional routing
- retry loops
- runtime orchestration

LangGraph should not own:

- provider-specific model invocation details
- prompt text
- structured output parsing logic

### 4.2 LangChain Owns Model-Driven Capability Execution

LangChain should own:

- prompt templates
- structured output contracts
- model invocation wrappers
- provider-neutral capability chains
- optional tool wrappers

LangChain should not own:

- workflow routing
- repository logic
- SQL retrieval
- fusion or deterministic rerank

### 4.3 Application Services Own Retrieval Execution

Existing retrieval and business execution services should continue to own:

- retrieval preparation fallback logic
- vector recall
- FTS recall
- SQL and repository calls
- candidate fusion
- deterministic rerank

LangChain is not introduced to replace business execution code that is already deterministic and well-bounded.

---

## 5. Target Architecture

The recommended long-term architecture is a four-layer model:

### 5.1 Provider Layer

This layer isolates model provider differences.

Responsibilities:

- create a provider-agnostic chat model abstraction
- map configuration to provider adapters
- isolate OpenAI, Gemini, OpenRouter, and future providers

### 5.2 LangChain Capability Layer

This layer is the primary LangChain home.

Responsibilities:

- prompt definitions
- schema-first structured outputs
- capability-specific chains
- optional tool wrappers
- invocation helpers and tracing hooks

### 5.3 Application Service Layer

This layer remains ordinary application code.

Responsibilities:

- retrieval execution
- repository access
- fusion
- rerank
- business-level fallbacks
- service contracts

### 5.4 LangGraph Orchestration Layer

This layer remains the orchestration top.

Responsibilities:

- state transitions
- node routing
- retry control
- final graph execution

In short:

- LangChain defines what happens inside intelligent capabilities
- LangGraph defines how those capabilities are sequenced

---

## 6. Target File Structure

The recommended target structure is:

```text
backend/
  llm/
    providers/
      __init__.py
      base.py
      openai.py
      gemini.py
      openrouter.py
      factory.py

    prompts/
      retrieval_understanding.py
      retrieval_rewrite.py
      intent_classification.py
      search_planning.py
      critic_review.py
      response_reason.py

    schemas/
      retrieval_understanding.py
      retrieval_rewrite.py
      intent.py
      planner.py
      critic.py
      response.py

    chains/
      retrieval_understanding_chain.py
      retrieval_rewrite_chain.py
      intent_chain.py
      planner_chain.py
      critic_chain.py
      response_chain.py

    tools/
      retrieval_tool.py

    runtime/
      invocation.py
      structured_output.py
      tracing.py
```

The design goal is not directory purity for its own sake.

The design goal is to prevent:

- prompt logic from leaking into factories
- provider logic from leaking into business services
- node logic from becoming prompt logic containers

---

## 7. Capability Layer Boundaries

The LangChain capability layer should define stable, reusable units.

### 7.1 RetrievalUnderstandingChain

Purpose:

- consume raw query and mode hint
- return structured understanding

Replaces the current manual model-calling pattern used by `QueryUnderstandingService`.

### 7.2 RetrievalRewriteChain

Purpose:

- consume structured understanding
- produce embedding rewrite, FTS rewrite, and lexical terms

Replaces the current manual rewrite payload generation and parsing pattern.

### 7.3 IntentClassificationChain

Purpose:

- classify task-level intent for graph routing
- optionally determine topic action

This chain should replace the long-term heuristic-only intent strategy.

### 7.4 SearchPlannerChain

Purpose:

- generate structured search plans
- produce `strict`, `balanced`, and `exploratory` search specs

This chain should replace the current hard-coded planner implementation while preserving graph-level plan semantics.

### 7.5 CriticAdviceChain

Purpose:

- provide richer diagnostic explanation
- augment but not replace rule-based retry decisions

This chain is optional in the earliest migration wave but is part of the ideal architecture.

### 7.6 ResponseReasonChain

Purpose:

- generate a clean user-facing explanation of why the chosen results were selected

This chain should remain downstream of deterministic final item selection.

---

## 8. What Stays Outside LangChain

A successful LangChain integration requires strong non-goals.

These parts should remain outside LangChain:

- repositories
- SQL retrieval
- photo-index recall queries
- reciprocal-rank fusion
- deterministic rerank
- route-level session lifecycle
- search-execution node control flow

This is critical.

LangChain should not be used to wrap code merely because it exists in an agent system.

LangChain should only be used where it simplifies model-driven capability execution.

---

## 9. Standardized Invocation Shapes

The project should standardize on three capability shapes.

### 9.1 Structured Chain

This is the default shape.

Use for:

- understanding
- rewrite
- intent
- planner
- critic advice
- response explanation

Call shape:

```python
result = chain.invoke(input_payload)
```

Result:

- typed structured schema

### 9.2 Tool Wrapper

Use selectively for exposing deterministic services to model-driven chains.

Use for:

- retrieval service
- possible future external tools

This is not mandatory for all services in the first implementation wave.

### 9.3 Hybrid Policy

Use when deterministic control should stay primary.

Use for:

- critic
- response

Pattern:

- rules decide control flow
- LangChain chains provide richer interpretation, explanation, or advice

---

## 10. Migration Targets in the Current Codebase

### 10.1 First Migration Wave

These files should be migrated first:

- `backend/services/retrieval_preparation/understanding.py`
- `backend/services/retrieval_preparation/rewrite.py`

After migration:

- they should stop owning raw prompt construction
- they should stop owning manual JSON parsing
- they should become service-level wrappers around LangChain chains

### 10.2 Second Migration Wave

These files should migrate next:

- `backend/agents/nodes/intent_node.py`
- `backend/agents/nodes/planner_node.py`

After migration:

- nodes become thin state adapters
- intelligent behavior moves into `IntentClassificationChain` and `SearchPlannerChain`

### 10.3 Third Migration Wave

These files evolve next:

- `backend/agents/policies/critic_policy.py`
- `backend/agents/nodes/response_node.py`

After migration:

- rule logic remains primary
- LangChain advisory chains augment summary and explanation quality

### 10.4 Supporting Migration

These factories should be simplified after capability extraction:

- `backend/services/retrieval/factory.py`
- `backend/services/retrieval_preparation/factory.py`

Their future role should be:

- dependency assembly
- provider injection
- no embedded prompt bodies

---

## 11. Provider-Agnostic Model Strategy

MuseaAgent should not bind LangChain integration to one provider.

The provider abstraction should:

- choose provider by capability or config
- allow different chains to use different models
- support OpenAI, Gemini, OpenRouter, and future additions

The capability layer should not care whether a model came from:

- OpenAI
- Gemini
- OpenRouter
- another provider

It should receive a provider-neutral chat model abstraction from the provider layer.

This is one of the main reasons for introducing LangChain systematically rather than ad hoc.

---

## 12. Observability and Tracing Expectations

The LangChain capability layer should make tracing more consistent.

It should support:

- capability name tagging
- provider/model tagging
- structured invocation metadata
- failure classification
- fallback visibility

The project does not need full LangSmith dependence to benefit from this structure.

Even if tracing remains local-first, the runtime should consistently capture:

- which chain ran
- which provider/model served it
- whether fallback ran
- which structured schema was expected

---

## 13. Target End State

This LangChain integration should be considered successful when all of these are true:

- model-driven capability execution no longer uses ad hoc prompt-plus-JSON parsing patterns
- LangGraph remains the explicit workflow orchestrator
- retrieval execution remains a business service rather than a LangChain abstraction accident
- provider configuration is centralized and capability-aware
- nodes are thinner and no longer own prompt logic
- prompt text and structured schemas live in formal capability modules
- critic and response can support richer language without losing deterministic control

This is the desired ideal-state architecture for MuseaAgent.

---

## 14. Summary

The right way to introduce LangChain into MuseaAgent is not to replace LangGraph and not to wrap the entire project in generic chain abstractions.

The right move is to formalize a capability layer:

- provider-agnostic
- schema-first
- prompt-organized
- chain-based
- orchestration-clean

That lets MuseaAgent keep its strong workflow boundaries while replacing fragile ad hoc model-calling patterns with a maintainable capability architecture.
