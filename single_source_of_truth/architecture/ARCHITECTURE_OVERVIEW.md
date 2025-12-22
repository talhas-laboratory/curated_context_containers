# Architecture Overview — Local Latent Containers

**Purpose:** Single-page map of all major components, their responsibilities, and how they connect. Complements `SYSTEM.md`, `DATA_MODEL.md`, and `API_CONTRACTS.md`.
**Scope:** Phase 2 state (multimodal + rerank) with Phase 3 hooks noted.

---

## System Shape

```
MCP Clients (Claude, Cursor, CLI, SDK) / Frontend (Next.js)
        │ HTTP/JSON (MCP v1 tools, /v1 REST)
        ▼
 FastAPI MCP Server (mcp-server/)
   ├─ API Layer (routers)     ├─ Auth/ACL     ├─ Diagnostics
   ├─ Service Layer: Search · Ingest · Manifest · Diagnostics · Admin
   ├─ Adapter Layer: Postgres · Qdrant · MinIO · Embedding · Cache
   └─ Job Dispatcher (enqueue ingestion/refresh/export)
        │                                        │
        │ gRPC/HTTP/SQL                          │ Postgres job poll
        ▼                                        ▼
 Data Plane: Postgres · Qdrant · MinIO    Worker Pool (workers/)
```

---

## Component Purposes & Interconnections

- **Frontend (frontend/)** — Next.js App Router UI for gallery, search workspace, diagnostics rail, maintenance (refresh/export). Uses React Query hooks over MCP HTTP client (`src/lib/mcp-client.ts`). Tokens from env or `localStorage`. Talks directly to FastAPI over HTTP/MCP.

- **MCP Gateway (mcp-server-gateway/)** — stdio MCP server that maps agent tool calls (`containers_list/search/add/describe`, `jobs_status`) to HTTP calls against FastAPI. Used by Claude Desktop/Cursor. Shares auth token and base URL via env.

- **Agents SDK (agents-sdk/)** — Python client + LangChain/LlamaIndex adapters. Wraps session metadata (agent_id/name), exposes container list/describe/search/add/jobs, and reuses the same HTTP contracts. Integrates into agent workflows without touching UI.

- **FastAPI MCP Server (mcp-server/)** — Contract-first surface that hosts:
  - **API Layer (`app/api/*`)**: `/v1` REST + `/mcp` tool descriptors. Validates requests (Pydantic v2), applies bearer auth, emits envelopes with diagnostics toggles.
  - **Service Layer**:  
    - *SearchService*: query embedding (Nomic multimodal), parallel vector (Qdrant) + BM25 (Postgres) retrieval, RRF fusion, optional rerank, dedup/freshness heuristics.  
    - *IngestService*: validates sources vs manifest, writes metadata stubs, enqueues jobs.  
    - *ManifestService*: CRUD/cache for container manifests, policy checks for adapters.  
    - *DiagnosticsService*: aggregates stage timings, issue codes, container health.  
    - *AdminService*: refresh/export orchestration (fastpath + worker path).
  - **Adapter Layer**:  
    - *PostgresAdapter*: typed queries for registry/FTS/jobs/embedding cache, advisory locks.  
    - *QdrantAdapter*: collection lifecycle, batched upserts/search per modality.  
    - *MinIOAdapter*: blob/originals/thumbnails/PDF renders via canonical paths.  
    - *EmbeddingAdapter*: HTTPX client to Nomic multimodal with hash-based caching.  
    - *CacheAdapter* (optional Phase 3 Redis/SQLite) for embed cache acceleration.
  - **Job Dispatcher**: writes jobs to Postgres for workers; admin fastpath can execute refresh/export inline for UI tests.

- **Worker Pool (workers/)** — Async ingestion executors polling Postgres `jobs` via `FOR UPDATE SKIP LOCKED`. Pipelines in `workers/pipelines/{text,pdf,image,web}.py` perform fetch → extract → chunk → embed (cache-aware) → persist (Postgres+Qdrant+MinIO) → status/metrics. Implements retries/backoff and DLQ semantics (failed payload snapshot). Will host refresh/export handlers in Phase 3.

- **Data Stores**  
  - *PostgreSQL (migrations/)*: source of truth for containers/documents/chunks/jobs, BM25 FTS, embedding cache, manifests, advisory locks.  
  - *Qdrant*: per-container/per-modality collections `c_<container>_<modality>` holding embeddings + mirrored payloads.  
  - *Neo4j*: graph store for Graph RAG nodes/edges (Cypher via bolt), scoped per container.  
  - *MinIO*: object storage for originals, thumbnails, PDF page renders using manifest-driven path scheme.  
  - *Local volumes*: Docker named volumes for persistence (`pg_data`, `qdrant_data`, `minio_data`, `worker_cache`).

- **External Services** — Nomic multimodal embedding API (text/image). Optional rerank API reserved for Phase 2/3. No other runtime cloud dependencies by design.

- **Infrastructure & Ops**  
  - `docker/compose.local.yaml`: single-node stack; only MCP port exposed to host.  
  - Observability: structured JSON logs, Prometheus metrics, health endpoints; budgets from `SYSTEM.md` enforced via diagnostics.  
  - CI/CD (Makefile + workflows): migrate → pytest(+cov) → smoke → golden (Playwright optional via `CI_E2E`).

- **Knowledge & Governance (single_source_of_truth/)**  
  - Vision/Context/Progress, architecture specs (`SYSTEM.md`, `DATA_MODEL.md`, `API_CONTRACTS.md`), ADRs, design system, runbooks, diaries. Acts as canonical intent; implementations mirror these contracts.

---

## End-to-End Flows

- **Ingestion**: Client/UI/SDK calls `containers.add` → IngestService validates/creates `jobs` row → Worker claims job → fetch/extract/chunk → embed (cache check via Postgres/optional Redis) → persist metadata in Postgres, vectors in Qdrant, blobs in MinIO → job status/metrics surfaced via `jobs_status` and diagnostics.

- **Search (hybrid by default)**: Client calls `containers.search` with query/modalities/containers → SearchService embeds query → parallel Qdrant vector + Postgres BM25 → Reciprocal Rank Fusion → optional rerank → dedup/freshness boost → response with snippets, provenance, diagnostics/issue codes.

- **Refresh/Export (Phase 2 baseline, Phase 3 hardening)**: Admin/API triggers refresh/export → either fastpath (inline) or enqueue to workers → workers rebuild embeddings/blobs or package manifest/vectors/blobs into MinIO artifact → statuses reported via jobs endpoints.

---

## Responsibilities by Module (Implementation Mapping)

- `frontend/`: Presentation, interaction, and MCP client integration; no business logic beyond view-model shaping.
- `mcp-server/`: All request validation, policy enforcement, orchestration, and adapter coordination; authoritative contracts.
- `workers/`: Long-running, failure-tolerant ingestion/maintenance execution; no direct client exposure.
- `agents-sdk/`: Typed client and agent-facing abstractions; no persistence; defers to server contracts.
- `mcp-server-gateway/`: Thin translation layer MCP stdio ↔ HTTP; stateless aside from config.
- `migrations/`: Canonical SQL schema; Alembic wrapper reuses the same SQL.
- `docker/`: Runtime topology, env/secrets wiring, health checks; keeps non-MCP services private.
- `single_source_of_truth/`: Governance, decisions, design system, runbooks, and architecture specs that precede code changes.

---

## Interfaces & Contracts

- **Protocols:** MCP v1 tools (stdio for gateway, HTTP for frontend/SDK), REST `/v1/*` for direct calls. All authenticated via bearer token.
- **Schemas:** Defined in `API_CONTRACTS.md`; enforced by FastAPI/Pydantic; mirrored in SDK and gateway tool schemas.
- **Data Model:** `DATA_MODEL.md` + `migrations/001_initial_schema.sql` define tables, indexes, and payload shapes; Qdrant payloads mirror chunk metadata.
- **Metrics/Diagnostics:** Prometheus names in `SYSTEM.md`; diagnostics envelopes include timings, hit counts, issue codes; logs carry `request_id`, agent metadata.

---

## Phase Outlook

- **Complete (Phase 2):** Multimodal ingest, crossmodal search, rerank provider/cache, refresh/export endpoints, CI/golden gates, UI parity.
- **Planned (Phase 3):** Multi-vector embeddings, deeper observability dashboards, refresh/export worker handlers, router cutover tooling, DLQ + rate limiting, enhanced cache layer.

---

## How to Navigate

- Want contracts? See `single_source_of_truth/architecture/API_CONTRACTS.md`.
- Need data shapes? See `single_source_of_truth/architecture/DATA_MODEL.md` and `migrations/001_initial_schema.sql`.
- Running locally? Start with `docker/README.md` and `Makefile` targets.
- Building clients/agents? Start with `agents-sdk/README.md` or `mcp-server-gateway/README.md`.
- UI development? See `frontend/README.md` and `single_source_of_truth/design/`.
