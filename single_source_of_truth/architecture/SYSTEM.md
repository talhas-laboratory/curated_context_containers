# System Architecture — Local Latent Containers

**Owner:** Silent Architect  
**Last Updated:** 2025-11-09T01:30:00Z  
**Status:** 🟡 In Progress — Baseline architecture defined, awaiting implementation

---

## Executive Summary

Local Latent Containers is a local-first retrieval system that exposes a deterministic MCP v1 surface from a FastAPI service backed by Qdrant (vectors), PostgreSQL (registry + BM25), MinIO (blobs) and a lightweight worker pool that performs ingestion pipelines. Everything runs under Docker Compose on a single Apple Silicon machine. Contracts are defined first (this document + `DATA_MODEL.md` + `API_CONTRACTS.md`) before any code is written.

---

## Logical Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       MCP Clients (agents)                       │
│   Claude Desktop · Cursor MCP · Local CLI · Playwright harness   │
└──────────────┬───────────────────────────────────────────────────┘
               │ HTTP/JSON (MCP v1 tools)
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI MCP Server                        │
│ ┌────────────┬───────────────┬─────────────────────────────────┐ │
│ │ API Layer  │  Auth / ACL   │ Diagnostics & Observability     │ │
│ └────┬───────┴──────┬────────┴────────────┬────────────────────┘ │
│      │              │                     │                      │
│ ┌────▼──────────────▼─────────────┐ ┌──────▼───────────────────┐ │
│ │        Service Layer           │ │    MCP Tool Descriptors  │ │
│ │ Search · Ingest · Manifest ·   │ │     (schema + routing)   │ │
│ │ Health · Admin                 │ │                          │ │
│ └────┬──────────────┬────────────┘ └────────────┬──────────────┘ │
│      │              │                           │                │
│ ┌────▼──────────────▼────────────┐ ┌────────────▼───────────────┐ │
│ │         Adapter Layer          │ │ Background Job Dispatcher  │ │
│ │ Qdrant · Postgres · MinIO ·    │ │ (enqueue ingestion jobs)   │ │
│ │ Nomic API · Caching            │ │                           │ │
│ └────┬──────────────┬────────────┘ └────────────┬───────────────┘ │
└──────┼──────────────┴───────────────────────────┴────────────────┘
       │                                          │
       │ gRPC/HTTP                                │ Postgres job queue polling
       ▼                                          ▼
┌────────────┐  ┌──────────────┐  ┌──────────────┐   ┌───────────────────────┐
│  Qdrant    │  │  PostgreSQL  │  │    MinIO     │   │  Worker Pool (RQ-lite)│
│ collections│  │ registry+FTS │  │  object store│   │ pipelines/text/pdf/etc │
└────────────┘  └──────────────┘  └──────────────┘   └───────────────────────┘
```

---

## Component Responsibilities

### MCP Clients
- Consume MCP tool descriptions exposed by the server (list, describe, add, search, refresh, export)
- Provide `request_id`, `diagnostics` preference, and authentication token
- Must handle partial responses and remediation hints

### FastAPI MCP Server
- Hosts REST endpoints and MCP tool descriptors under `/v1` and `/mcp`
- Performs request validation (Pydantic v2) and envelope construction
- Resolves manifests/policies from PostgreSQL before delegating to services
- Emits structured logs + Prometheus metrics per request

### Service Layer
- **SearchService**: orchestrates query embedding, vector/BM25 search, reciprocal rank fusion, optional rerank, and dedup/freshness heuristics
- **IngestService**: validates ingestion requests, creates `jobs` records, and hands work to the worker pool
- **ManifestService**: CRUD for containers and cached manifest views, ensures policy compatibility with adapters
- **DiagnosticsService**: surfaces timings, stage counts, container health from adapters
- **AdminService**: handles refresh/export orchestration in later phases

### Adapter Layer
- **PostgresAdapter**: typed queries for containers/documents/chunks/jobs, manages FTS indexes, handles advisory locks for job claiming
- **QdrantAdapter**: manages per-container collections (text/image), schema verification, batched upserts, and search parameter tuning
- **MinIOAdapter**: uploads original files, thumbnails, and PDF page renders following the canonical path scheme
- **EmbeddingAdapter**: HTTPX client for nomic-embed-multimodal-7b with request dedup + caching layer (sha256+model key)
- **CacheAdapter (optional)**: local sqlite/redis for embedding cache metadata (Phase 1 uses Postgres table)

### Worker Pool
- Runs ingestion pipelines (`workers/pipelines/{text,pdf,image,web}.py`)
- Polls the Postgres `jobs` table using `FOR UPDATE SKIP LOCKED`
- Processes fetch → extract → chunk → embed → persist steps
- Reports metrics (job throughput, failures) and writes job status updates
- Implements exponential backoff retries and DLQ semantics (status `failed` + payload snapshot)

### Data Stores
- **PostgreSQL 16**: canonical registry, metadata, BM25 index, job queue, embedding cache
- **Qdrant 1.11**: vector embeddings per container + modality, payload mirrors chunk metadata
- **Neo4j**: graph store for graph RAG nodes/edges (Cypher over bolt)
- **MinIO**: blob storage for originals, renders, thumbnails
- **Local disk volumes**: persistent storage bound to each container for durability across restarts

### External Services
- **Nomic API**: synchronous embedding calls (text + image); only external dependency besides optional rerank provider
- **Optional Rerank API**: reserved for Phase 2 (Cohere/Jina/Local cross-encoder)

---

## Operational Flows

### 1. Ingestion Flow (text/web/pdf/image)
1. Client calls `containers.add` with container reference + sources
2. IngestService validates modalities vs container manifest, normalizes URIs, stores metadata stub
3. A `jobs` row is created per source with payload (container_id, modality, fetch config)
4. Worker polls job → fetches source → extracts modality-specific payload
5. Worker splits into chunks (semantic-first, fallback to fixed-size). Each chunk gets provenance + metadata
6. Worker checks `embedding_cache` (sha256+model). Cache hit reuses embedding; miss calls Nomic API
7. Insert/Upsert into Postgres (`documents`, `chunks`, `tsv`), store blobs in MinIO, and upsert vectors into Qdrant collection `c_<container>_<modality>`
8. Worker updates job status + metrics; IngestService surfaces progress via `jobs` table for UI/CLI polling

### 2. Search Flow (semantic/hybrid default)
1. Client invokes `containers.search` with query text/image, target containers, mode, rerank toggle, diagnostics flag
2. SearchService fetches manifests + container settings, builds query context (freshness lambda, dedup) from Postgres
3. Embed query via Nomic adapter (cached by query hash where allowed)
4. Parallel fan-out: Qdrant vector search per container/modality (k=100) and PostgreSQL BM25 search (k=100)
5. Fuse candidates using Reciprocal Rank Fusion (weight vector_tier=0.5, bm25=0.5 by default)
6. Optional rerank (Phase 2) reduces to k=10; Phase 1 returns fused ranking directly
7. Apply dedup (cosine ≥0.92) and freshness boost (manifest lambda). Compose snippets using stored `chunks.text`
8. DiagnosticsService aggregates stage timings, hit counts, and container statuses. Response returns consistent envelope

### 3. Refresh Flow (Phase 2)
- `admin.refresh` enqueues jobs to re-embed containers when manifest/embedding version changes
- Workers reprocess using the latest embedder and perform snapshot + atomic swap once new vectors ready

### 4. Export Flow (Phase 2)
- `containers.export` triggers creation of tarball manifest (metadata + vectors + blobs) stored in MinIO and optionally streamed to client

---

## Deployment Topology

| Service | Container | Ports | Resources | Notes |
|---------|-----------|-------|-----------|-------|
| FastAPI MCP | `mcp` | `7801/tcp` | 1 CPU / 1 GiB | Runs uvicorn + Prometheus exporter |
| Worker Pool | `workers` | `9105/metrics` | 2 CPU / 3 GiB | Horizontal scale by adding replicas + Prom exporter |
| PostgreSQL | `postgres` | `5432/tcp` | 1.5 CPU / 2 GiB | Extensions: `pg_trgm`, `unaccent` |
| Qdrant | `qdrant` | `6333/http`, `6334/grpc` | 2 CPU / 4 GiB | Payload on disk |
| MinIO | `minio` | `9000/http`, `9001/console` | 1 CPU / 1 GiB | Bucket `containers` |
| Optional Redis | `cache` (future) | `6379/tcp` | 0.5 CPU / 0.5 GiB | For embedding cache acceleration |

**Networking:** Private Docker network (`latent-net`). Only MCP server exposes localhost port 7801. Other services accessible via internal DNS names (`postgres`, `qdrant`, `minio`).

**Secrets:** Provided via `.env` mounted into containers. Minimal set (database DSN, MinIO keys, MCP token, Nomic API key). Secrets never written to logs.

**Volumes:**
- `pg_data`, `qdrant_data`, `minio_data`, `worker_cache`
- Local `./manifests` bind-mounted for manifest editing

---

## Service Level Objectives & Budgets

| Dimension | Target | Enforcement |
|-----------|--------|-------------|
| Search latency | P95 < 900 ms, P50 < 400 ms | Logged per request; failing windows trigger diagnostics task |
| Ingestion throughput | 50k tokens/min sustained | Worker metrics + job lag alarms |
| Quality | nDCG@10 ≥ 0.75 (per container golden set) | Evaluated after ingest/before cutover |
| Reliability | Error rate < 1% / 1000 requests | Observed via Prometheus counter ratios |
| Index drift | Postgres↔Qdrant delta < 5 s | Reconciliation job monitors `updated_at` deltas |

---

## Observability Plan

**Metrics (Prometheus names):**
- `llc_search_requests_total{container,mode,status}` — increments per `/v1/search`
- `llc_search_stage_latency_seconds{stage}` — histograms for bm25/vector stages
- `llc_search_total_latency_seconds` — overall search latency SLO gate
- `llc_search_results_returned{mode}` — histogram for result counts
- `llc_ingest_duration_seconds{modality}` — worker ingest time
- `llc_embedding_cache_hits_total{modality}` / `llc_embedding_cache_misses_total{modality}` — cache health
- `llc_semantic_dedup_chunks_total{modality}` — semantic dedup drops
- `llc_qdrant_upserts_total{modality}` — actual vectors written

**Logs:** JSON Lines via `python-json-logger`. Fields: `timestamp`, `level`, `request_id`, `endpoint`, `status`, `latency_ms`, `issues`, `diagnostics_hash`, `agent`. Workers log `job_id`, `kind`, `status`, `duration_ms`, `error_code`.

**Tracing:** Optional OpenTelemetry spans around embed/search/rerank; exported to stdout or OTLP collector when enabled. Trace IDs propagate via `X-Request-ID` header.

**Health Checks:**
- `/health/ready`: verifies DB + Qdrant connections
- `/metrics`: Prometheus scrape endpoint
- Docker `HEALTHCHECK` for each service (psql ping, qdrant HTTP ping, MinIO mc admin)

---

## Security & Access Control

- **Auth:** Bearer token validated per request (see `API_CONTRACTS.md`). Token stored in env or a secrets manager.
- **Transport:** Localhost only. For remote use, place behind reverse proxy + TLS.
- **Network Isolation:** Only MCP container publishes a port. Others stay on private network.
- **Input Validation:** Whitelists ingestion schemes (https://, file:// local). Optional domain allowlist per container.
- **Data Residency:** All blobs stored locally in MinIO; export feature gated behind explicit manifest flag.
- **Secrets Hygiene:** Provided via env vars, not committed. Logs redact tokens/keys.

---

## Failure Modes & Mitigations

| Failure | Impact | Detection | Mitigation |
|---------|--------|-----------|------------|
| Postgres down | All API endpoints fail | `/health` + connection errors | Restart container, run migrations after recovery |
| Qdrant unavailable | Search degrades to BM25-only | Adapter raises `VectorStoreUnavailable` | Return partial results, flag `issues=["VECTOR_DOWN"]`, queue reconciliation |
| Nomic API timeout | Query/ingest latency spike | Adapter timeout metrics | Retry w/ exponential backoff, fallback to cached embeddings or BM25-only |
| Worker crash | Ingestion backlog grows | `ingest_queue_depth` + job age alerts | Supervisor restarts worker container, DLQ stuck jobs |
| Disk full | Writes fail | Docker metrics + MinIO alerts | Rotate/trim logs, expand host disk, enforce retention policies |
| Manifest drift (schema mismatch) | Requests fail validation | Adapter schema checks | Prevent deployments until manifest/DB schema reconciled |

---

## Phase Transitions

- **Phase 1 (current):** Single-container prototype, hybrid search, Postgres-backed queue, no rerank
- **Phase 2:** Introduce rerank provider, refresh/export endpoints, image ingestion + crossmodal search, rerank cache
- **Phase 3:** Multi-vector embeddings (named vectors), observability dashboards, automated eval gates

---

## References

- `single_source_of_truth/architecture/DATA_MODEL.md` — schema + invariants
- `single_source_of_truth/architecture/API_CONTRACTS.md` — MCP surface area
- `single_source_of_truth/work/CURRENT_FOCUS.md` — active implementation focus
