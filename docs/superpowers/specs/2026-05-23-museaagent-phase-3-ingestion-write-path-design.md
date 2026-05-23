# MuseaAgent Phase 3 Ingestion Write Path Design

> Scope: Full indexing write path for Phase 3 only

---

## 1. Goal

Phase 3 defines the full write path that turns Unsplash source photos into completed `photo_index` records.

This phase is about designing a reusable single-photo indexing pipeline that can be shared by:

- cold-start dataset import
- Unsplash API incremental sync

The goal is not to design retrieval behavior yet. The goal is to make sure every indexed photo is produced through a clear, complete, and consistent enrichment pipeline before it becomes searchable.

---

## 2. Scope

Phase 3 covers:

- source photo normalization
- single-photo text preparation
- English retrieval text generation
- external model invocation boundaries for translation, visual understanding, and embedding
- image and text semantic enrichment
- caption generation
- tag extraction
- product-oriented scoring
- embedding generation
- final validation before indexing
- atomic persistence into `photo_index`
- top-level scheduling differences between cold start and incremental sync
- lightweight operational logging at the run level

Phase 3 does not cover:

- retrieval scoring and read-path ranking logic
- query normalization for user search requests
- LangGraph or agent orchestration
- synchronous search API behavior
- multi-turn chat or SSE streaming
- detailed retry systems
- formal reindex workflows
- queue-based or event-driven execution architecture

---

## 3. Design Principles

### 3.1 Single-Photo Pipeline Is the Core

The core unit of Phase 3 is not the batch job. It is the processing of one source photo into one completed index record.

Cold start and incremental sync differ only in how they discover candidate photos. They must both reuse the same single-photo pipeline.

### 3.2 Clear Node Boundaries, Simple Scheduling

The write path should be divided into clear logical nodes with explicit responsibilities.

However, the scheduling model should remain simple:

- a batch source enumerates candidate photos
- each candidate photo is processed through one unified pipeline
- the pipeline runs as one application-level job for that photo

Phase 3 does not require stage-level persistence or complex orchestration.

### 3.3 Completed Records Only

`photo_index` must contain completed searchable records only.

This means:

- processing does not insert placeholder rows before enrichment completes
- partial or failed indexing work does not enter the retrieval table
- persistence happens only after final validation succeeds

Phase 3 assumes the team may rebuild existing index contents when introducing the completed-record contract.

This means the schema evolution for this phase does not need to preserve partially indexed or Phase 2-style placeholder rows as long as:

- source-of-truth photo data remains available from the cold-start dataset or incremental source
- the Phase 3 pipeline can regenerate completed index rows from source data

### 3.4 Retrieval-Facing Data Over Process Data

The primary output of this phase is high-quality retrieval-facing data.

The database should store the final indexed representation needed for later retrieval, not the internal temporary state used while producing it.

### 3.5 Rich Enrichment Is Part of the Main Path

Captioning, tagging, semantic flags, and product-oriented scores are part of the indexing contract in this phase.

They are not optional extras layered on later. They are part of what makes a photo indexable for MuseaAgent.

### 3.6 Model Calls Stay Behind Stable Adapters

Phase 3 does not hard-code indexing nodes directly against one vendor SDK or one prompt surface.

Instead, model-backed steps should be isolated behind narrow application-facing adapters so that:

- pipeline orchestration remains stable
- prompt and provider iteration stays local to model-facing modules
- stub or fake implementations can support tests

The pipeline should depend on capabilities such as translation, visual enrichment, and embedding generation, not on raw SDK calls scattered across nodes.

### 3.7 Lightweight Operations Layer

Operational visibility matters, but it is not the center of this phase.

Run-level logs should stay lightweight and separate from the retrieval index design.

---

## 4. Architecture Overview

Phase 3 is organized into two layers:

1. `Source Scheduling Layer`
2. `Single-Photo Enrichment Pipeline`
3. `Model Invocation Layer`

### 4.1 Source Scheduling Layer

This layer finds photos that should be processed.

It is responsible for:

- reading source items from cold-start datasets or Unsplash API pages
- deciding which source items should be passed to indexing
- invoking the shared single-photo pipeline
- recording lightweight run-level logs

It is not responsible for:

- generating retrieval text
- image understanding
- tag extraction
- embedding generation
- direct writes to `photo_index`

### 4.2 Single-Photo Enrichment Pipeline

This layer transforms one normalized source photo into one completed `photo_index` record.

It is responsible for:

- constructing text artifacts
- producing semantic enrichment
- generating embeddings
- validating output completeness
- atomically writing the final index record

This layer is the only place where indexing semantics are defined.

### 4.3 Model Invocation Layer

This layer provides the concrete bridge from indexing nodes to external AI models.

It is responsible for:

- sending translation requests to a text model or translation-capable model
- sending image-plus-text requests to a vision-language model for captioning and semantic enrichment
- sending embedding requests to the selected embedding model
- mapping raw provider responses into stable application-level outputs

It is not responsible for:

- batch scheduling policy
- repository writes
- pipeline orchestration
- source payload normalization

This layer exists so that the rest of the write path can reason in terms of stable capabilities rather than vendor-specific request shapes.

---

## 5. Single-Photo Enrichment Pipeline

The pipeline is composed of the following logical nodes:

1. `Source Normalize`
2. `Text Assembly`
3. `Translation and Normalization`
4. `Semantic Enrichment`
5. `Scoring`
6. `Embedding`
7. `Final Validation`
8. `Atomic Persist`

### 5.1 Source Normalize

Input:

- raw Unsplash photo payload

Output:

- normalized source photo object

Responsibilities:

- extract the source identifiers required downstream
- extract the raw descriptive fields needed for enrichment
- extract structural metadata such as orientation and dimensions
- normalize field presence and empty-value handling
- isolate downstream code from Unsplash payload shape changes

This node should produce a stable application-facing source object so later nodes do not depend directly on raw upstream JSON.

### 5.2 Text Assembly

Input:

- normalized source photo object

Output:

- `source_text`
- `analysis_text`

Responsibilities:

- combine raw title, description, alt description, and other usable source text
- clean whitespace and empty fragments
- preserve source semantics in a readable concatenated form
- prepare a stable text input for later translation and enrichment steps

`source_text` exists primarily for retrieval traceability and debugging.

`analysis_text` exists as the best prepared text input for downstream enrichment tasks.

### 5.3 Translation and Normalization

Input:

- normalized source photo object
- `analysis_text`

Output:

- `search_text`

Responsibilities:

- translate non-English source text into English when needed
- normalize phrasing into retrieval-friendly English
- preserve scene terms, style terms, subject terms, and descriptive constraints
- avoid empty or overly lossy output

Implementation expectation:

- this node should call a model-facing translation adapter
- the adapter may use a general LLM or a dedicated translation-capable model
- the output contract remains a single retrieval-oriented English `search_text`

`search_text` is the primary textual retrieval field written into `photo_index`.

### 5.4 Semantic Enrichment

Input:

- normalized source photo object
- image asset
- `analysis_text`
- `search_text`

Output:

- `ai_caption`
- `ai_short_caption`
- `scene_tags`
- `mood_tags`
- `style_tags`
- `composition_tags`
- `lighting_tags`
- `color_tags`
- `subject_tags`
- `use_case_tags`
- `has_human`
- `has_face`
- `is_abstract`
- `is_minimal`
- `is_dark`
- `dominant_colors`

Responsibilities:

- describe the image in retrieval-relevant language
- convert visual semantics into stable structured fields
- capture descriptive signals that may later help ranking or filtering

Implementation expectation:

- this node should call a vision-language model through a semantic enrichment adapter
- the adapter should accept the image input together with prepared text context
- the adapter should return structured outputs that the pipeline can trust without provider-specific parsing leaking outward

This node is about understanding the image and representing that understanding in a retrieval-oriented structure.

### 5.5 Scoring

Input:

- semantic enrichment outputs

Output:

- `wallpaper_score`
- `photography_reference_score`

Responsibilities:

- convert general semantic understanding into product-facing utility scores
- estimate how suitable a photo is for wallpaper-oriented and photography-reference-oriented use cases

Implementation expectation:

- scoring may initially be implemented as deterministic logic over semantic enrichment outputs
- if later moved to a model-assisted scorer, the scorer should still remain a separate node behind its own adapter boundary

This node does not determine whether the photo is indexable. It produces value-added ranking signals for later phases.

### 5.6 Embedding

Input:

- `search_text`
- caption and high-value semantic outputs

Output:

- `embedding`

Responsibilities:

- generate the vector representation used by later semantic retrieval
- reflect the final retrieval-oriented understanding of the photo rather than raw source text alone

Implementation expectation:

- this node should call a dedicated embedding adapter
- the adapter should hide provider request details, model naming, batching rules, and dimensional assumptions from the pipeline
- the adapter should expose a single responsibility: transform finalized retrieval semantics into one embedding vector

The embedding input should be based on the finalized retrieval semantics of the photo, not only the original metadata quality.

### 5.7 Final Validation

Input:

- all pipeline outputs

Output:

- completed index record payload

Responsibilities:

- confirm required indexing fields are present
- reject incomplete outputs that do not meet Phase 3 completeness standards
- assemble the final persistence payload

This node is the gate that enforces the meaning of a completed searchable record.

### 5.8 Atomic Persist

Input:

- validated index record payload

Output:

- completed `photo_index` write

Responsibilities:

- write the final record in one persistence operation
- preserve the contract that `photo_index` stores completed records only

This node should not perform new enrichment logic. It should only persist the final output.

---

## 6. Pipeline Context and Node Contracts

The pipeline should pass a structured in-memory context object across nodes.

This context should remain application-level and should not be persisted as process state.

Recommended context sections:

- `source`
- `text_artifacts`
- `semantic_artifacts`
- `retrieval_artifacts`

### 6.1 `source`

Contains the normalized source photo and source-level metadata needed across the pipeline.

### 6.2 `text_artifacts`

Contains:

- `source_text`
- `analysis_text`
- `search_text`

This section is owned by text-focused nodes.

### 6.3 `semantic_artifacts`

Contains:

- captions
- tag buckets
- boolean semantic flags
- dominant colors
- product-oriented scores

This section is owned by semantic enrichment and scoring nodes.

### 6.4 `retrieval_artifacts`

Contains:

- `embedding`
- final persistence-ready indexing payload

This section is owned by embedding, validation, and persistence preparation.

This contract keeps node boundaries clear while avoiding database-backed intermediate state.

---

## 7. External Model Invocation Design

Phase 3 should make model usage explicit instead of treating it as an implementation afterthought.

Three model-backed capabilities are required in the write path:

1. translation and retrieval-text normalization
2. image-plus-text semantic enrichment
3. embedding generation

### 7.1 Translation Capability

Purpose:

- transform source-side descriptive text into retrieval-oriented English

Recommended adapter contract:

- input: `analysis_text`
- output: `search_text`

Design constraints:

- the adapter should preserve concrete descriptive vocabulary over fluency
- the adapter should be usable as a synchronous single-item call from the pipeline
- tests should be able to replace it with a deterministic fake implementation

### 7.2 Semantic Enrichment Capability

Purpose:

- generate the caption, short caption, tags, boolean semantic flags, and dominant colors

Recommended adapter contract:

- input: image reference plus prepared text context
- output: structured semantic artifacts

Design constraints:

- the adapter should centralize prompt structure and output parsing
- the pipeline should consume parsed structured results rather than raw provider JSON or free-form text
- image understanding should be grounded in both the photo itself and the assembled source text when available

### 7.3 Embedding Capability

Purpose:

- generate the final vector used by later semantic retrieval

Recommended adapter contract:

- input: finalized retrieval-oriented text package
- output: embedding vector

Design constraints:

- the embedding request should be based on the finalized semantic representation, not only raw source metadata
- the dimensionality assumption belongs inside the embedding module and persistence contract, not inside the pipeline orchestrator
- tests should be able to inject fixed vectors

### 7.4 Provider Isolation

All provider-specific concerns should remain inside the model invocation layer, including:

- model names
- request payload formats
- authentication
- timeout configuration
- response parsing
- prompt templates

The pipeline should only know about capability interfaces.

### 7.5 Recommended Phase 3 Model Topology

Phase 3 should use a simple and explicit model topology:

- one text-capable or multimodal LLM for translation and retrieval-text normalization
- one multimodal LLM for semantic enrichment
- one dedicated embedding model for vector generation

Recommended decision:

- keep translation and semantic enrichment as two separate capability calls, even if they use the same provider family
- keep embedding as an independent capability instead of reusing a generative model for pseudo-embeddings

This split is recommended because it preserves clean node boundaries:

- translation is a text transformation task
- semantic enrichment is an image-understanding task
- embedding is a retrieval-vector task

Phase 3 should optimize for clarity of responsibility over minimizing the raw number of external calls.

### 7.6 Image Input Strategy

For semantic enrichment, the model invocation layer should prefer passing a stable image URL from the normalized source photo rather than downloading image bytes inside the pipeline.

Recommended default:

- use the normalized Unsplash image URL as the image input reference

Reasons:

- the source already provides a stable hosted image asset
- the pipeline remains simpler because it does not need an image download stage
- model adapters can stay focused on model invocation rather than file transport

Deferred fallback:

- if a future provider requires uploaded bytes instead of URL input, that transport adaptation should be implemented inside the semantic enrichment adapter, not in the pipeline orchestrator

### 7.7 Call Sequencing in the Single-Photo Pipeline

The recommended model-call order for one photo is:

1. translation call on `analysis_text`
2. semantic enrichment call on image URL plus prepared text context
3. deterministic scoring over semantic outputs
4. embedding call on finalized retrieval semantics

This sequence is recommended because:

- `search_text` should exist before semantic enrichment finishes, so the vision-language step can benefit from the retrieval-oriented text form
- scoring should remain a lightweight local transformation unless a later phase proves otherwise
- embedding should happen after caption and tags are available so the vector reflects the finalized semantic representation

### 7.8 Finalized Embedding Input Package

The embedding adapter should not receive only raw `search_text`.

Instead, it should build the vector from a compact finalized semantic package derived from:

- `search_text`
- `ai_caption`
- selected high-value tags such as scene, style, mood, and subject

The intent is to generate vectors from the system's best final understanding of the photo, not from raw source metadata alone.

### 7.9 Provider Configuration Surface

Phase 3 should treat provider configuration as part of the adapter boundary.

Recommended configuration categories:

- provider name
- model name
- API base URL when relevant
- API key or credential reference
- timeout budget

These belong in application configuration and should be consumed by the model adapters rather than the pipeline orchestration layer.

### 7.10 Provider Strategy for Phase 3

Phase 3 should default to a multi-provider gateway style design rather than binding the system to one model vendor.

Recommended decision:

- adapters should be written against a provider-agnostic internal capability contract
- the concrete backend may point to OpenAI-compatible endpoints, OpenRouter-style gateways, or another compatible provider surface
- concrete model selection should be injected through configuration

This means the design should assume flexibility at two levels:

- provider routing
- model selection per capability

Recommended configuration dimensions:

- `translation_provider`
- `translation_model`
- `enrichment_provider`
- `enrichment_model`
- `embedding_provider`
- `embedding_model`
- provider base URL where needed
- provider API key reference where needed

The important constraint is that configuration chooses providers and models. The pipeline and node contracts do not.

---

## 8. Success Criteria for a Single Indexed Photo

A photo is considered successfully indexed only if the pipeline can produce a complete final record that passes validation.

Minimum success conditions:

- source normalization succeeds
- source identifiers are present
- `source_text` is generated
- `search_text` is generated and non-empty
- captioning and semantic enrichment produce usable outputs
- embedding generation succeeds
- final persistence payload conforms to the `photo_index` schema contract

If these conditions are not met, the photo is not written into `photo_index`.

This is intentionally stricter than a "best effort partial write" approach because the table is intended to remain a completed-searchable-record set.

---

## 9. Persistence Contract for Completed Records

Phase 3 writes completed index records into `photo_index`.

The write-side design assumes that this table stores:

- source identity
- source structural metadata needed by retrieval
- retrieval text fields
- semantic enrichment fields
- product-oriented scores
- embedding
- completion timestamps

It should not store:

- process-stage checkpoints
- incomplete or pending records
- detailed execution state for failed runs

Phase 3 keeps `photo_index` focused on retrieval-ready data only.

---

## 10. Source Scheduling Layer

The scheduling layer exists to feed candidate photos into the single-photo pipeline.

It should support two entry paths:

1. `Cold Start Import`
2. `Incremental Sync`

### 9.1 Cold Start Import

Cold start import processes a historical dataset or snapshot in batches.

Responsibilities:

- iterate over source items from a local dataset or equivalent cold-start source
- group work into manageable batches
- invoke the shared single-photo pipeline for each item

### 9.2 Incremental Sync

Incremental sync processes newly discovered or recently changed source photos from Unsplash API fetches.

Responsibilities:

- fetch source items from incremental API entrypoints
- hand candidate items to the shared single-photo pipeline

### 9.3 Shared Constraint

Both entry paths must reuse the same single-photo enrichment pipeline and the same final persistence contract.

They may differ in batching and source enumeration, but they must not fork indexing semantics.

---

## 11. Lightweight Operational Logging

Operational logging is intentionally lightweight in this phase.

Its purpose is to make runs observable without turning runtime operations into a core data model.

Recommended logging focus:

- run started
- run finished
- source type
- trigger type
- total candidates seen
- total succeeded
- total failed

This information may be recorded through application logs or a minimal run-level record, but it is not part of the retrieval contract and should remain operational in nature.

Detailed failure recovery, retry orchestration, and task-system design are deferred.

---

## 12. Internal Trigger Surface

Phase 3 should define lightweight internal entrypoints for starting write-path work.

Recommended trigger types:

- manual cold-start import trigger
- manual incremental sync trigger
- local developer trigger for a single photo or small batch

These entrypoints are operational surfaces for starting indexing work. They are not user-facing product APIs.

Their responsibility is to initiate scheduling-layer work, not to expose the internals of the enrichment pipeline.

---

## 13. Phase Transition Assumption

The move from the Phase 2 minimal index schema to the Phase 3 completed-record schema should be treated as an index-contract transition rather than a strict in-place preservation exercise.

Recommended decision:

- preserve source-of-truth inputs
- allow rebuilding `photo_index` contents through the Phase 3 write path
- avoid designing Phase 3 around backward compatibility for incomplete historical index rows

This keeps the write-path design clean and aligned with the "completed records only" principle.

---

## 14. Acceptance Criteria

Phase 3 is successful when:

- a cold-start import path exists that can feed historical source items into the single-photo pipeline
- an incremental sync path exists that can feed newly discovered source items into the same pipeline
- one shared single-photo pipeline is defined for both entry paths
- external model invocation boundaries are defined for translation, semantic enrichment, and embedding
- the pipeline includes text generation, semantic enrichment, scoring, embedding, final validation, and persistence
- `photo_index` only receives completed index records
- operational logging is present at a lightweight run level

---

## 15. Deferred Topics

The following topics are intentionally deferred beyond Phase 3:

- retrieval read-path design
- agent orchestration
- chat and SSE
- detailed retry systems
- formal reindex workflows
- queue-backed distributed execution
- stage-level persistence of intermediate results
- full evaluation harness design
