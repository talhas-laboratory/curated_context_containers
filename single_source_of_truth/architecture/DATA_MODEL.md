# Data Model — Schemas & Contracts

**Owner:** Silent Architect  
**Last Updated:** 2026-02-01T12:15:00Z  
**Status:** 🟡 In Progress — Phase 2 modalities + container hierarchy captured, migrations pending

---

## Purpose

Codify every persistent structure (PostgreSQL, Qdrant, MinIO) plus invariants that guarantee deterministic retrieval. All downstream code must treat this file as the contract of truth.

---

## PostgreSQL 16 Schemas

Extensions required:
- `pg_trgm` (similarity + fuzzy search)
- `unaccent` (normalize text before FTS)
- `pgcrypto` or `uuid-ossp` for UUID generation

### Enum Types
```sql
CREATE TYPE container_state AS ENUM ('active','paused','archived');
CREATE TYPE job_kind AS ENUM ('ingest','refresh','export');
CREATE TYPE job_status AS ENUM ('queued','running','done','failed');
CREATE TYPE modality AS ENUM ('text','pdf','image','web');
```

### `containers`
Container registry + manifest cache.
```sql
CREATE TABLE containers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES containers(id) ON DELETE CASCADE,
    name TEXT NOT NULL UNIQUE CHECK (name ~ '^[a-z0-9_-]+$'),
    theme TEXT NOT NULL,
    description TEXT,
    modalities modality[] NOT NULL CHECK (array_length(modalities,1) > 0),
    embedder TEXT NOT NULL,
    embedder_version TEXT NOT NULL,
    dims INT NOT NULL CHECK (dims > 0),
    policy JSONB NOT NULL,          -- matches Policy schema below
    acl JSONB NOT NULL DEFAULT '{}',
    state container_state NOT NULL DEFAULT 'active',
    stats JSONB NOT NULL DEFAULT jsonb_build_object('document_count',0,'chunk_count',0,'size_mb',0),
    graph_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    graph_url TEXT,
    graph_schema JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_containers_state ON containers(state);
CREATE INDEX idx_containers_theme ON containers(theme);
CREATE INDEX idx_containers_parent ON containers(parent_id);
```

**Graph fields:** `graph_enabled` flags containers that participate in graph RAG; `graph_url` allows overriding the default Neo4j bolt URI; `graph_schema` can cache introspected labels/relationships for diagnostics/UI.

### `container_versions`
History of manifest revisions for auditing.
```sql
CREATE TABLE container_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID REFERENCES containers(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    manifest JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_container_versions_container ON container_versions(container_id);
```

### `documents`
One row per logical document/source.
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    uri TEXT,
    mime TEXT NOT NULL,
    hash TEXT NOT NULL,                        -- sha256 of original content
    title TEXT,
    size_bytes BIGINT,
    meta JSONB,
    state TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(container_id, hash)
);
CREATE INDEX idx_documents_container ON documents(container_id);
CREATE INDEX idx_documents_hash ON documents(hash);
```

### `chunks`
Atomic retrieval units (text spans, PDF pages, image embeddings, etc.).
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    modality modality NOT NULL,
    text TEXT,                                -- nullable for pure image chunks
    offsets INT4RANGE,                        -- token span when available
    tsrange TSRANGE,                          -- temporal bounds for AV/media
    provenance JSONB NOT NULL,                -- see schema below
    meta JSONB,
    embedding_version TEXT NOT NULL,
    dedup_of UUID,                            -- references chunks(id) when deduped
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE chunks ADD COLUMN tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(unaccent(text),'')), 'A')
) STORED;                                      -- Phase 1 uses english analyzer
CREATE INDEX idx_chunks_container ON chunks(container_id);
CREATE INDEX idx_chunks_doc ON chunks(doc_id);
CREATE INDEX idx_chunks_tsv ON chunks USING GIN(tsv);
CREATE INDEX idx_chunks_modality ON chunks(modality);
```

### `jobs`
Lightweight job queue for ingestion/refresh/export.
```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind job_kind NOT NULL,
    status job_status NOT NULL DEFAULT 'queued',
    container_id UUID REFERENCES containers(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,
    error TEXT,
    retries INT NOT NULL DEFAULT 0,
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_container ON jobs(container_id);
```

### `job_events`
Append-only log of job lifecycle.
```sql
CREATE TABLE job_events (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status job_status NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `embedding_cache`
Stores reusable embeddings keyed by content hash + modality + model version.
```sql
CREATE TABLE embedding_cache (
    cache_key TEXT PRIMARY KEY,                -- sha256(content) + ':' + model_version + ':' + modality
    modality modality NOT NULL,                -- text|pdf|image
    dims INT NOT NULL,
    vector BYTEA NOT NULL,                    -- stored as float32[] via extension or pgvector (phase 2)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_embedding_cache_last_used ON embedding_cache(last_used_at);
```

### `diagnostics`
Optional table for storing search traces (Phase 1 optional, on by default for testing).
```sql
CREATE TABLE diagnostics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Trigger Summary
- `containers.updated_at` auto-updated via trigger on row change
- `documents.stats` update trigger increments container stats (document_count, chunk_count)
- `chunks` insert trigger updates container/chunk counts + `tsv`
- `jobs` trigger enforces `running` heartbeat update every 60s else job considered abandoned and reset to `queued`

### Policy Schema (JSON)
```json
{
  "retention_days": "integer|null",
  "privacy": "local_only|exportable",
  "freshness_lambda": 0.02,
  "dedup_threshold": 0.92,
  "max_chunk_tokens": 600,
  "max_pdf_pages": 1000,
  "allowed_domains": ["example.com"],
  "diagnostics_enabled": true
}
```

### Provenance Schema (JSON)
```json
{
  "source": "url|file|manual",
  "ingested_at": "iso8601",
  "pipeline": "text|pdf|image|web",
  "handler_version": "git_sha or semver",
  "embedder": "nomic-embed-multimodal-7b",
  "embedder_version": "1.0.0",
  "page": 12,
  "section": "H1.2",
  "fetch_uri": "https://..."
}
```

### Embedding Cache + Dedup Policy

- `embedding_cache.cache_key = sha256(content) + ':' + embedder_version + ':' + modality`. Entries store vector bytes + timestamps; dims follow container manifest (1408 for multimodal).
- TTL (`LLC_EMBEDDING_CACHE_TTL_SECONDS`, default 7 days) governs eviction: stale rows are recomputed + replaced whenever accessed.
- Semantic dedup threshold (`LLC_SEMANTIC_DEDUP_THRESHOLD`, default 0.96 cosine; manifest override allowed per ADR-003) is applied per chunk:
  1. Worker embeds chunk text/image (after cache check)
  2. Search Qdrant collection `c_<container_uuid>_<modality>` for top-1 neighbor
  3. When score ≥ threshold, insert chunk with `dedup_of = <existing_chunk_id>` and skip Qdrant upsert
  4. `chunks.meta.semantic_dedup_score` stores the similarity for UI diagnostics
- Dedup logs annotated (`ingest_semantic_dedup`) so smoke/golden flows can assert policy behavior.

### Rerank Cache (Phase 2)
- In-memory cache keyed by sha256 of `provider_url + query + top_k_in + top_k_out + candidate_ids`.
- TTL controlled by `LLC_RERANK_CACHE_TTL_SECONDS` (default 300s); size via `LLC_RERANK_CACHE_SIZE` (default 256 entries).
- Stored value: ordering of chunk_ids + diagnostics hash. Persisted store deferred.

---

## Qdrant Collections

### Naming
`c_<container_uuid>_<modality>` — e.g. `c_6d1b..._text`. Names stored alongside container record for lookup.

### Vector Schema
```json
{
  "vectors": {
    "size": 1408,
    "distance": "Cosine"
  },
  "hnsw_config": { "m": 32, "ef_construct": 256 },
  "quantization_config": null,
  "optimizers_config": { "default_segment_number": 2 }
}
```

### Payload Fields
| Field | Type | Source |
|-------|------|--------|
| `chunk_id` | UUID | `chunks.id` |
| `doc_id` | UUID | `documents.id` |
| `container_id` | UUID | `containers.id` |
| `uri` | TEXT | canonical document URI + anchors |
| `modality` | TEXT | text/pdf/image |
| `score_debug` | JSON | stage scores (vector, bm25, rerank) for last query (optional) |
| `provenance` | JSON | copy of Postgres provenance |
| `meta` | JSON | doc metadata, tags, dedup_of |
| `freshness` | FLOAT | derived weight used for re-ranking |

### Consistency Rules
1. Every Qdrant payload row **must** have a matching `chunks` row; enforced via reconciliation job comparing IDs
2. Embedding dimension (`size`) matches `containers.dims`
3. Collections are created lazily per modality; dropping a container deletes associated collections
4. Snapshot/restore uses Qdrant built-in snapshot endpoint stored in `./snapshots/<container>`

---

## MinIO Object Model

- **Bucket:** `containers` (single bucket; folders per container)
- **Path Convention:**
```
s3://containers/{container_id}/{doc_id}/
  ├─ original/{filename}
  ├─ normalized/{slug}.txt            # text extraction result
  ├─ thumbs/{filename}_thumb.jpg
  └─ pdf_pages/{page_number}.png
```
- Objects tagged with metadata: `pipeline`, `mime`, `hash`, `embedder_version`
- Lifecycle (optional) removes `normalized/` artifacts older than `retention_days` when manifest allows

---

## Derived Views & Helpers

### `chunks_search_view`
Combines `chunks` + `documents` to simplify API queries.
```sql
CREATE VIEW chunks_search_view AS
SELECT
    c.id AS chunk_id,
    c.container_id,
    c.doc_id,
    c.modality,
    c.text,
    c.tsv,
    c.dedup_of,
    c.meta,
    c.provenance,
    d.title,
    d.uri,
    d.meta AS document_meta
FROM chunks c
JOIN documents d ON d.id = c.doc_id
WHERE c.state IS DISTINCT FROM 'deleted';
```

### Materialized Stats View
```sql
CREATE MATERIALIZED VIEW container_stats AS
SELECT
    container_id,
    COUNT(*) FILTER (WHERE modality = 'text') AS text_chunks,
    COUNT(*) FILTER (WHERE modality = 'image') AS image_chunks,
    COUNT(DISTINCT doc_id) AS documents,
    SUM(octet_length(coalesce(text,''))) / 1024 / 1024 AS approx_text_mb
FROM chunks
GROUP BY container_id;
```
Refresh via cron or after large ingests.

---

## Data Integrity Checks

- `SELECT COUNT(*) FROM chunks LEFT JOIN documents USING (doc_id) WHERE documents.id IS NULL` must be zero
- `SELECT COUNT(*) FROM qdrant_payload_diff` (custom reconciliation view) must be zero before releases
- Jobs older than `15 minutes` in `running` state get recycled to `queued`
- `embedding_cache` rows older than manifest `retention_days` get garbage-collected nightly

---

## Migration Strategy

- Tooling: Alembic scripts stored under `migrations/versions`
- Naming: `YYYYMMDDHHMM_<slug>.py`
- Always include downgrade path
- Use transactional DDL where possible; fallback to `--autocommit` for operations incompatible with transactions
- Pre-deployment checklist: apply migrations, run integrity checks, compute context hash

---

## Interfaces to Other Docs

- `SYSTEM.md` describes how services rely on these schemas
- `API_CONTRACTS.md` references fields surfaced to clients
- `design/COMPONENTS.md` uses metadata fields (title, provenance) to map UI
