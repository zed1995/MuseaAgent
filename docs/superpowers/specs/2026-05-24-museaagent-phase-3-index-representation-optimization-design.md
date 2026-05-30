# MuseaAgent Phase 3 Index Representation Optimization Design

> Scope: Improve the Phase 3 indexing output so Phase 4 retrieval can recall and rank photos more accurately, without introducing curated vocabularies or hardcoded semantic mappings.

---

## 1. Goal

This design strengthens the Phase 3 indexing write path so each indexed photo produces richer retrieval-facing representations, and it defines the matching Phase 4 retrieval-side changes required to use those representations in production.

The main objective is:

- improve recall accuracy in Phase 4 without changing the product boundary between indexing and retrieval
- make more of the existing enrichment output usable by vector recall, full-text recall, and deterministic rerank
- ensure the retrieval service actually consumes the new artifacts in production rather than storing them passively
- avoid curated taxonomies, code-level vocabularies, or manually hardcoded semantic expansions

The intended result is that later retrieval stages operate on better index artifacts rather than trying to recover missing semantics at query time.

---

## 2. Problem Statement

The current indexing implementation already stores many useful enrichment fields in `photo_index`, including:

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
- `dominant_colors`
- `has_human`
- `has_face`
- `is_abstract`
- `is_minimal`
- `is_dark`
- `wallpaper_score`
- `photography_reference_score`

However, the current retrieval-facing representations do not fully use them.

Today:

- `search_text` is built mainly from translated source text
- embedding input uses `search_text`, caption, and a small subset of tags
- FTS recall only searches `search_text`
- rerank mostly inspects text and a few scalar scores

This means Phase 3 is already paying the cost of semantic enrichment, but only a narrow slice of that enrichment is actually compiled into forms that retrieval can consume reliably.

The problem is therefore not a lack of stored data. The problem is insufficient representation building.

---

## 3. Constraints

This design must follow these constraints:

1. No curated controlled vocabulary.
2. No code-level hardcoded semantic mapping tables for moods, styles, scenes, colors, or subjects.
3. No static synonym dictionaries embedded in application code.
4. No product change that shifts semantic understanding responsibility into Phase 4 retrieval.
5. No removal of the existing Phase 3 completed-record contract.

The system may still:

- compose model outputs into retrieval-facing fields
- normalize whitespace, casing, deduplication, and empty-value handling
- use generic formatting rules and field weighting
- derive structured retrieval fields from already-produced enrichment output

The distinction is important:

- formatting and representation assembly are allowed
- semantic hand-labeling through hardcoded domain lists is not allowed

---

## 4. Design Principles

### 4.1 Indexing Must Compile Semantics, Not Just Store Them

Phase 3 should not treat enrichment as passive metadata. It should compile enrichment into explicit retrieval artifacts that later stages can use directly.

### 4.2 Representation Building Must Stay Generic

The pipeline may define how different fields are assembled, weighted, and formatted, but it must not rely on handcrafted semantic vocabularies.

### 4.3 Retrieval Views Should Be Deliberately Different

One representation is not enough. Vector recall, FTS recall, and rerank need different views of the same photo.

### 4.4 Existing Enrichment Should Be Reused Before Adding New Model Work

The system should first improve how existing tags, captions, and flags are compiled into retrieval artifacts before introducing new enrichment stages.

### 4.5 Structured Signals Should Remain Structured

Boolean and scalar attributes such as `has_human`, `has_face`, `is_dark`, `is_minimal`, and use-case scores should stay as structured retrieval features rather than being flattened into free text.

---

## 5. Scope

This design covers:

- Phase 3 representation-building changes
- schema additions needed for new retrieval-facing fields
- pipeline changes for assembling richer retrieval artifacts
- repository and retrieval-query changes needed to consume those artifacts
- rerank changes that consume structured Phase 3 features
- production retrieval rollout, observability, and fallback expectations
- test and migration expectations

This design does not cover:

- agent orchestration
- multi-turn memory
- online learning
- manual editorial vocabularies
- handcrafted synonym databases
- approximate nearest-neighbor infrastructure changes beyond current pgvector usage
- full online experimentation infrastructure beyond the search debug and logging surfaces already present

---

## 6. Proposed Architecture

Phase 3 will continue to process one photo through one indexing pipeline, but the pipeline output will be expanded from a single `search_text` plus one embedding into a small bundle of retrieval-facing representations.

The production requirement is:

- every new write-path artifact must correspond to an explicit read-path use
- no new persisted representation field should exist without a retrieval-time consumer

The optimized single-photo pipeline becomes:

1. `Source Normalize`
2. `Text Assembly`
3. `Translation`
4. `Semantic Enrichment`
5. `Scoring`
6. `Representation Compose`
7. `Embedding Build`
8. `Final Validation`
9. `Atomic Persist`

The new node in this design is `Representation Compose`.

---

## 7. Representation Model

### 7.1 New Retrieval-Facing Artifacts

Each indexed photo should produce these retrieval-facing artifacts:

- `search_text`
  A compact English keyword-oriented lexical field preserved for backward compatibility.

- `retrieval_caption_text`
  A readable English sentence-level representation built from the best descriptive outputs.

- `retrieval_tag_text`
  A compact lexical field composed from enrichment tag arrays without curated vocabulary mapping.

- `retrieval_document_text`
  A canonical retrieval document assembled from captions and tag-bearing text fields already produced by the pipeline.

- `embedding_text`
  The semantic text input used for embedding generation.

- `fts_document`
  A database-side weighted FTS expression built from multiple stored columns.

The key idea is:

- do not force one text field to satisfy every retrieval path
- store enough representation pieces so each read-path can use the right surface
- make retrieval execution choose the right surface deliberately rather than implicitly falling back to legacy `search_text`

### 7.2 Structured Retrieval Features

These fields remain structured and must be consumed explicitly later:

- `orientation`
- `has_human`
- `has_face`
- `is_abstract`
- `is_minimal`
- `is_dark`
- `wallpaper_score`
- `photography_reference_score`
- `dominant_colors`

No new semantic labels are introduced here. The design only requires these fields to participate more directly in later ranking.

### 7.3 Retrieval Consumption Contract

The retrieval service must consume the new representation bundle in production as follows:

- vector recall uses the persisted embedding built from `embedding_text`
- FTS recall searches a weighted document assembled from the new stored text fields
- candidate records returned from recall expose the richer representation and structured fields needed for rerank
- deterministic rerank uses those structured fields explicitly rather than relying on text-only substring checks
- traces and debug output show which representation surfaces contributed to each stage

---

## 8. Representation Compose Design

### 8.1 Inputs

The representation composer consumes:

- normalized source metadata
- translated `search_text`
- `ai_caption`
- `ai_short_caption`
- all tag arrays already produced by Phase 3 enrichment
- boolean flags and scalar scores already produced by enrichment/scoring

### 8.2 Responsibilities

The representation composer is responsible for:

- trimming and deduplicating repeated fragments
- preserving field boundaries during assembly
- promoting high-signal descriptive fields into semantic text
- promoting lexical tag fields into FTS-friendly text
- keeping composition logic generic and field-driven

### 8.3 Assembly Rules

The composer may use fixed assembly rules, but those rules must be structural rather than semantic.

Examples of allowed rules:

- `retrieval_caption_text` is assembled from `ai_short_caption + ai_caption`
- `retrieval_tag_text` is assembled from all non-empty tag arrays in a stable order
- `embedding_text` is assembled from captions plus selected tag-bearing text fields already produced by the pipeline
- duplicate fragments are removed
- empty fields are skipped

Examples of forbidden rules:

- if tag equals `moody`, rewrite to `cinematic dark emotional`
- if color looks blue, add `ocean vibe`
- maintain a hardcoded list of wallpaper adjectives in code

### 8.4 Why This Helps

This approach improves recall because the retrieval system will search against a richer compiled description of each photo:

- vector recall gets a denser semantic view
- FTS recall gets access to more lexical surfaces
- rerank gets more structured signals to compare against query understanding

The production benefit depends on both halves shipping together:

- indexing compiles better representations
- retrieval executes against those better representations

---

## 9. Schema Changes

The `photo_index` table should be expanded with new persisted representation fields in a follow-up append-only migration.

Required additions:

- `retrieval_caption_text: Text`
- `retrieval_tag_text: Text`
- `retrieval_document_text: Text`
- `embedding_text: Text`

These fields are persisted because:

- they are deterministic outputs of Phase 3
- they are useful for traceability and debugging
- they let retrieval inspect exactly what was indexed
- they avoid having retrieval rebuild write-path representations at read time

This design does not require storing a second embedding vector in the first optimization pass. One vector remains acceptable as long as its input text improves materially.

---

## 10. FTS Design

### 10.1 Move From Single-Column FTS to Weighted Multi-Field FTS

FTS should no longer search only `search_text`.

Instead, retrieval should search a weighted document assembled from:

- `search_text`
- `retrieval_caption_text`
- `retrieval_tag_text`
- `retrieval_document_text`

The weighting policy may be hardcoded structurally by field, because this is ranking policy rather than domain vocabulary.

Recommended weighting:

- highest weight for `search_text` and `ai_short_caption`-like lexical summaries
- medium weight for caption text
- medium or lower weight for tag bundles
- lowest weight for broader document text

The specific weight letters or rank formula belong to implementation details, but the design intent is fixed:

- concise lexical fields should influence precision more strongly
- broader assembled text should improve recall without overwhelming ranking

### 10.2 Production Retrieval Behavior

The retrieval repository should treat the weighted multi-field FTS document as the primary lexical recall surface for newly indexed data.

In production:

- FTS candidate generation should prefer the weighted multi-field expression over the legacy single-column expression
- retrieval traces should report the FTS query text and candidate counts under the new path
- the service should retain its existing dual-path failure isolation so lexical improvements do not weaken availability

### 10.3 No Semantic Expansion Tables

FTS improvement must come from better indexed document construction, not from manually expanded hardcoded synonym lists.

---

## 11. Embedding Design

### 11.1 Improve the Embedding Input Instead of Adding Semantic Hardcoding

The embedding input should switch from the current narrow composition to `embedding_text`, a richer representation assembled from:

- `ai_short_caption`
- `ai_caption`
- high-signal tag arrays
- use-case hints already produced by enrichment

### 11.2 Keep One Embedding in This Iteration

This design intentionally keeps one persisted embedding vector in the first pass.

That keeps scope bounded while still addressing the main quality issue: the embedding input text is too thin relative to available enrichment output.

If later evaluation shows need for separate lexical and semantic vectors, that should be a follow-up design.

### 11.3 Production Vector Retrieval Behavior

Production vector retrieval should remain operationally simple:

- keep one stored embedding vector
- improve recall quality by improving `embedding_text`
- keep the existing vector-path fallback isolation in place
- expose the richer embedding rewrite and candidate counts in traces for debugging and evaluation

---

## 12. Retrieval Consumption Changes

This is still primarily a Phase 3 design, but it requires specific downstream consumption updates so the new artifacts matter.

### 12.1 Repository Recall Changes

The retrieval repository should:

- run FTS against a weighted multi-field document instead of only `search_text`
- continue to use the persisted single embedding vector
- expose new representation fields to rerank where useful

### 12.2 Retrieval Service Changes

The retrieval service must be updated so the optimization lands in production behavior, not only in storage:

- retrieval response items should carry the new high-signal representation fields where needed for debugging and ranking inspection
- retrieval traces should indicate that the new representation bundle was used
- retrieval preparation output should continue to drive query understanding, but the execution layer should map that understanding onto the richer stored artifacts
- fallback behavior must remain stage-isolated: vector failure, FTS failure, and dual failure handling should continue to work exactly once the new read path ships

### 12.3 Rerank Changes

The deterministic reranker should consume more structured Phase 3 fields.

It should add explicit comparison logic for:

- `is_dark`
- `is_minimal`
- `has_face`
- `dominant_colors`
- tag overlap through stored tag arrays rather than only substring checks on text

This still avoids hardcoded vocabularies because the reranker is comparing query-time structured preferences against stored structured outputs, not mapping terms through a fixed semantic ontology and not generating new descriptive phrases in code.

### 12.4 Search Logging and Debug Changes

Because these optimizations are intended for production use, the retrieval stack should log enough detail to verify that the new path is actually active.

The existing search logging and trace surfaces should be extended to capture:

- whether the request used the richer representation bundle
- top candidate IDs from each recall path
- whether structured rerank features contributed materially
- which fallback path, if any, was used

This is not a new evaluation system. It is the minimum observability needed to validate production behavior.

---

## 13. Query-to-Index Alignment

This design intentionally shifts more work into the index.

The retrieval-preparation layer should stay responsible for:

- understanding the query
- extracting hard filters and soft preferences
- generating retrieval-friendly rewrites

But it should not be responsible for compensating for weak index representations.

The index should already expose:

- strong lexical surfaces
- strong semantic surfaces
- structured retrieval features

That division keeps later retrieval simpler and more accurate.

It also makes rollout safer:

- indexing improvements are deterministic and inspectable
- retrieval consumption remains localized to repository and ranking layers
- operational verification can compare old and new traces without redesigning the entire service

---

## 14. Validation Rules

Final validation for a completed indexed record should be expanded.

Required fields:

- `search_text`
- `ai_caption`
- `retrieval_caption_text`
- `retrieval_tag_text`
- `retrieval_document_text`
- `embedding_text`
- `embedding`

Validation should confirm:

- non-empty text after assembly
- deduplicated text does not collapse to blank
- persisted representation fields are internally consistent

The validation layer should still not impose semantic whitelists or curated vocabularies.

---

## 15. Migration and Reindexing

Existing rows may not have the new representation fields populated.

This design assumes the team can reindex from source data rather than trying to infer all new fields in-place from incomplete older rows.

Therefore:

- schema migration should add the new columns
- backfill may be limited or omitted if a full reindex is planned
- the operational rollout should treat reindex as the primary path to correctness

---

## 16. Testing Strategy

Testing should cover three layers:

### 16.1 Unit Tests

- representation composer assembles stable outputs from enrichment inputs
- empty and duplicate fragments are handled correctly
- validation rejects incomplete representation bundles

### 16.2 Integration Tests

- pipeline persists all new representation fields
- FTS retrieval improves candidate coverage by searching the weighted multi-field document
- embedding generation consumes `embedding_text`
- retrieval service returns results whose ordering changes appropriately when structured Phase 3 features are present

### 16.3 Retrieval Regression Tests

- dark/minimal/wallpaper queries retrieve items whose tags and flags support those requests
- negative people/face preferences are not lost when richer representations are introduced
- retrieval traces expose the new stored representation surfaces where helpful
- fallback behavior remains intact when either the vector path or the FTS path fails under the new production read path

### 16.4 Production Verification

Before considering rollout complete, the team should verify:

- new rows are being written with the full representation bundle
- retrieval logs and traces show the new read path in use
- candidate counts and ranking behavior remain stable under expected traffic shapes
- the system still degrades gracefully on vector-only or FTS-only execution

---

## 17. Risks

### 17.1 Overly Verbose Indexed Documents

If assembled representation text becomes too repetitive, both FTS precision and embedding quality can degrade.

Mitigation:

- deduplicate fragments
- keep stable field ordering
- keep compact fields separate from broad fields

### 17.2 Model Noise in Tag Arrays

Because no curated vocabulary is allowed, model-generated tags may drift in wording.

Mitigation:

- favor representation assembly that combines multiple fields instead of trusting any single tag array
- keep retrieval robust through weighted multi-field matching rather than exact one-field dependence

### 17.3 Scope Expansion Into Retrieval Redesign

This work should not become a full rewrite of Phase 4 retrieval.

Mitigation:

- keep vector infrastructure unchanged
- keep retrieval-preparation architecture unchanged
- only update recall and rerank enough to consume richer Phase 3 artifacts

### 17.4 Production Rollout Risk

Because retrieval behavior changes directly, production risk is not limited to indexing correctness.

Mitigation:

- preserve existing failure isolation between vector and FTS paths
- keep the first rollout focused on representation consumption rather than algorithm proliferation
- ensure traces and search logs expose enough detail to compare old and new behavior

---

## 18. Recommended Implementation Order

1. Add new persisted representation fields to `photo_index`.
2. Introduce a representation composer in the Phase 3 pipeline.
3. Expand final validation to require the new representation bundle.
4. Update embedding generation to use `embedding_text`.
5. Update repository FTS search to use weighted multi-field documents.
6. Update rerank to compare more structured Phase 3 outputs.
7. Update retrieval service traces and logging to prove the richer path is active in production.
8. Add retrieval regression tests covering the richer representations and fallback behavior.

---

## 19. Success Criteria

This design is successful when:

- every completed indexed photo persists a richer representation bundle
- retrieval no longer depends on `search_text` alone for lexical recall
- embedding generation consumes a denser semantic representation
- more of the existing Phase 3 enrichment output is actually used in recall and rerank
- production retrieval traces and logs make it obvious that the richer read path is active
- the implementation introduces no curated vocabulary tables and no code-level hardcoded semantic mappings

---

## 20. Summary

The recommended path is not to add manual vocabularies or query-time hacks.

The better path is to make Phase 3 compile each photo into stronger retrieval-facing artifacts:

- multiple stored text representations
- one stronger embedding input
- weighted multi-field FTS
- richer structured rerank features

This keeps the system generic, respects the no-hardcode constraint, and increases the chance that Phase 4 retrieval becomes more accurate because the index itself is more truthful and more usable.
