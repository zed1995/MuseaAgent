# AGENTS.md

This document is a practical guide for agents and contributors working in this repository.

## What This Project Is

MuseaAgent is a FastAPI backend for visual search over an indexed photo corpus.

Current architecture combines:

- `Phase 4` retrieval primitives and debug surface
- `Phase 5` LangGraph-based agent orchestration
- a provider-agnostic LangChain capability layer for LLM-powered steps

The main product direction is:

- use deterministic retrieval infrastructure for execution
- use LLMs for understanding, planning, and explanation
- use LangGraph to orchestrate multi-step search workflows

## Core Entry Points

- App entry: `backend/main.py`
- App factory: `backend/app.py`
- API router: `backend/api/router.py`
- Main agent route: `GET /api/search/agent`
- Debug retrieval route: `GET /api/search/debug`
- Internal ingestion routes: `POST /api/internal/ingestion/photo`, `POST /api/internal/ingestion/incremental-sync`

Important note:

- `/api/search/debug` is a temporary debug surface for retrieval verification.
- `/api/search/agent` is the formal agent workflow entry.
- The debug route is only mounted when `retrieval.enable_debug_endpoint` is enabled.

## High-Level Architecture

### 1. LangGraph orchestration layer

Location: `backend/agents/`

Responsible for:

- workflow state
- node orchestration
- conditional routing
- retry handling

Current graph shape:

`Intent -> Constraint -> Planner -> Search Execution -> Critic -> Response`

Possible retry path:

`Critic -> prepare_retry -> Search Execution -> Critic -> Response`

Key file:

- `backend/agents/visual_search_graph.py`

### 2. LangChain capability layer

Location: `backend/llm/`

Responsible for:

- provider abstraction
- prompts
- structured output schemas
- chains for understanding, rewrite, intent, planner, critic, response
- shared invocation/runtime helpers

Design principle:

- LangChain owns node-internal LLM capabilities
- LangGraph owns workflow orchestration

### 3. Retrieval and business execution layer

Location: `backend/services/`

Important subareas:

- `retrieval/`: search execution, fusion, rerank, retrieval contracts
- `retrieval_preparation/`: query understanding and rewrite preparation
- `indexing/`: ingestion and cold-start indexing logic

Design principle:

- retrieval execution remains a business/service concern
- do not force SQL, fusion, or deterministic ranking logic into LangChain

### 4. Persistence layer

Locations:

- `backend/models/`
- `backend/repositories/`
- `backend/core/`

This repository uses a strict persistence boundary:

- ORM models never leave the persistence layer
- repositories return record/write DTOs, not ORM instances
- repositories never commit directly
- transaction boundaries belong to the unit of work

## Directory Guide

```text
backend/
  agents/        LangGraph state, nodes, routing, retry policies
  api/           FastAPI routes
  core/          settings, DB config, shared infrastructure
  llm/           LangChain capability layer
  models/        SQLAlchemy ORM models
  repositories/  persistence DTOs and repositories
  schemas/       API response/request schemas
  services/      retrieval, retrieval preparation, indexing
tests/
  unit/          fast tests, no database required
  integration/   DB-backed and route-level tests
docs/
  superpowers/
    specs/       design specs
    plans/       implementation plans
```

## Recommended Working Mental Model

When modifying this codebase, treat it as four cooperating layers:

1. `LLM capability`
2. `workflow orchestration`
3. `retrieval/business execution`
4. `persistence`

Try not to blur these boundaries.

Examples:

- If a node needs smarter structured output, prefer adding or improving a chain in `backend/llm/chains/`.
- If workflow branching changes, update `backend/agents/visual_search_graph.py` and node/policy contracts.
- If search quality changes because of ranking or filtering, change `backend/services/retrieval/`.
- If database contracts change, update models, repositories, and migrations deliberately.

## Current Agent Workflow

The current agent route builds these dependencies:

- retrieval service
- retrieval preparation service
- LangGraph workflow

Then it invokes the workflow with an initial `VisualSearchState`.

The state currently carries fields such as:

- `original_query`
- `mode`
- `hard_constraints`
- `soft_preferences`
- `search_specs`
- `search_results`
- `critic_result`
- `retry_count`
- `final_items`
- `response_reason`

Workflow behavior today:

- `Intent` classifies mode/topic intent
- `Constraint` extracts hard and soft constraints
- `Planner` builds controlled search specs
- `Search Execution` runs retrieval against those specs
- `Critic` decides pass vs retry strategy
- `Response` formats final output

Retry is intentionally constrained:

- retry count is capped
- hard constraints should not be silently dropped
- retry is based on fixed strategies, not open-ended replanning

## Commands

Primary commands:

```bash
make sync
make test
make run
make migrate
make revision MSG="message"
```

Useful direct commands:

```bash
.venv/bin/pytest
.venv/bin/pytest tests/unit/test_visual_search_graph.py -v
.venv/bin/pytest tests/integration/test_search_agent.py -v
```

The dev server runs through `uvicorn` on port `8000` via `make run`.

## Configuration

Settings come from environment variables prefixed with `MUSEA_AGENT_` or from a root `.env` file.

Important categories include:

- database
- retrieval
- agent workflow
- LLM/provider settings

Examples:

- `MUSEA_AGENT_DATABASE__URL`
- `MUSEA_AGENT_ENVIRONMENT`

The root `.env` file is gitignored.

## Testing Guidance

Unit tests should be the default first stop.

Use integration tests when you change:

- route wiring
- database-backed retrieval behavior
- workflow composition across layers

Keep in mind:

- some integration tests depend on PostgreSQL + pgvector
- external DB/network-dependent tests may fail if local environment is not ready

If a change is primarily about:

- graph routing: test `backend/agents/`
- LLM contract parsing: test `backend/llm/`
- retrieval behavior: test `backend/services/retrieval/`

## Migration and Persistence Rules

- Migrations are append-only after merge
- Review autogenerated Alembic output before trusting it
- Do not expose ORM models out of the persistence layer
- Do not call `commit()` from repository methods

## Project Conventions

- Prefer small, thin graph nodes
- Keep prompts out of random business files; place them in `backend/llm/prompts/`
- Keep structured output schemas in `backend/llm/schemas/`
- Prefer provider-agnostic capability wiring over provider-specific calls in application code
- Do not fold the entire retrieval pipeline into one opaque graph node
- Reuse Phase 4 retrieval primitives instead of reimplementing retrieval logic in the graph
- New functions should usually include a short comment when they sit on a main flow, hide a cross-layer boundary, or encode non-obvious decisions
- It is fine to skip comments only when a function is genuinely trivial and its purpose is obvious from the code alone

## When Adding New Agent Behavior

Use this checklist:

1. Decide whether the change belongs to capability, orchestration, retrieval, or persistence.
2. If it is LLM-driven, define schema first.
3. Add or update a chain in `backend/llm/chains/`.
4. Keep graph nodes thin and state-driven.
5. Add or update unit tests close to the changed layer.
6. Add integration coverage if route behavior or multi-layer orchestration changed.

## Documents Worth Reading

- `CLAUDE.md`
- `docs/superpowers/specs/2026-05-30-museaagent-phase-5-agent-workflow-design.md`
- `docs/superpowers/plans/2026-05-30-museaagent-phase-5-agent-workflow-implementation-plan.md`
- `docs/superpowers/specs/2026-05-31-museaagent-langchain-capability-layer-design.md`
- `docs/superpowers/plans/2026-05-31-museaagent-langchain-capability-layer-implementation-plan.md`

## Practical Summary

If you only remember a few things, remember these:

- LangGraph controls the workflow
- LangChain controls the LLM capability layer
- retrieval services execute search, fusion, and ranking
- persistence boundaries are strict
- `/api/search/debug` is for retrieval verification
- `/api/search/agent` is the real agent-facing route
