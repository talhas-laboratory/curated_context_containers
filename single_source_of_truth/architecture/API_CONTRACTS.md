# API Contracts — MCP v1 Endpoints

**Owner:** Silent Architect  
**Last Updated:** 2026-02-07T16:08:09Z  
**Status:** 🟡 In Progress — Phase 2 image/crossmodal/rerank/refresh/export documented

---

## Protocol Overview

| Item | Value |
|------|-------|
| Base URL | `http://localhost:7801` |
| Version | `v1` |
| Transport | HTTP/JSON (REST) + MCP tool descriptors |
| Authentication | Bearer token (optional in local dev) |
| Content Type | `application/json` (UTF-8) |
| Timeout | 5 s default (override via `timeout_ms`) |

All responses share the envelope:
```json
{
  "version": "v1",
  "request_id": "uuid or client-supplied",
  "partial": false,
  "timings_ms": {"total": 83},
  "issues": []
}
```

`issues` is an array of machine-readable codes (see Error Codes). When `partial=true`, results may be truncated and remediation guidance must be included.

---

## Authentication

- Header: `Authorization: Bearer <TOKEN>`
- Token location: `LLC_MCP_TOKEN` env var (or `MCP_TOKEN` for compatibility)
- When auth disabled (local prototyping), header is ignored but warning logged
- Failed auth returns `401` with `error.code = "AUTH_FAILED"`

---

## Endpoint Catalog

### Core Endpoints

| Endpoint | HTTP | Description | MCP Tool |
|----------|------|-------------|----------|
| `/v1/containers/list` | POST | List containers with pagination/filtering | `containers.list` |
| `/v1/containers/describe` | POST | Retrieve detailed metadata for one container | `containers.describe` |
| `/v1/containers/add` | POST | Submit ingestion jobs for one or more sources | `containers.add` |
| `/v1/search` | POST | Execute semantic/hybrid/crossmodal/graph search | `containers.search` |
| `/v1/containers/graph_upsert` | POST | Upsert graph nodes/edges for a container | `containers.graph_upsert` |
| `/v1/containers/graph_search` | POST | Graph/NL→Cypher search over container graph | `containers.graph_search` |
| `/v1/containers/graph_schema` | GET | Retrieve graph labels/relationship schema | `containers.graph_schema` |
| `/v1/jobs/status` | POST | Check status of ingestion jobs | `jobs.status` |
| `/v1/documents/list` | POST | List embedded documents for a container | `documents.list` |
| `/v1/documents/delete` | POST | Remove document + chunks from a container | `documents.delete` |
| `/health` | GET | Liveness/readiness checks | — |
| `/ready` | GET | Readiness (503 when any dependency is down) + `migrations` report | — |
| `/v1/system/status` | GET | Status (200 always): dependency checks + errors + `migrations` report (for UI/agents) | — |
| `/metrics` | GET | Prometheus scrape | — |

### Agent Access Endpoints (NEW)

| Endpoint | HTTP | Description | MCP Tool |
|----------|------|-------------|----------|
| `/v1/containers/create` | POST | Create a new container | `containers.create` |
| `/v1/containers/{id}/update` | PATCH | Update container metadata | `containers.update` |
| `/v1/containers/{id}` | DELETE | Archive or delete container | `containers.delete` |
| `/v1/collaboration/link` | POST | Link two containers with relationship | `collaboration.link` |
| `/v1/collaboration/containers/{id}/links` | GET | Get links for a container | — |
| `/v1/collaboration/subscribe` | POST | Subscribe to container updates | `collaboration.subscribe` |
| `/v1/collaboration/containers/{id}/subscriptions` | GET | Get container subscriptions | — |

### Phase 2 Endpoints

| Endpoint | HTTP | Description | MCP Tool |
|----------|------|-------------|----------|
| `/v1/admin/refresh` | POST | Trigger re-embed jobs | `admin.refresh` |
| `/v1/admin/export` | POST | Build/export container snapshot | `containers.export` |
| `/v1/containers/recommend` | POST | Recommend containers based on mission | `containers.recommend` |

All POST/PATCH endpoints accept JSON payload; GET endpoints return JSON; DELETE returns JSON confirmation.

**Hierarchy Note:** `containers.create` accepts optional `parent_id` (uuid or slug). When provided, the new container inherits the parent’s `policy` field.

---

## 1. `containers.list`

**Route:** `POST /v1/containers/list`  
**Purpose:** Enumerate containers for UI/client bootstrapping.

**Request Schema:**
```json
{
  "state": "active|paused|archived|all",
  "limit": 50,
  "offset": 0,
  "search": "optional substring",
  "parent_id": "optional parent container (uuid or slug)",
  "include_stats": true
}
```
Defaults: `state="active"`, `limit=25`, `offset=0`, `include_stats=false`.

**Response Payload:**
```json
{
  "containers": [
    {
      "id": "f2a...",
      "parent_id": "a1b... (null for top-level)",
      "name": "expressionist-art",
      "theme": "German Expressionism",
      "modalities": ["text","image"],
      "state": "active",
      "stats": {
        "document_count": 142,
        "chunk_count": 1834,
        "size_mb": 234.5,
        "last_ingest": "2025-11-08T23:50:00Z"
      },
      "created_at": "2025-11-01T12:00:00Z",
      "updated_at": "2025-11-08T23:50:00Z"
    }
  ],
  "total": 5
}
```

**Validation Rules:**
- `limit` ≤ 100
- `offset` ≥ 0
- `search` trimmed, lowercased

**Issues:**
- `NO_RESULTS` when query matches nothing (empty `containers` array still allowed)

---

## 2. `containers.describe`

**Route:** `POST /v1/containers/describe`  
**Purpose:** Retrieve manifest + stats + policies for a single container.

**Request Schema:**
```json
{
  "container": "uuid or slug"
}
```
If slug provided, server resolves to canonical ID.

**Response Payload:**
```json
{
  "container": {
    "id": "f2a...",
    "parent_id": "a1b... (null for top-level)",
    "name": "expressionist-art",
    "theme": "German Expressionist paintings",
    "description": "...",
    "modalities": ["text","image"],
    "embedder": "nomic-embed-multimodal-7b",
    "embedder_version": "1.0.0",
    "dims": 1408,
    "policy": {...},
    "manifest_version": "2025-11-09-001",
    "stats": {
      "documents": 142,
      "chunks": 1834,
      "text_chunks": 1800,
      "image_chunks": 34,
      "size_mb": 234.5,
      "last_ingest": "2025-11-08T23:50:00Z"
    },
    "observability": {
      "diagnostics_enabled": true,
      "freshness_lambda": 0.02
    },
    "created_at": "...",
    "updated_at": "..."
  }
}
```

**Issues:**
- `CONTAINER_NOT_FOUND` when lookup fails (404)

---

## 3. `containers.add`

**Route:** `POST /v1/containers/add`  
**Purpose:** Register ingestion jobs for URIs or uploaded files.

**Request Schema:**
```json
{
  "container": "uuid or slug",
  "sources": [
    {
      "uri": "https://example.com/essay.pdf",
      "title": "optional override",
      "mime": "application/pdf",
      "modality": "pdf",
      "meta": {"author": "...", "tags": ["color"] }
    }
  ],
  "mode": "async|blocking",
  "timeout_ms": 5000
}
```

**Response Payload (async default):**
```json
{
  "jobs": [
    {
      "job_id": "9cb...",
      "source_uri": "https://example.com/essay.pdf",
      "status": "queued",
      "submitted_at": "2025-11-09T01:20:00Z"
    }
  ]
}
```

**Blocking Mode:** Waits until job transitions out of `running` or `timeout_ms` reached, returning summary with `chunks_created`, `issues`.

**Validation Rules:**
- Each source must specify either `uri` or `file_token` (future local upload reference)
- `modality` must be allowed by container manifest
- Duplicate hashes short-circuit to cache path, returning `issues=["DUPLICATE_SOURCE"]`

**Issues:**
- `INVALID_PARAMS`, `CONTAINER_NOT_FOUND`, `BLOCKED_MODALITY`, `RATE_LIMIT`, `INGEST_FAIL`

---

## 4. `containers.search`

**Route:** `POST /v1/search`  
**Purpose:** Execute semantic or hybrid retrieval over one or more containers.

**Request Schema:**
```json
{
  "query": "expressionist use of color",
  "query_image_base64": "…",         // optional; when present, mode auto-promotes to crossmodal
  "container_ids": ["expressionist-art"],
  "mode": "hybrid",
  "rerank": false,
  "k": 10,
  "diagnostics": true,
  "graph": {
    "max_hops": 2,
    "neighbor_k": 10
  },
  "filters": {
    "modality": ["text","image"],
    "metadata": {"period": ["modernism"]}
  },
  "timeout_ms": 5000
}
```
`query_image_base64` enables crossmodal search; when only image is provided, rerank is skipped by design.

**Response Payload:**
```json
{
  "query": "expressionist use of color",
  "containers": ["expressionist-art"],
  "mode": "hybrid",
  "results": [
    {
      "chunk_id": "...",
      "doc_id": "...",
      "container_id": "...",
      "container_name": "expressionist-art",
      "title": "Kandinsky — Concerning the Spiritual in Art",
      "snippet": "…use of saturated IKB hues…",
      "uri": "https://example.com/doc.pdf#page=12",
      "score": 0.87,
      "stage_scores": {"vector": 0.74, "bm25": 0.65, "fusion_rank": 1},
      "provenance": {
        "source": "url",
        "ingested_at": "2025-11-08T18:00:00Z",
        "modality": "text"
      },
      "meta": {
        "author": "Author Name",
        "tags": ["expressionism"]
      }
    }
  ],
  "total_hits": 47,
  "returned": 10,
  "graph_context": {
    "nodes": [],
    "edges": [],
    "snippets": []
  },
  "diagnostics": {
    "embed_ms": 45,
    "vector_ms": 23,
    "bm25_ms": 12,
    "fusion_ms": 5,
    "rerank_ms": 0,
    "applied_filters": ["modality:text"],
    "container_status": {
      "expressionist-art": "healthy"
    }
  }
}
```

**Validation Rules:**
- `k` 1..50
- All requested containers must exist and be `state != 'archived'`
- When a container has descendants, the search set is expanded to include subcontainers
- When `mode=bm25`, query embedding is skipped but `issues` notes `VECTOR_SKIPPED`
- When `diagnostics=false`, diagnostics field omitted
 - `mode` also accepts `graph` and `hybrid_graph`; `graph` requires text query; `graph.max_hops` 1..3.

**Issues:**
- `NO_HITS` when zero results (HTTP 200, `issues` contains remediation tips)
- `TIMEOUT` when 5s limit exceeded → `partial=true`, results truncated
- `VECTOR_DOWN` or `BM25_DOWN` when respective subsystem unhealthy

---

## 5. `containers.delete`

**Route:** `DELETE /v1/containers/{id}`  
**Purpose:** Archive a container (soft delete) or permanently remove it and associated data.

**Query Params:**
```
permanent=true|false   # default false
```

**Response Payload:**
```json
{
  "version": "v1",
  "request_id": "uuid",
  "success": true,
  "container_id": "f2a...",
  "message": "Container archived successfully",
  "timings_ms": {},
  "issues": []
}
```

**Validation Rules:**
- `id` must resolve to an existing container (UUID or slug)
- `permanent=false` archives the container (state=`archived`) and its descendants
- `permanent=true` removes container metadata, vectors, and blobs for the container and its descendants (best-effort cleanup)

**Issues:**
- `CONTAINER_NOT_FOUND` if container lookup fails

---

## 6. `documents.list`

**Route:** `POST /v1/documents/list`  
**Purpose:** Enumerate embedded documents (and chunk counts) for a container so clients can inspect current state.

**Request Schema:**
```json
{
  "container": "uuid or slug",
  "limit": 25,
  "offset": 0,
  "search": "optional substring matched against title or uri"
}
```

**Response Payload:**
```json
{
  "container_id": "f2a...",
  "documents": [
    {
      "id": "2c1...",
      "uri": "https://example.com/doc.pdf",
      "title": "Doc title",
      "mime": "application/pdf",
      "hash": "sha256",
      "state": "active",
      "chunk_count": 128,
      "meta": {"tags": ["expressionism"]},
      "created_at": "2025-11-08T18:00:00Z",
      "updated_at": "2025-11-08T18:00:00Z"
    }
  ],
  "total": 42,
  "timings_ms": {"db_query": 12}
}
```

**Validation Rules:**
- `limit` 1..200
- `offset` ≥ 0
- `search` optional; matched case-insensitively

**Issues:**
- `CONTAINER_NOT_FOUND` if container lookup fails

---

## 7. `documents.delete`

**Route:** `POST /v1/documents/delete`  
**Purpose:** Remove a specific document, its chunks, and associated vectors/blobs from a container.

**Request Schema:**
```json
{
  "container": "uuid or slug",
  "document_id": "uuid"
}
```

**Response Payload:**
```json
{
  "document_id": "2c1...",
  "deleted": true,
  "timings_ms": {"db_query": 18},
  "issues": []
}
```

**Validation Rules:**
- `document_id` must be a valid UUID
- Container must exist and own the requested document

**Issues:**
- `CONTAINER_NOT_FOUND` if container missing
- `DOCUMENT_NOT_FOUND` if document does not belong to container
- `INVALID_DOCUMENT_ID` if UUID parsing fails

---

## 8. `admin.refresh` (Phase 2 Stub)

**Route:** `POST /v1/admin/refresh`

**Purpose:** Schedule re-embedding jobs when manifest or embedder changes.

**Request:**
```json
{
  "container": "uuid or slug",
  "strategy": "in_place|shadow",
  "embedder_version": "1.1.0"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "timings_ms": {"db_query": 4},
  "issues": []
}
```

---

## 9. `admin.export` (Phase 2)

**Route:** `POST /v1/admin/export`

**Purpose:** Generate snapshot job for container metadata + vectors + blobs (MinIO tar/zip).

**Request:**
```json
{
  "container": "uuid or slug",
  "format": "tar",
  "include_vectors": true,
  "include_blobs": true
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "timings_ms": {"db_query": 4},
  "issues": []
}
```

---

## 9. `containers.graph_upsert`

**Route:** `POST /v1/containers/graph_upsert`

**Purpose:** Upsert graph nodes/edges for a container (merge or replace batch).

**Request:**
```json
{
  "container": "uuid or slug",
  "mode": "merge",
  "nodes": [
    {"id": "Person:1", "label": "Alice", "type": "Person", "summary": "Engineer", "source_chunk_ids": ["chunk_1"] }
  ],
  "edges": [
    {"source": "Person:1", "target": "Project:42", "type": "WORKS_ON", "source_chunk_ids": ["chunk_1"]}
  ],
  "diagnostics": false
}
```

**Response:**
```json
{
  "request_id": "...",
  "inserted_nodes": 1,
  "inserted_edges": 1,
  "updated_nodes": 0,
  "updated_edges": 0,
  "timings_ms": {"graph_ms": 12},
  "issues": []
}
```

**Issues:** `CONTAINER_NOT_FOUND`, `GRAPH_DISABLED`, `INVALID_PARAMS` (bad chunk IDs / limits), `GRAPH_DISABLED`.

---

## 10. `containers.graph_search`

**Route:** `POST /v1/containers/graph_search`

**Purpose:** Run graph/NL→Cypher search for a container graph; optional raw Cypher via `mode="cypher"` if enabled.

**Request:**
```json
{
  "container": "uuid or slug",
  "query": "decisions about GraphOS",
  "mode": "nl",
  "max_hops": 2,
  "k": 20,
  "diagnostics": true
}
```

**Response:**
```json
{
  "request_id": "...",
  "nodes": [],
  "edges": [],
  "snippets": [],
  "diagnostics": {"mode": "nl", "graph_hits": 0},
  "timings_ms": {"graph_ms": 0},
  "issues": []
}
```

**Issues:** `CONTAINER_NOT_FOUND`, `GRAPH_DISABLED`, `GRAPH_CYPHER_DISABLED`, `GRAPH_QUERY_INVALID`, `NO_HITS`, `TIMEOUT`, `INVALID_PARAMS`, `VECTOR_DOWN`.

---

## 11. `containers.graph_schema`

**Route:** `GET /v1/containers/graph_schema?container=<id_or_slug>`

**Purpose:** Return graph labels/relationship types + cached schema info.

**Response:**
```json
{
  "request_id": "...",
  "schema": {"node_labels": [], "edge_types": [], "cached": {}},
  "diagnostics": {"node_count": 0, "edge_count": 0},
  "issues": []
}
```

---

## Error Codes & Remediation

| Code | Meaning | Suggested remediation |
|------|---------|-----------------------|
| `AUTH_FAILED` | Missing/invalid token | Provide Bearer token via `Authorization` header |
| `CONTAINER_NOT_FOUND` | ID/slug invalid | Call `containers.list` to discover names |
| `INVALID_PARAMS` | Schema validation failure | Inspect `error.details.field_errors` |
| `BLOCKED_MODALITY` | Manifest disallows requested modality | Update manifest or choose allowed modality |
| `RATE_LIMIT` | Too many requests | Backoff with jitter and retry |
| `TIMEOUT` | Request exceeded timeout | Lower `k`, disable `diagnostics`, or try BM25-only |
| `NO_HITS` | Query returned nothing | Provide hints (broaden query, check filters) |
| `INGEST_FAIL` | Worker raised error | Inspect `jobs/<id>` via CLI or UI |
| `VECTOR_DOWN` | Qdrant unreachable | Retry once healthy; system falls back to BM25 |
| `BM25_DOWN` | Postgres FTS unavailable | Use `mode=semantic` temporarily |
| `DOCUMENT_NOT_FOUND` | Document missing from container | Refresh document list; ensure IDs accurate |
| `INVALID_DOCUMENT_ID` | Document id failed validation | Pass UUID from `documents.list` |
| `NOT_IMPLEMENTED` | Endpoint reserved for future phase | N/A |
| `RERANK_TIMEOUT` | Rerank provider exceeded budget | Use baseline hybrid results |
| `RERANK_SKIPPED_NO_TEXT` | Image-only crossmodal search skips rerank | Add text query to enable rerank |

**Error Response:**
```json
{
  "version": "v1",
  "request_id": "...",
  "error": {
    "code": "INVALID_PARAMS",
    "message": "mode must be one of semantic|hybrid|bm25",
    "remediation": "Update request payload",
    "details": {"field": "mode"}
  }
}
```

---

## Diagnostics Contract

When `diagnostics=true`, responses must include:
- `stage_scores` per result (vector, bm25, rerank, freshness)
- `timings_ms` aggregated per pipeline stage
- `container_status` map (`healthy|degraded|offline`)
- `issues` array capturing suppressed warnings (e.g., fallback to cached embedding, rerank skipped)
- Prometheus metrics: `llc_search_requests_total{container,mode,status}` (status=`success` when no issues, `partial` when latency budget hit, otherwise `error`); `llc_search_results_returned{mode}` and `llc_search_stage_latency_seconds{stage}` mirror returned count and stage timings.

Structured logs store the same diagnostics payload hashed as `diagnostics_hash` to keep logs small; full payload optionally stored in `diagnostics` table for debugging.

---

## MCP Tool Descriptors

Each endpoint is mirrored as an MCP tool descriptor served at `/mcp/manifest.json`. Example entry:
```json
{
  "name": "containers.search",
  "description": "Hybrid search over themed containers",
  "input_schema": {
    "$schema": "https://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["query"],
    "properties": {
      "query": {"type": "string"},
      "container_ids": {"type": "array", "items": {"type": "string"}},
      "mode": {"type": "string", "enum": ["semantic","hybrid","bm25"]}
    }
  }
}
```
Clients such as Claude Desktop read this manifest to know available tools.

---

## Rate Limiting

- Default bucket: 60 requests/min per token
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- When exceeded, server returns `429` with `Retry-After` seconds; `issues` includes `RATE_LIMIT`

---

## Pagination Strategy

- `containers.list`: offset/limit pattern
- `containers.search`: no pagination in Phase 1 (k ≤ 50); future streaming left open
- `containers.add`: returns array of job IDs; job polling occurs via CLI/worker logs (Phase 2 may add `/jobs/status`)

---

## Versioning & Compatibility

- `version` field stays `v1` throughout Phase 1–2. Breaking changes require `v2` path + manifest update.
- Additive fields allowed without version bump; clients instructed to ignore unknown fields.
- MCP manifest includes `version` metadata and `hash` for integrity checks.

---

## References

- `SYSTEM.md` for architecture context
- `DATA_MODEL.md` for schema references surfaced via API
- `design/COMPONENTS.md` for frontend mapping of response fields
