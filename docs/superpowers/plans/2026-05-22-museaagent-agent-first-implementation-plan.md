# MuseaAgent Agent-First MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an agent-first visual search backend that can ingest image metadata, run hybrid retrieval, expose a synchronous agent search interface, and later evolve into a multi-turn chat experience.

**Architecture:** The system is delivered in layers. First establish the backend skeleton and persistence boundaries, then build the retrieval core, then add agent orchestration, then add chat and evaluation on top. The synchronous search entry remains throughout as the stable debugging and benchmarking surface, while chat is treated as the interaction layer above the same pipeline.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, PostgreSQL/pgvector, LangGraph, pytest

---

## Planning Principles

- This plan stays at the module and milestone level.
- It intentionally does not lock detailed schema fields, SQL shapes, prompt text, or local command paths.
- Data contracts, exact field design, and lower-level implementation choices should be refined when each task starts.
- The primary purpose of this plan is to define sequencing, ownership boundaries, and acceptance criteria.

## Proposed Module Boundaries

- `API layer`
  - Owns HTTP and SSE endpoints only
  - Translates requests into application calls and returns structured responses
- `Persistence layer`
  - Owns database access and storage concerns
  - Hides SQL and storage details from the rest of the system
- `Retrieval core`
  - Owns query normalization, embeddings, hybrid retrieval, fusion, and rerank
  - Must be callable independently from chat
- `Agent orchestration layer`
  - Owns intent understanding, constraint extraction, query planning, critic, retry, and response composition
  - Uses retrieval core as its foundation
- `Conversation layer`
  - Owns multi-turn state, conversation persistence, and SSE streaming behavior
- `Operational layer`
  - Owns ingestion, evaluation, internal triggers, and observability hooks

---

### Task 1: Backend Skeleton and Project Conventions

**Objective:** Establish the runnable backend shell and the minimum project structure needed for incremental delivery.

**Scope:**
- Create the initial application entrypoint
- Add a health endpoint
- Establish configuration loading and dependency wiring conventions
- Create the top-level module layout for API, services, repositories, agents, schemas, migrations, scripts, and tests

**Key decisions to confirm during execution:**
- How configuration is loaded
- How environment separation is handled
- How dependencies are injected across services and graph nodes

**Acceptance criteria:**
- The backend process starts cleanly
- A health endpoint responds successfully
- The directory structure is clear enough to support later phases without major reshaping

---

### Task 2: Database Foundation and Persistence Boundaries

**Objective:** Define the initial database bootstrap and repository interfaces without overcommitting to final field-level contracts.

**Scope:**
- Add the first migration covering the main storage entities from the design
- Establish repository boundaries for photos, conversations, messages, logs, and feedback
- Decide how application models are translated to and from storage rows

**Key decisions to confirm during execution:**
- Which fields are essential for MVP versus deferrable
- Which derived values should be persisted versus computed on read
- How much search trace data is needed in the first logging pass

**Acceptance criteria:**
- The initial schema can support ingestion, search, chat history, and evaluation logging
- The rest of the codebase can depend on repositories without knowing SQL details

---

### Task 3: Query Normalization and Shared Search Contracts

**Objective:** Introduce a shared contract for search requests and a first-pass normalization layer that turns user language into retrieval-friendly input.

**Scope:**
- Define request and response model boundaries for search
- Implement a first version of query normalization
- Support mode resolution and structured constraints at a coarse level
- Treat Chinese natural-language input as a first-class scenario

**Key decisions to confirm during execution:**
- How much of normalization should be deterministic rules versus model-assisted
- Which constraints count as hard constraints in MVP
- How rewritten queries should be represented for downstream retrieval and debugging

**Acceptance criteria:**
- A single normalized representation can be passed from API to retrieval to agent graph
- The system can turn a Chinese request into a retrieval-friendly representation

---

### Task 4: Hybrid Retrieval Core

**Objective:** Build the retrieval foundation that combines semantic search, keyword search, filtering, fusion, and first-pass reranking.

**Scope:**
- Add embedding generation abstraction
- Implement vector retrieval
- Implement full-text retrieval
- Apply structured filters
- Fuse and rerank results

**Key decisions to confirm during execution:**
- Whether the first embedding implementation is real or stubbed
- How vector and FTS candidates are merged
- Which scoring signals are mandatory in MVP

**Acceptance criteria:**
- Retrieval can be executed independently of chat
- The service can return ranked results for normalized queries
- The scoring pipeline is explicit enough to support later critic and evaluation work

---

### Task 5: Minimum Agent Graph

**Objective:** Turn retrieval into a real agent pipeline by adding orchestration nodes around it.

**Scope:**
- Define the shared graph state
- Add nodes for intent, constraint extraction, query planning, retrieval orchestration, rerank, critic, and response composition
- Wire the first conditional retry path

**Key decisions to confirm during execution:**
- Which parts of the graph are deterministic first and which need model calls immediately
- What constitutes a retry-worthy failure in MVP
- How much graph state is persisted versus ephemeral

**Acceptance criteria:**
- The pipeline can accept a user request and return final items plus an explanation layer
- The graph can distinguish at least basic refine-versus-reset behavior
- A single retry path exists and is observable

---

### Task 6: Synchronous Agent Search API

**Objective:** Expose the shared pipeline through a stable synchronous endpoint for early product integration and debugging.

**Scope:**
- Add the main photo search endpoint
- Make the endpoint call the agent pipeline rather than bypassing it
- Return normalized intent/planning context and final ranked items in one response

**Key decisions to confirm during execution:**
- How much internal reasoning is exposed in the API response
- Whether the API surface should distinguish debugging and product payloads
- How response shape balances product needs and evaluation needs

**Acceptance criteria:**
- The endpoint can serve as the first external integration point
- The endpoint uses the same core pipeline that chat will later use
- The response is useful both for UI integration and agent debugging

---

### Task 7: Ingestion Pipeline and Internal Triggers

**Objective:** Create the data growth path that enriches incoming photos and writes searchable records.

**Scope:**
- Implement ingestion orchestration
- Add metadata enrichment, search text construction, and embedding generation flow
- Add internal trigger endpoints for batch ingestion
- Add a cold-start path for local or offline initialization

**Key decisions to confirm during execution:**
- What “analysis success” means for write eligibility
- Which failures are retried and which are skipped
- How ingestion progress is tracked and surfaced

**Acceptance criteria:**
- New photos can be processed end-to-end into searchable records
- Failed items do not block whole-batch progress
- The backend has an operational path for both cold start and incremental growth

---

### Task 8: Conversation Layer and Chat Streaming

**Objective:** Add the multi-turn interaction layer without changing the underlying retrieval and agent core.

**Scope:**
- Add conversation and message persistence
- Add conversation CRUD endpoints
- Add chat streaming endpoint
- Stream agent progress and results in phases
- Support simple constraint inheritance for follow-up turns

**Key decisions to confirm during execution:**
- What gets persisted from each turn
- Which events are required for the first SSE contract
- How follow-up turns reuse prior constraints and when they reset context

**Acceptance criteria:**
- Chat uses the same core search pipeline as the synchronous endpoint
- Streaming exposes meaningful step progression to the client
- Follow-up queries can refine previous constraints in at least simple cases

---

### Task 9: Evaluation and Operational Feedback Loop

**Objective:** Add the minimum evaluation harness needed to compare retrieval and agent behavior over time.

**Scope:**
- Add an evaluation runner
- Define a fixed seed query set
- Compare minimum-agent and fuller-agent behavior
- Add internal hooks for evaluation execution

**Key decisions to confirm during execution:**
- Which metrics are mandatory in the first pass
- How much of evaluation is automated versus manually judged
- Whether logs and evaluation outputs live only in the database or also in exported artifacts

**Acceptance criteria:**
- The team can run a repeatable evaluation pass
- The system can compare baseline retrieval behavior and fuller agent behavior
- The project has a concrete way to observe whether later changes improve or regress quality

---

## Recommended Delivery Order

1. Backend skeleton
2. Database foundation
3. Query normalization and search contracts
4. Hybrid retrieval core
5. Minimum agent graph
6. Synchronous agent search API
7. Ingestion pipeline
8. Conversation layer and chat streaming
9. Evaluation loop

## Cross-Cutting Review Topics

These should be revisited at the start of each implementation task instead of being frozen upfront:

- Exact schema fields
- Prompt design
- Logging granularity
- Retry conditions
- API payload detail level
- Evaluation metrics and rubric

## Plan Self-Review

- Scope check: the plan stays at the milestone level and does not prematurely lock implementation details.
- Coverage check: the plan covers ingestion, retrieval, orchestration, synchronous search, chat, and evaluation from the design.
- Flexibility check: field-level and prompt-level choices remain open for later discussion.
