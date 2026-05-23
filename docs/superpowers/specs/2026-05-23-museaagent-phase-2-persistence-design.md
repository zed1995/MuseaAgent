# MuseaAgent Phase 2 Persistence Design

> Scope: Database foundation and persistence boundaries for Phase 2 only

---

## 1. Goal

Phase 2 establishes the persistence foundation that later retrieval, agent, chat, and evaluation phases can depend on without reworking storage boundaries.

This phase is not about implementing retrieval behavior. It is about locking down:

- the initial database schema contract
- the migration strategy
- the ORM model contract
- the repository contract
- the mapping boundary between persistence objects and application-facing objects

The outcome of Phase 2 should be a storage layer that is stable enough for later phases, while still avoiding premature schema commitments for uncertain product or model behavior.

---

## 2. Scope

Phase 2 covers:

- PostgreSQL as the primary database
- `pgvector` as the vector storage extension
- Alembic-based schema migration strategy
- first-generation schema for persistence foundation
- SQLAlchemy persistence model boundaries
- repository boundaries for core persistence use cases
- storage-to-domain mapping rules
- transaction and session ownership rules

Phase 2 does not cover:

- retrieval scoring logic
- query normalization behavior
- prompt design
- agent graph orchestration
- SSE or chat streaming behavior
- detailed ingestion enrichment logic
- full evaluation or feedback workflows
- client-facing API payload design beyond what persistence must support

---

## 3. Design Principles

### 3.1 Contract-First

Phase 2 uses a contract-first approach across three layers:

- storage schema contract
- ORM model contract
- repository contract

The goal is to avoid two failure modes:

- schema-first design that forces the rest of the application to think in table shapes
- repository-first design that hides important database constraints until too late

### 3.2 Index Table, Not Display Table

`photo_index` is a retrieval index table, not a display mirror of Unsplash metadata.

This means:

- the table stores retrieval fields only
- it does not store image card display fields for client rendering
- clients or later services may use the returned identifier to fetch live display details from Unsplash

### 3.3 Store Only Retrieval-Relevant Data

Unsplash fields are stored only if they are needed for one or more of the following:

- retrieval
- retrieval debugging
- index rebuilds
- ingestion status handling

Fields that exist only for display convenience are excluded from the Phase 2 index schema.

### 3.4 English Retrieval Text

`search_text` is English-only.

This is a hard design constraint:

- ingestion-time text preparation must translate and normalize retrieval text into English before writing `search_text`
- query-time retrieval must translate non-English user input into English before FTS and embedding retrieval
- PostgreSQL FTS operates against English retrieval text only

This avoids tying database search quality to Chinese tokenizer choices in Phase 2.

### 3.5 Embedding-First Semantics

Phase 2 does not pre-encode many semantic judgments into dedicated columns.

The following are intentionally excluded from the first-generation schema unless later phases prove they are stable and high-value hard filters:

- `has_human`
- `has_face`
- `is_abstract`
- `is_minimal`
- `is_dark`
- broad families of semantic tag bucket columns

The system should initially rely on:

- `embedding` for semantic recall
- `search_text` for keyword recall
- a very small set of stable structured filters

### 3.6 Single Generated Primary Key

All core tables use a single application-generated `BIGINT id`.

Phase 2 does not use:

- database auto-increment primary keys
- UUID dual-identifier strategy

The ID generator contract is:

- Snowflake-style generated ID
- generated in the application layer
- used consistently across primary keys and foreign keys

### 3.7 First-Generation Embedding Contract

Phase 2 defines `embedding` as a single vector column for the first selected embedding model.

Important constraint:

- the embedding dimension is not fixed in this design document
- the dimension is determined by the first implementation choice
- the schema is allowed to evolve later if the embedding model changes

Phase 2 explicitly does not attempt a multi-model embedding storage design.

---

## 4. Three-Layer Contract Boundaries

### 4.1 Storage Schema Contract

The storage schema contract defines:

- tables
- columns
- types
- defaults
- primary keys
- unique constraints
- foreign keys
- indexes
- extension dependencies

It does not define:

- API response models
- agent workflow state behavior
- retrieval ranking logic

### 4.2 ORM Model Contract

The ORM model contract exists only to represent persistence structure in SQLAlchemy.

It defines:

- table-to-model mapping
- database types mapped into Python-side persistence types
- timestamps and shared persistence mixins
- relationship mappings where needed for persistence access

It does not define:

- service-layer business semantics
- API response structure
- retrieval logic

ORM models are persistence objects only. They must not be treated as application-facing domain objects.

### 4.3 Repository Contract

Repositories define persistence capabilities for the application layer.

They define:

- supported read and write operations
- operation semantics
- transaction participation rules
- repository return types

They do not define:

- HTTP behavior
- retrieval ranking
- agent orchestration
- external API calls

Repositories should be use-case oriented rather than generic CRUD wrappers.

---

## 5. Phase 2 Table Set

Phase 2 includes the following tables:

- `photo_index`
- `conversations`
- `messages`
- `search_logs`

Phase 2 explicitly excludes:

- `photographer_profile`
- `feedback`

These are deferred because they are not required to establish the first persistence foundation.

---

## 6. Table Design

### 6.1 `photo_index`

#### Purpose

`photo_index` is the primary retrieval index table for photo search.

It exists to support:

- FTS candidate recall
- vector candidate recall
- minimal stable filtering
- indexing lifecycle management
- index debugging and rebuild support

It does not exist to store display-ready Unsplash card data.

#### Included Fields

- `id BIGINT PRIMARY KEY`
- `source TEXT NOT NULL DEFAULT 'unsplash'`
- `unsplash_photo_id TEXT NOT NULL UNIQUE`
- `unsplash_user_id TEXT`
- `orientation TEXT`
- `source_text TEXT`
- `search_text TEXT NOT NULL`
- `embedding VECTOR(<first-model-dimension>)`
- `status TEXT NOT NULL DEFAULT 'pending'`
- `last_error TEXT`
- `indexed_at TIMESTAMPTZ`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Field Notes

- `source_text` stores source retrieval text for debugging, rebuilds, and reprocessing. It does not participate directly in retrieval.
- `search_text` stores the English retrieval text used by FTS.
- `orientation` is retained as a stable structured filter because it is not a model-derived semantic judgment and is a likely high-value hard filter.
- `embedding` is nullable during pre-index or failed-index lifecycle states.
- `status` is a lifecycle field, not a retrieval signal.

#### Excluded Fields

The following are intentionally excluded from Phase 2:

- card display URLs
- width and height
- raw Unsplash display descriptions that are not part of retrieval text preparation
- semantic booleans such as `has_human`
- broad semantic tag bucket columns
- scoring columns such as `wallpaper_score`

#### Indexes and Constraints

- primary key on `id`
- unique constraint on `unsplash_photo_id`
- btree index on `unsplash_user_id`
- btree index on `orientation`
- GIN FTS index on English `search_text`
- vector index on `embedding`

#### Status Contract

The initial status vocabulary should remain intentionally small:

- `pending`
- `indexed`
- `failed`

Phase 2 does not need a more detailed processing state machine.

### 6.2 `conversations`

#### Purpose

`conversations` provides a stable conversation container for later multi-turn work without committing to advanced chat semantics in Phase 2.

#### Included Fields

- `id BIGINT PRIMARY KEY`
- `user_id TEXT`
- `title TEXT`
- `message_count INT NOT NULL DEFAULT 0`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Excluded Fields

- context snapshot blobs
- constraint inheritance state
- conversation mode state

Phase 2 stores only the basic conversation container.

### 6.3 `messages`

#### Purpose

`messages` stores ordered conversation messages and minimal structured payloads that later phases may consume.

#### Included Fields

- `id BIGINT PRIMARY KEY`
- `conv_id BIGINT NOT NULL REFERENCES conversations(id)`
- `role TEXT NOT NULL`
- `content TEXT NOT NULL`
- `structured_data JSONB`
- `metadata JSONB`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Excluded Fields

- token accounting
- model provider detail
- event-stream step payload storage

#### Indexes and Constraints

- primary key on `id`
- foreign key from `conv_id` to `conversations(id)`
- index on `conv_id`

### 6.4 `search_logs`

#### Purpose

`search_logs` stores coarse-grained retrieval debug and evaluation inputs without becoming a full agent trace store in Phase 2.

#### Included Fields

- `id BIGINT PRIMARY KEY`
- `request_id TEXT UNIQUE`
- `user_id TEXT`
- `query TEXT NOT NULL`
- `intent JSONB`
- `rewritten_queries JSONB`
- `filters JSONB`
- `retrieved_photo_ids JSONB`
- `reranked_photo_ids JSONB`
- `latency_ms INT`
- `result_count INT`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

#### Excluded Fields

- node-by-node graph traces
- detailed score breakdowns for every retrieval stage
- evaluation labels
- user feedback payloads

---

## 7. Database and Migration Standards

### 7.1 Database

Phase 2 targets PostgreSQL with:

- `pgvector` required

No other extension is required by default for Phase 2.

### 7.2 Key Strategy

All Phase 2 core tables use:

- `id BIGINT PRIMARY KEY`

ID generation rules:

- IDs are generated by the application layer
- IDs use a Snowflake-style generator contract
- database tables do not rely on auto-increment sequences for primary identity

### 7.3 Timestamp Strategy

All core tables use:

- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

Mutable tables also use:

- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

Lifecycle tables may also use domain-specific timestamps such as:

- `indexed_at`

### 7.4 JSONB Strategy

`JSONB` is allowed only where structure is intentionally flexible and not yet worth normalizing.

Phase 2 uses `JSONB` sparingly:

- `structured_data`
- `metadata`
- `intent`
- `rewritten_queries`
- `filters`
- `retrieved_photo_ids`
- `reranked_photo_ids`

The schema should not use `JSONB` as a substitute for stable, queryable core columns.

### 7.5 FTS Strategy

`search_text` is the only text field indexed for FTS in `photo_index`.

The contract is:

- FTS runs on English retrieval text
- non-English user inputs must be translated before search
- source-language text is not the FTS target

### 7.6 Vector Strategy

`embedding` is stored in a single vector column for the first-generation embedding model.

The contract is:

- dimension is implementation-defined in the first build
- the schema may need evolution if the embedding model changes later
- Phase 2 does not support multiple embedding models in parallel

### 7.7 Alembic Standards

Phase 2 migrations must follow these rules:

- use Alembic for schema versioning
- first migration must create required extensions, tables, indexes, and constraints
- migration files must be reviewed and adjusted manually
- autogeneration output is not trusted as final migration source
- historical migrations are append-only after merge

### 7.8 Delete Behavior

Phase 2 delete behavior should be conservative.

Recommended initial behavior:

- `messages.conv_id` should use standard referential integrity
- no broad cascade-delete behavior should be introduced unless a concrete use case requires it

This avoids accidentally encoding data-lifecycle assumptions too early.

---

## 8. Repository Contract

### 8.1 General Rules

Repositories must:

- expose use-case-oriented operations
- hide SQLAlchemy query construction from callers
- return repository records or DTOs, not ORM instances
- participate in caller-owned transaction boundaries

Repositories must not:

- expose ORM query objects
- perform hidden commits by default
- return HTTP-layer schemas
- depend on FastAPI or transport concerns

### 8.2 `PhotoIndexRepository`

#### Responsibilities

- get an index record by `id`
- get an index record by `unsplash_photo_id`
- create or update a single index entry
- create or update entries in bulk
- update lifecycle fields such as `status`, `last_error`, `indexed_at`

#### Non-Responsibilities

- rank final search results
- generate embeddings
- translate source text
- call Unsplash

#### Suggested Operation Shapes

- `get_by_id(id: int)`
- `get_by_unsplash_photo_id(unsplash_photo_id: str)`
- `upsert_index_entry(entry: PhotoIndexWriteModel)`
- `bulk_upsert_index_entries(entries: list[PhotoIndexWriteModel])`
- `mark_indexed(id: int, indexed_at: datetime)`
- `mark_failed(id: int, error_message: str)`

### 8.3 `ConversationRepository`

#### Responsibilities

- create a conversation
- get a conversation by `id`
- update title or counts
- verify conversation existence

#### Non-Responsibilities

- load full conversation messages
- compute derived multi-turn state

### 8.4 `MessageRepository`

#### Responsibilities

- create a message
- list messages for a conversation in order
- batch-load messages for a conversation

#### Non-Responsibilities

- derive conversation summary state
- own follow-up or refinement semantics

### 8.5 `SearchLogRepository`

#### Responsibilities

- create an initial search log
- read by `request_id`
- update retrieved/reranked ids and timing summary

#### Non-Responsibilities

- store full graph traces
- aggregate evaluation metrics

---

## 9. Mapping Contract

### 9.1 Persistence Objects vs Application-Facing Objects

Phase 2 requires a strict separation between:

- SQLAlchemy ORM persistence models
- repository-facing write models
- repository-facing read records or DTOs

ORM models must not leak into service, API, or agent layers.

### 9.2 Recommended Object Families

For persistence-heavy entities such as `photo_index`, the design should allow different object shapes for different responsibilities:

- `PhotoIndexOrmModel`
- `PhotoIndexWriteModel`
- `PhotoIndexRecord`

This avoids turning one persistence model into a pseudo-universal object that serves storage, API, and domain needs at once.

### 9.3 Mapping Ownership

Mapping between ORM rows and repository return types belongs inside the persistence layer.

Callers should not need to know:

- ORM field names
- lazy-loaded relationships
- session behavior

---

## 10. Session and Transaction Boundaries

Phase 2 should adopt explicit session ownership rules.

### 10.1 Session Ownership

- repositories receive a session or work inside a caller-owned unit of work
- repositories do not own process-global mutable session state

### 10.2 Commit Ownership

- repository methods do not commit implicitly by default
- commit and rollback are owned by the application service or unit-of-work boundary

This is required for later multi-table use cases.

### 10.3 Query Abstraction Rule

Repositories must not expose SQLAlchemy query objects or accept external query fragments as part of their public contract.

If callers need a new persistence operation, the repository contract should grow explicitly.

---

## 11. Risks and Evolution

### 11.1 Embedding Model Evolution

The first-generation single-column embedding approach is intentionally simple, but it creates future migration cost when the embedding model changes.

That tradeoff is accepted in Phase 2.

### 11.2 Translation Quality Dependency

Because `search_text` is English-only, retrieval quality depends directly on translation quality in both ingestion and query-time pathways.

This is a retrieval-layer risk, but the persistence design must acknowledge it.

### 11.3 Structured Filter Expansion

If later retrieval phases prove that certain constraints are stable and high-value hard filters, new structured columns may be added through follow-up migrations.

Phase 2 intentionally avoids guessing those columns too early.

### 11.4 Deferred Tables

`photographer_profile` and `feedback` remain valid future schema candidates, but they are intentionally excluded from Phase 2 to keep the persistence foundation narrowly focused.

---

## 12. Acceptance Criteria

Phase 2 persistence design is considered successful when:

- the first schema is clear enough to implement without redefining table purpose
- the migration strategy is explicit and reviewable
- repository boundaries are clear enough that later phases do not need direct SQL access
- ORM models are clearly separated from application-facing records
- later retrieval and chat work can build on this foundation without reworking identity or storage ownership
