# Vision & North Star

A local-first, MCP-addressable **collection of themed content containers** (e.g., *Expressionist Art*, *Protein Folding*) holding **embedded representations** of text, PDFs, images, and single-page websites. Agents (Claude, ChatGPT, your own) call a **thin MCP server** to: list containers, ingest content, and retrieve context via **hybrid search** (dense vectors + BM25) with optional **reranking**. Everything is **versioned, portable, and pluggable** via per-container manifests.

---

# High-Level Architecture

```
Agent (Claude/ChatGPT/Your agents)
   │  MCP tools over localhost:7801
   ▼
MCP Server (FastAPI): list/describe/add/search/refresh/export
   │
   ├─► Qdrant (vectors; one collection per container per modality)
   ├─► Postgres (registry, ACLs, jobs, BM25 text)
   └─► MinIO (S3) for raw blobs & derivatives (PDF renders, thumbnails)

Workers (Celery/RQ) → parse → chunk → call Nomic Embed Multimodal 7B (API) → upsert vectors

```

---

# Tech Stack

## Core Infrastructure

**Containerization & Orchestration**
- Docker 24+ with Docker Compose 2.x
- Named volumes for persistent storage (optimized for macOS M2)

**Vector Database**
- Qdrant 1.11.0
- HNSW indexing (M=32, ef_construct=256)
- On-disk payload storage

**Relational Database**
- PostgreSQL 16
- Extensions: pg_trgm, unaccent (for BM25 full-text search)
- Alembic for schema migrations

**Object Storage**
- MinIO (S3-compatible)
- Bucket-per-container organization
- Original files + derivatives (thumbnails, PDF renders)

## Application Layer

**MCP Server (FastAPI)**
- Python 3.11
- FastAPI 0.115.5
- Uvicorn (ASGI server)
- Pydantic 2.9.2 (data validation)
- HTTPX 0.27.2 (async HTTP client)

**Workers (Job Processing)**
- Python 3.11
- Postgres-based job queue (no broker needed)
- Optimistic locking for job claiming

**Python Libraries**
- **PDF**: PyMuPDF 1.24.10 (text extraction + rendering)
- **Web scraping**: Trafilatura 1.9.0, Readability-lxml 0.9.2, BeautifulSoup4 4.12.3
- **HTTP**: Requests 2.32.3, HTTPX 0.27.2
- **Data**: NumPy (vector operations), orjson 3.10.7 (fast JSON)
- **Utilities**: python-slugify 8.0.4, python-json-logger 2.0.7

## ML & Embeddings

**Embedding Model**
- Nomic Embed Multimodal 7B (via API)
- 1408-dimensional vectors
- L2-normalized for cosine similarity
- Supports text and image inputs

**Optional Reranking**
- External API support (Cohere, Jina AI compatible)
- Placeholder for local cross-encoder models

## Retrieval & Search

**Hybrid Search Components**
- **Dense retrieval**: Qdrant vector search (cosine similarity)
- **Sparse retrieval**: PostgreSQL full-text search (tsvector + GIN index)
- **Fusion**: Reciprocal Rank Fusion (RRF)
- **Deduplication**: Cosine similarity threshold (0.92)
- **Freshness**: Exponential time decay

**Search Modes**
- Semantic (vector-only)
- Hybrid (vector + BM25 + RRF)
- Crossmodal (text ↔ image)
- Rerank (two-stage with top-k refinement)

## Development & Operations

**API Specification**
- OpenAPI 3.1.0
- RESTful HTTP endpoints
- Bearer token authentication (local file-based)

**Logging & Monitoring**
- Structured JSON logging (pythonjsonlogger)
- Docker healthchecks (curl-based)
- Worker heartbeat logging

**Testing**
- Pydantic schema validation
- Golden query evaluation (nDCG@10, Recall@20)
- Regression gates (2% nDCG drop, 20% latency threshold)

**CLI Tools**
- Python scripts for: container creation, ingestion, search, eval, export
- Direct MCP API clients

**Local Commands & Env**
- `make migrate` — run Alembic migrations (`LLC_POSTGRES_DSN` configurable)
- `make smoke` — bootstrap docker stack, ingest sample text/PDF, run hybrid search (diagnostics checked)
- `make golden-queries` — execute `golden_queries.json` against `/v1/search` and print summary stats
- Required env vars: `LLC_NOMIC_API_KEY` (Nomic embed), `LLC_MINIO_*` for MinIO creds; defaults provided for local compose
- CI runs `make migrate`, `make smoke`, `make golden-queries` via `.github/workflows/ci.yml` (services: Postgres, Qdrant, MinIO)

## Data Flow Technologies

**Ingestion Pipeline**
1. Content fetching: requests/httpx
2. Text extraction: trafilatura, readability-lxml, PyMuPDF
3. Image processing: PIL/Pillow (via PyMuPDF)
4. Chunking: semantic (heading-based) + fixed-size fallback
5. Embedding: Nomic API (HTTPS)
6. Storage: PostgreSQL (metadata) + Qdrant (vectors) + MinIO (blobs)

**Retrieval Pipeline**
1. Query embedding: Nomic API
2. Vector search: Qdrant (HNSW approximate)
3. BM25 search: PostgreSQL (tsvector + GIN)
4. Fusion: RRF algorithm (Python)
5. Reranking: External API (optional)
6. Deduplication: Cosine similarity (NumPy)
7. Snippet rendering: Template strings (Python)

## Resource Requirements (MacBook Air M2)

**Minimum Hardware**
- 8GB RAM (16GB recommended)
- 50GB free disk space
- Apple Silicon M2 or equivalent

**Docker Resource Limits**
- Qdrant: 2 CPU cores, 4GB RAM
- PostgreSQL: 1.5 CPU cores, 2GB RAM
- MCP Server: 1 CPU core, 1GB RAM
- Workers: 2 CPU cores, 3GB RAM
- MinIO: Default (< 1GB RAM)

**Network**
- Localhost-only by default (port 7801 exposed for MCP)
- Nomic API requires internet access
- Optional rerank API requires internet access

## Future-Proofing

**Local-First → Production Path**
- Replace file-based auth with OAuth2/JWT
- Replace Postgres job queue with Celery + Redis
- Add Nginx reverse proxy + SSL termination
- Multi-user ACLs via database-backed permissions
- Horizontal scaling with multiple worker nodes

**Supported for Future**
- Multi-vector embeddings (Qdrant named vectors)
- Audio/video modalities (extend ingestion pipeline)
- Incremental indexing (delta updates)
- Cross-container semantic search
- Real-time ingestion via webhooks

---

# Operating Assumptions (Locked)

- **Embeddings:** Nomic Embed Multimodal 7B via API
- **Containers:** themed; **dense** embeddings now; schema supports multi-vector later
- **Retrieval:** **Hybrid** (vector + BM25) with optional rerank (top-50→10)
- **Similarity:** L2-normalized → **cosine**
- **PDFs:** extract text **and** render pages as images
- **Web:** single-page ingestion (no crawl)
- **Images:** originals + 2k-edge thumbnail
- **Dedup:** SHA256 + semantic (cosine ≥ 0.92)
- **Lifecycle:** versioned manifests; parallel index upgrades
- **ACL:** enforced in MCP; DBs never exposed
- **Device:** MacBook Air M2; Docker Desktop; named volumes

---

# Repository Layout

```
latent-containers/
├─ docker/                     # compose files, healthchecks
├─ mcp-server/                 # FastAPI app exposing MCP tools
│  ├─ app/
│  │  ├─ api/                  # routers: containers, admin, stats
│  │  ├─ core/                 # settings, logging, security
│  │  ├─ models/               # pydantic schemas (v1)
│  │  ├─ services/             # search, fuse, rerank, manifests
│  │  ├─ adapters/             # qdrant, postgres, minio, nomic
│  │  └─ mcp/                  # MCP tool descriptors, discovery
│  └─ tests/
├─ workers/
│  ├─ pipelines/               # text/pdf/image/web
│  ├─ jobs/                    # ingest/add, refresh, export
│  ├─ util/                    # chunking, hashing, cache, dedup
│  └─ tests/
├─ manifests/                  # per-container manifests (YAML)
├─ migrations/                 # Postgres Alembic migrations
├─ scripts/                    # CLI: create container, export, eval
└─ docs/                       # runbooks, ADRs, metrics

```

---

# Docker Compose (M2-tuned)

```yaml
version: "3.9"
services:
  qdrant:
    image: qdrant/qdrant:v1.11.0
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]
    environment:
      QDRANT__STORAGE__ON_DISK_PAYLOAD: "true"
      QDRANT__SERVICE__GRPC_PORT: 6334
    deploy: {resources: {limits: {cpus: "2", memory: 4g}}}

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: local
      POSTGRES_PASSWORD: localpw
      POSTGRES_DB: registry
    ports: ["5432:5432"]
    volumes: ["pg_data:/var/lib/postgresql/data"]
    deploy: {resources: {limits: {cpus: "1.5", memory: 2g}}}

  minio:
    image: quay.io/minio/minio:RELEASE.2025-01-10T00-00-00Z
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: localminio
      MINIO_ROOT_PASSWORD: localminio123
    ports: ["9000:9000", "9001:9001"]
    volumes: ["minio_data:/data"]

  mcp:
    build: ./mcp-server
    environment:
      REG_DB_DSN: postgresql://local:localpw@postgres:5432/registry
      QDRANT_URL: http://qdrant:6333
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: localminio
      MINIO_SECRET_KEY: localminio123
      NOMIC_API_KEY: ${NOMIC_API_KEY}
      # Rerank provider optional: set URL/TOKEN or leave off
    ports: ["7801:7801"]
    depends_on: [qdrant, postgres, minio]
    deploy: {resources: {limits: {cpus: "1", memory: 1g}}}

  workers:
    build: ./workers
    environment:
      REG_DB_DSN: postgresql://local:localpw@postgres:5432/registry
      QDRANT_URL: http://qdrant:6333
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: localminio
      MINIO_SECRET_KEY: localminio123
      NOMIC_API_KEY: ${NOMIC_API_KEY}
      EMBED_RATE_LIMIT_PER_MIN: "120"
    depends_on: [qdrant, postgres, minio]
    deploy: {resources: {limits: {cpus: "2", memory: 3g}}}

volumes:
  qdrant_data:
  pg_data:
  minio_data:

```

---

# Postgres Schema (Registry/Jobs/BM25)

```sql
-- Containers registry
CREATE TABLE containers (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  theme TEXT NOT NULL,
  modalities TEXT[] NOT NULL,          -- ["text","image"]
  embedder TEXT NOT NULL,               -- nomic-embed-mm-7b
  embedder_version TEXT NOT NULL,
  dims INT NOT NULL,
  policy JSONB NOT NULL,                -- knobs from manifest
  acl JSONB NOT NULL DEFAULT '{}',
  state TEXT NOT NULL DEFAULT 'active', -- active|readonly|archived
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Documents & chunks metadata (text is also stored here for BM25)
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  container_id UUID REFERENCES containers(id),
  uri TEXT,
  mime TEXT,
  hash TEXT,
  title TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chunks (
  id UUID PRIMARY KEY,
  container_id UUID REFERENCES containers(id),
  doc_id UUID REFERENCES documents(id),
  modality TEXT CHECK (modality IN ('text','image')),
  text TEXT,                             -- for BM25 & snippets
  offsets INT4RANGE,                     -- token offsets if text
  tsrange TSRANGE,                       -- timestamps for AV if needed
  provenance JSONB NOT NULL,             -- {source_uri, fetched_at, handler_version, embedder_version, page, ...}
  meta JSONB,                            -- custom metadata per your request
  created_at TIMESTAMP DEFAULT NOW()
);

-- BM25 (PG trigram or pg_btree_gin + ts_vector)
ALTER TABLE chunks ADD COLUMN tsv tsvector;
CREATE INDEX idx_chunks_tsv ON chunks USING gin(tsv);
-- Populate tsv on insert/update in workers (language configurable)

-- Jobs for ingestion/refresh/export
CREATE TABLE jobs (
  id UUID PRIMARY KEY,
  kind TEXT,               -- ingest|refresh|export
  status TEXT,             -- queued|running|done|failed
  payload JSONB,
  error TEXT,
  retries INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

```

---

# Qdrant Layout

- One **collection per container per modality**:
    - `c_<container_id>_text`
    - `c_<container_id>_image`
- Vector params:
    - size = `dims` (from manifest), distance = `Cosine`
    - HNSW: `M=32`, `ef_construct=256`, search `ef=64` (tune per container)
- Payload fields (mirrored from Postgres `chunks`):
    - `doc_id`, `chunk_id`, `uri`, `modality`, `score_debug`, `provenance`, `meta`

---

# Container Manifest (YAML)

```yaml
id: "expressionist-art"
name: "Expressionist Art"
theme: "art"
modalities: ["text","image"]
embedder: "nomic-embed-multimodal-7b"
embedder_version: "1.0.0"
dims: 1408
retrieval:
  mode_default: "hybrid"            # semantic|hybrid|multivector|crossmodal|rerank
  fusion: { method: "rrf" }
  freshness: { enabled: true, decay_lambda: 0.02 }
  rerank: { enabled: true, top_k_in: 50, top_k_out: 10, provider: "api" }
  debug: { return_diagnostics: true }
chunker:
  mode: "semantic_then_fallback"
  size: 600
  overlap: 0.12
pdf:
  render_dpi: 150
  max_pages: 1000
image:
  thumbnail_max_edge: 2048
  compress_quality: 90
web:
  javascript: false
  sanitize_rules: ["strip_nav","strip_ads"]
dedup:
  semantic_threshold: 0.92
metadata:
  custom_schema:
    period: ["modernism","baroque","renaissance"]
    confidence: "float"
storage:
  blobs:
    bucket: "latent-expressionist"
backup:
  cron: "0 3 * * *"
eval:
  enabled: true
  metrics: ["ndcg@10","recall@20","latency"]
display:
  sort: "score_then_freshness"
  snippet_template: "{title} — {snippet}"
  max_snippet_chars: 320
acl:
  roles:
    owner: ["local:you"]
    reader: ["agent:claude","agent:chatgpt","agent:local"]

```

---

# Ingestion Pipelines (Workers)

**Global principles**

- Compute **content hash** (SHA256) to dedup & cache embeddings
- On insert/update: populate Postgres row(s); generate BM25 `tsv`; upsert vectors to Qdrant
- Store raw blobs in MinIO under `bucket/container_id/<doc_id>/...`

**Text / Web (single page)**

1. Fetch (requests; or Playwright if `web.javascript: true`)
2. Extract main content (trafilatura/readability)
3. Chunk: semantic by headings else 400–700 tokens, 10–15% overlap
4. Embed: Nomic API (normalized vectors)
5. Upsert: Postgres `documents` + `chunks` (+ `tsv`), Qdrant `c_<id>_text`

**PDFs**

1. Parse text (pymupdf); page → text blocks
2. Render page PNG at `render_dpi`; store in MinIO
3. Chunk text; embed text chunks → Qdrant text
4. Embed page images (and optional cropped figures) → Qdrant image

**Images**

1. Store original + thumbnail → MinIO
2. Embed image → Qdrant image
3. (Optional) Caption to `text` for BM25/snippets

**Dedup flow**

- Before embedding: check hash cache → reuse vector(s) if identical
- After insert: semantic dedup within container (cosine ≥ 0.92) → mark `meta.duplicate_of`

**Jobs & rate limiting**

- Token bucket per worker: `EMBED_RATE_LIMIT_PER_MIN`
- Retries with exponential backoff; DLQ for persistent failures

---

# Retrieval Engine (in MCP Server)

**Modes**

- `semantic`: Qdrant vector search only
- `hybrid`: BM25 (Postgres `tsv`) + Qdrant → **RRF fusion**
- `crossmodal`: allow querying both text & image indexes
- `rerank`: two-stage; semantic/hybrid → rerank top-50→10 via API or light local model
- `multivector`: placeholder for future switch (uses named vectors)

**Algorithm (hybrid default)**

1. Embed query (text or image) via Nomic API
2. Vector search K=100 per target modality/collection (apply filters from manifest)
3. BM25 search k=100 over `chunks.tsv` (container-scoped)
4. **RRF** merge → top-50
5. Optional **re-rank** → top-10
6. **Dedup** by doc overlap or cosine ≥ 0.92
7. Apply **freshness** boost if enabled
8. Build **clean snippets** using stored `text` and `snippet_template`

**Diagnostics (when `debug.return_diagnostics: true`)**

- stage_scores: {bm25, vector}
- candidates_before/after_rerank
- applied_filters, freshness_factor
- timing per stage, container_status[]

---

# MCP v1 API (Tool Contracts)

**All responses include** `{request_id, version:"v1", partial, timings, issues:[]}`

## `containers.list()`

**Response** `200`

```json
{
  "containers": [
    {"id":"expressionist-art","name":"Expressionist Art","modalities":["text","image"],"dims":1408,"state":"active"}
  ]
}

```

## `containers.describe(container_id)`

**Response** `200`: full manifest + sizes, last_ingest_at

## `containers.add({container_id, uri|file_ref, modality})`

**Response** `202` `{job_id, status:"queued"}`

## `containers.search({containers[], query|image_ref, mode, top_k, filters, rerank_k, dedup})`

**Response** `200`

```json
{
  "hits": [
    {
      "container_id":"expressionist-art",
      "doc_id":"...","chunk_id":"...",
      "modality":"text",
      "score":0.83,
      "title":"Kandinsky — Concerning the Spiritual in Art",
      "snippet":"...",
      "uri":"s3://latent-expressionist/.../pg12.png",
      "offsets":[120,780],
      "provenance":{"source_uri":"https://...","fetched_at":"...","embedder_version":"1.0.0"},
      "meta":{"period":"modernism","confidence":0.93}
    }
  ],
  "diagnostics": {
    "stage_scores": {"bm25": [...], "vector": [...]},
    "timings_ms": {"embed": 18, "vector": 22, "bm25": 14, "fuse": 3, "rerank": 48}
  }
}

```

## `admin.refresh({container_id, strategy})`

Rebuild embeddings for a container (e.g., after model upgrade). Returns job id.

## `containers.export({container_id})`

Produce tarball with manifest + metadata snapshot; pointers to MinIO blobs.

**Error taxonomy**: `AUTH, TIMEOUT, NO_HITS, RATE_LIMIT, POLICY, INGEST_FAIL`

---

# MCP Tool Discovery & Registration

**How agents discover available tools**

The MCP server exposes a tool discovery endpoint that returns the complete tool manifest in MCP-compatible format.

## `GET /mcp/tools`

**Response** `200`

```json
{
  "tools": [
    {
      "name": "containers.list",
      "description": "List all available themed containers in the system",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    },
    {
      "name": "containers.describe",
      "description": "Get full manifest and metadata for a specific container",
      "inputSchema": {
        "type": "object",
        "properties": {
          "container_id": {"type": "string", "description": "Container ID to describe"}
        },
        "required": ["container_id"]
      }
    },
    {
      "name": "containers.add",
      "description": "Ingest new content (URI or file) into a container",
      "inputSchema": {
        "type": "object",
        "properties": {
          "container_id": {"type": "string", "description": "Target container ID"},
          "uri": {"type": "string", "description": "URI to fetch and ingest"},
          "file_ref": {"type": "string", "description": "File reference (alternative to uri)"},
          "modality": {"type": "string", "enum": ["auto", "text", "image"], "description": "Content modality"}
        },
        "required": ["container_id"]
      }
    },
    {
      "name": "containers.search",
      "description": "Search containers using hybrid retrieval (vector + BM25) with optional reranking",
      "inputSchema": {
        "type": "object",
        "properties": {
          "containers": {"type": "array", "items": {"type": "string"}, "description": "Container IDs to search"},
          "query": {"type": "string", "description": "Text query"},
          "image_ref": {"type": "string", "description": "Image reference for visual search"},
          "mode": {"type": "string", "enum": ["semantic", "hybrid", "multivector", "crossmodal", "rerank"], "default": "hybrid"},
          "top_k": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
          "filters": {"type": "object", "description": "Metadata filters"},
          "rerank_k": {"type": "integer", "description": "Candidates to rerank before final top_k"},
          "dedup": {"type": "boolean", "default": true, "description": "Enable semantic deduplication"}
        },
        "required": ["containers", "top_k"]
      }
    },
    {
      "name": "admin.refresh",
      "description": "Rebuild embeddings for a container (e.g., after model upgrade)",
      "inputSchema": {
        "type": "object",
        "properties": {
          "container_id": {"type": "string"},
          "strategy": {"type": "string", "enum": ["parallel", "inplace"], "default": "parallel"}
        },
        "required": ["container_id"]
      }
    },
    {
      "name": "containers.export",
      "description": "Export container as tarball with manifest and metadata snapshot",
      "inputSchema": {
        "type": "object",
        "properties": {
          "container_id": {"type": "string"}
        },
        "required": ["container_id"]
      }
    }
  ]
}
```

**Implementation location**: `mcp-server/app/mcp/discovery.py`

Agents (Claude, ChatGPT, custom) call this endpoint on initialization to learn what operations are available.

---

# Authentication Flow (Local First)

**Token configuration and validation**

The MCP server requires a bearer token to be configured via environment or a secrets
store (no repo-managed token files).

## Token Bootstrap

1. Set `LLC_MCP_TOKEN` in your environment or `.env.home`
2. Ensure clients send `Authorization: Bearer <token>`
3. Do not commit tokens to the repository

## Token Validation

All MCP endpoints require `Authorization: Bearer <token>` header.

**Implementation** (`mcp-server/app/core/security.py`):

```python
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path

security = HTTPBearer()

def load_token() -> str:
    token = os.getenv("LLC_MCP_TOKEN")
    if token:
        return token.strip()
    raise RuntimeError("LLC_MCP_TOKEN is required to start the server.")

def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    expected_token = load_token()
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
```

**Usage in routers**:

```python
from fastapi import Depends
from app.core.security import verify_bearer_token

@router.get("/v1/containers/list")
async def list_containers(authenticated: bool = Depends(verify_bearer_token)):
    # ... implementation
```

## CLI Token Usage

```bash
# Export token for CLI scripts
export MCP_TOKEN="$LLC_MCP_TOKEN"

# Use in requests
curl -H "Authorization: Bearer $MCP_TOKEN" http://localhost:7801/v1/containers/list
```

**Future productization note**: For multi-user deployment, replace file-based token with proper OAuth2/JWT flow and user-scoped ACLs.

---

# Worker Architecture (Postgres-based Queue)

**Simple, broker-free job processing**

For local-first simplicity, workers poll the Postgres `jobs` table directly—no Redis/RabbitMQ needed.

## Job Queue Model

Workers use **optimistic locking** to claim jobs:

```sql
-- Claim a job (atomic)
UPDATE jobs 
SET status = 'running', updated_at = NOW()
WHERE id = (
  SELECT id FROM jobs 
  WHERE status = 'queued' 
  ORDER BY created_at ASC 
  LIMIT 1 
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

## Worker Loop

**Implementation** (`workers/jobs/worker.py`):

```python
import time
import logging
from workers.jobs import ingest, refresh, export
from workers.adapters.postgres import get_connection

logger = logging.getLogger(__name__)
POLL_INTERVAL = 5  # seconds

JOB_HANDLERS = {
    "ingest": ingest.handle,
    "refresh": refresh.handle,
    "export": export.handle,
}

def claim_job(conn):
    """Atomically claim next queued job"""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE jobs 
            SET status = 'running', updated_at = NOW()
            WHERE id = (
                SELECT id FROM jobs 
                WHERE status = 'queued' 
                ORDER BY created_at ASC 
                LIMIT 1 
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, kind, payload;
        """)
        return cur.fetchone()

def mark_done(conn, job_id):
    with conn.cursor() as cur:
        cur.execute("UPDATE jobs SET status = 'done', updated_at = NOW() WHERE id = %s", (job_id,))
    conn.commit()

def mark_failed(conn, job_id, error_msg):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status = 'failed', error = %s, retries = retries + 1, updated_at = NOW() WHERE id = %s",
            (error_msg, job_id)
        )
    conn.commit()

def worker_loop():
    conn = get_connection()
    logger.info("Worker started, polling every %ds", POLL_INTERVAL)
    
    while True:
        try:
            job = claim_job(conn)
            if job:
                job_id, kind, payload = job
                logger.info("Processing job %s (kind=%s)", job_id, kind)
                
                try:
                    handler = JOB_HANDLERS[kind]
                    handler(payload)
                    mark_done(conn, job_id)
                    logger.info("Job %s completed", job_id)
                except Exception as e:
                    logger.error("Job %s failed: %s", job_id, str(e), exc_info=True)
                    mark_failed(conn, job_id, str(e))
            else:
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            logger.error("Worker loop error: %s", str(e), exc_info=True)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    worker_loop()
```

## Dockerfile CMD

```dockerfile
CMD ["python", "-m", "jobs.worker"]
```

## Rate Limiting

Workers respect `EMBED_RATE_LIMIT_PER_MIN` using token bucket:

```python
# workers/util/rate_limit.py
import time
from threading import Lock

class TokenBucket:
    def __init__(self, rate_per_min: int):
        self.capacity = rate_per_min
        self.tokens = rate_per_min
        self.rate = rate_per_min / 60.0  # tokens per second
        self.last_update = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_for_token(self):
        while not self.consume():
            time.sleep(0.1)
```

**Future productization note**: For scale, migrate to Celery + Redis with priority queues and distributed workers.

---

# Manifest Bootstrap & Loading

**Container initialization on startup**

The MCP server automatically loads and validates all manifests on startup.

## Startup Sequence

**Implementation** (`mcp-server/app/main.py`):

```python
from fastapi import FastAPI
from pathlib import Path
from app.services.manifests import load_all_manifests
from app.adapters.qdrant import ensure_collections
from app.adapters.postgres import init_db

app = FastAPI()

@app.on_event("startup")
async def bootstrap():
    """Initialize system on startup"""
    # 1. Ensure database schema exists
    init_db()
    
    # 2. Load and validate all manifests
    manifest_dir = Path("/app/manifests")
    containers = await load_all_manifests(manifest_dir)
    
    # 3. Ensure Qdrant collections exist for each container
    for container in containers:
        await ensure_collections(container)
    
    logger.info("Bootstrap complete: %d containers loaded", len(containers))
```

## Manifest Loader

**Implementation** (`mcp-server/app/services/manifests.py`):

```python
import yaml
from pathlib import Path
from pydantic import BaseModel, ValidationError
from typing import List
from app.models.container import ContainerManifest
from app.adapters.postgres import upsert_container

async def load_all_manifests(manifest_dir: Path) -> List[ContainerManifest]:
    """Load and validate all YAML manifests"""
    containers = []
    
    for yaml_file in manifest_dir.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            
            # Validate against Pydantic model
            manifest = ContainerManifest(**data)
            
            # Upsert to database
            await upsert_container(manifest)
            
            containers.append(manifest)
            logger.info("Loaded manifest: %s", manifest.id)
            
        except ValidationError as e:
            logger.error("Invalid manifest %s: %s", yaml_file, e)
            raise
        except Exception as e:
            logger.error("Failed to load %s: %s", yaml_file, e)
            raise
    
    return containers
```

## Qdrant Collection Initialization

**Implementation** (`mcp-server/app/adapters/qdrant.py`):

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from app.models.container import ContainerManifest

async def ensure_collections(container: ContainerManifest):
    """Create Qdrant collections if they don't exist"""
    client = get_qdrant_client()
    
    existing = {c.name for c in client.get_collections().collections}
    
    for modality in container.modalities:
        collection_name = f"c_{container.id}_{modality}"
        
        if collection_name not in existing:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qm.VectorParams(
                    size=container.dims,
                    distance=qm.Distance.COSINE
                ),
                hnsw_config=qm.HnswConfigDiff(
                    m=32,
                    ef_construct=256
                ),
                optimizers_config=qm.OptimizersConfigDiff(
                    default_segment_number=2
                )
            )
            logger.info("Created collection: %s", collection_name)
```

---

# Snippet Rendering System

**Template-based snippet generation**

Snippets are built from stored chunk text using container-specific templates.

## Snippet Builder

**Implementation** (`mcp-server/app/services/snippets.py`):

```python
def render_snippet(
    hit: dict,
    template: str,
    max_chars: int,
    meta_schema: dict = None
) -> str:
    """
    Render a snippet using template variables
    
    Args:
        hit: Search result with text, title, meta fields
        template: Format string like "{title} — {snippet}"
        max_chars: Maximum snippet length
        meta_schema: Optional schema for custom metadata fields
    
    Returns:
        Formatted snippet string
    """
    # Extract and truncate main text
    text = hit.get("text", "")
    snippet = text[:max_chars]
    if len(text) > max_chars:
        # Truncate at last complete word
        snippet = snippet.rsplit(" ", 1)[0] + "..."
    
    # Build template context
    context = {
        "title": hit.get("title", "Untitled"),
        "snippet": snippet,
        "doc_id": hit.get("doc_id", ""),
        "score": f"{hit.get('score', 0):.2f}",
    }
    
    # Add custom metadata fields
    meta = hit.get("meta", {})
    if meta_schema:
        for field, field_type in meta_schema.items():
            if field in meta:
                if field_type == "float":
                    context[field] = f"{meta[field]:.2f}"
                else:
                    context[field] = str(meta[field])
    
    try:
        return template.format(**context)
    except KeyError as e:
        logger.warning("Template variable missing: %s", e)
        return f"{context['title']} — {context['snippet']}"

def apply_display_config(hits: list, display_config: dict) -> list:
    """
    Apply container display configuration to search results
    
    Args:
        hits: List of search results
        display_config: Display settings from manifest
    
    Returns:
        Formatted hits with rendered snippets
    """
    template = display_config.get("snippet_template", "{title} — {snippet}")
    max_chars = display_config.get("max_snippet_chars", 320)
    sort_mode = display_config.get("sort", "score_then_freshness")
    
    # Render snippets
    for hit in hits:
        hit["rendered_snippet"] = render_snippet(
            hit, 
            template, 
            max_chars,
            meta_schema=display_config.get("metadata", {}).get("custom_schema")
        )
    
    # Apply sorting
    if sort_mode == "freshness_then_score":
        hits.sort(key=lambda h: (-h.get("freshness_score", 0), -h.get("score", 0)))
    elif sort_mode == "source_then_score":
        hits.sort(key=lambda h: (h.get("source_priority", 999), -h.get("score", 0)))
    # default: score_then_freshness already applied in retrieval
    
    return hits
```

## Usage in Search Endpoint

```python
from app.services.snippets import apply_display_config

@router.post("/v1/containers/search")
async def search(request: SearchRequest):
    # ... perform retrieval ...
    
    # Get container manifests
    manifests = {c.id: c for c in await get_containers(request.containers)}
    
    # Apply display config per container
    for hit in hits:
        container_id = hit["container_id"]
        manifest = manifests[container_id]
        hit = apply_display_config([hit], manifest.display)[0]
    
    return SearchResponse(hits=hits, ...)
```

---

# Freshness Boost Implementation

**Time-decay scoring for recent content**

Freshness boosts prioritize recent content using exponential decay.

## Decay Formula

**Implementation** (`mcp-server/app/services/search.py`):

```python
import math
from datetime import datetime

def apply_freshness_boost(
    score: float,
    created_at: datetime,
    decay_lambda: float = 0.02,
    enabled: bool = True
) -> tuple[float, float]:
    """
    Apply exponential time decay to boost recent content
    
    Args:
        score: Base relevance score (0-1)
        created_at: When content was created/ingested
        decay_lambda: Decay rate (higher = faster decay)
        enabled: Whether freshness is enabled in manifest
    
    Returns:
        (boosted_score, freshness_factor)
    
    Formula:
        boost = exp(-lambda * age_in_days)
        final_score = score * (1 + boost)
    
    Examples:
        lambda=0.02, age=0 days  → boost=1.0  (doubles score)
        lambda=0.02, age=30 days → boost=0.55 (55% boost)
        lambda=0.02, age=100 days → boost=0.14 (14% boost)
    """
    if not enabled:
        return score, 1.0
    
    age_days = (datetime.utcnow() - created_at).days
    age_days = max(0, age_days)  # Handle future dates
    
    freshness_factor = math.exp(-decay_lambda * age_days)
    boosted_score = score * (1 + freshness_factor)
    
    return boosted_score, freshness_factor

def apply_freshness_to_results(
    hits: list,
    freshness_config: dict
) -> list:
    """Apply freshness boosting to all search results"""
    if not freshness_config.get("enabled", False):
        return hits
    
    decay_lambda = freshness_config.get("decay_lambda", 0.02)
    
    for hit in hits:
        created_at = hit.get("created_at")
        if created_at:
            boosted, factor = apply_freshness_boost(
                hit["score"],
                created_at,
                decay_lambda
            )
            hit["score"] = boosted
            hit["freshness_factor"] = factor
    
    # Re-sort by boosted scores
    hits.sort(key=lambda h: h["score"], reverse=True)
    
    return hits
```

## Integration in Hybrid Search

```python
async def hybrid_search(
    query: str,
    container: ContainerManifest,
    top_k: int
) -> list:
    # 1. Vector + BM25 + fusion
    candidates = await perform_hybrid_retrieval(query, container, k=100)
    
    # 2. Optional rerank
    if container.retrieval.rerank.enabled:
        candidates = await rerank(query, candidates)
    
    # 3. Apply freshness
    freshness_config = container.retrieval.freshness
    candidates = apply_freshness_to_results(candidates, freshness_config)
    
    # 4. Dedup and return top-k
    return deduplicate(candidates)[:top_k]
```

---

# Semantic Deduplication

**Prevent near-duplicate chunks using cosine similarity**

Dedup runs after ingestion and during search to remove redundant content.

## Dedup During Ingestion

**Implementation** (`workers/util/dedup.py`):

```python
import numpy as np
from workers.adapters.qdrant import search_vectors

def check_semantic_duplicate(
    vector: np.ndarray,
    container_id: str,
    modality: str,
    threshold: float = 0.92
) -> str | None:
    """
    Check if vector is semantically similar to existing chunks
    
    Args:
        vector: Embedding vector to check
        container_id: Target container
        modality: text or image
        threshold: Cosine similarity threshold (0.92 default)
    
    Returns:
        chunk_id of duplicate if found, else None
    """
    collection_name = f"c_{container_id}_{modality}"
    
    # Search for nearest neighbors
    results = search_vectors(
        collection=collection_name,
        vector=vector,
        limit=5,
        score_threshold=threshold
    )
    
    if results and len(results) > 0:
        # Found a near-duplicate
        duplicate_id = results[0].id
        logger.info(
            "Semantic duplicate found: similarity=%.3f, duplicate_of=%s",
            results[0].score,
            duplicate_id
        )
        return duplicate_id
    
    return None

async def process_chunk_with_dedup(
    chunk_data: dict,
    vector: np.ndarray,
    container: ContainerManifest
) -> bool:
    """
    Process chunk with deduplication check
    
    Returns:
        True if inserted, False if skipped as duplicate
    """
    threshold = container.dedup.semantic_threshold
    
    # Check for semantic duplicate
    duplicate_of = check_semantic_duplicate(
        vector,
        container.id,
        chunk_data["modality"],
        threshold
    )
    
    if duplicate_of:
        # Mark as duplicate in metadata, skip insertion
        chunk_data["meta"]["duplicate_of"] = duplicate_of
        chunk_data["meta"]["skipped_reason"] = "semantic_duplicate"
        
        # Store metadata only (no vector)
        await insert_chunk_metadata_only(chunk_data)
        return False
    
    # Not a duplicate - insert normally
    await insert_chunk(chunk_data, vector)
    return True
```

## Dedup During Search

```python
def deduplicate_search_results(
    hits: list,
    threshold: float = 0.92
) -> list:
    """
    Remove near-duplicate results from search
    
    Uses cosine similarity between result vectors or
    doc_id overlap detection
    """
    seen_docs = set()
    seen_vectors = []
    deduped = []
    
    for hit in hits:
        doc_id = hit["doc_id"]
        
        # Simple doc-level dedup
        if doc_id in seen_docs:
            continue
        
        # Vector-level semantic dedup
        if "vector" in hit:
            is_dup = False
            for seen_vec in seen_vectors:
                similarity = np.dot(hit["vector"], seen_vec)
                if similarity >= threshold:
                    is_dup = True
                    break
            
            if is_dup:
                continue
            
            seen_vectors.append(hit["vector"])
        
        seen_docs.add(doc_id)
        deduped.append(hit)
    
    return deduped
```

---

# Rerank API Contract

**Optional two-stage retrieval with reranking**

When `retrieval.rerank.enabled: true`, the system sends candidates to a reranking model.

## Rerank Service Interface

**Implementation** (`mcp-server/app/services/rerank.py`):

```python
import httpx
from typing import List, Optional

class RerankService:
    """
    Abstract reranker supporting multiple providers:
    - api: External rerank API (Cohere, Jina, etc.)
    - local: Lightweight local model
    - none: No reranking (passthrough)
    """
    
    def __init__(self, provider: str, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider
        self.api_url = api_url
        self.api_key = api_key
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[tuple[int, float]]:
        """
        Rerank documents by relevance to query
        
        Args:
            query: Search query
            documents: List of candidate document texts
            top_k: Number of results to return
        
        Returns:
            List of (original_index, score) tuples sorted by score
        """
        if self.provider == "none":
            # No reranking - return original order with uniform scores
            return [(i, 1.0 - i * 0.01) for i in range(min(top_k, len(documents)))]
        
        elif self.provider == "api":
            return await self._rerank_api(query, documents, top_k)
        
        elif self.provider == "local":
            return await self._rerank_local(query, documents, top_k)
        
        else:
            raise ValueError(f"Unknown rerank provider: {self.provider}")
    
    async def _rerank_api(
        self,
        query: str,
        documents: List[str],
        top_k: int
    ) -> List[tuple[int, float]]:
        """External API reranking (Cohere/Jina compatible)"""
        
        payload = {
            "query": query,
            "documents": documents,
            "top_k": top_k,
            "return_documents": False  # We only need scores
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response format (provider-specific)
            if "results" in data:
                # Cohere format
                results = [
                    (r["index"], r["relevance_score"]) 
                    for r in data["results"]
                ]
            elif "scores" in data:
                # Generic format
                results = [
                    (i, score) 
                    for i, score in enumerate(data["scores"])
                ]
                results.sort(key=lambda x: x[1], reverse=True)
                results = results[:top_k]
            else:
                raise ValueError("Unknown rerank API response format")
            
            return results
    
    async def _rerank_local(
        self,
        query: str,
        documents: List[str],
        top_k: int
    ) -> List[tuple[int, float]]:
        """Local lightweight reranking (placeholder for future)"""
        # TODO: Implement with cross-encoder model
        # For now, fallback to no reranking
        logger.warning("Local reranking not yet implemented, using passthrough")
        return [(i, 1.0 - i * 0.01) for i in range(min(top_k, len(documents)))]


async def rerank_results(
    query: str,
    hits: list,
    rerank_config: dict
) -> list:
    """
    Apply reranking to search results
    
    Args:
        query: Original search query
        hits: Candidate results from hybrid search
        rerank_config: Rerank settings from manifest
    
    Returns:
        Reranked and truncated results
    """
    if not rerank_config.get("enabled", False):
        return hits
    
    provider = rerank_config.get("provider", "none")
    top_k_in = rerank_config.get("top_k_in", 50)
    top_k_out = rerank_config.get("top_k_out", 10)
    
    # Take top candidates
    candidates = hits[:top_k_in]
    
    # Extract text for reranking
    documents = [hit.get("text", hit.get("snippet", "")) for hit in candidates]
    
    # Initialize reranker
    reranker = RerankService(
        provider=provider,
        api_url=os.getenv("RERANK_API_URL"),
        api_key=os.getenv("RERANK_API_KEY")
    )
    
    # Get reranked indices and scores
    reranked_indices = await reranker.rerank(query, documents, top_k_out)
    
    # Build reranked results
    reranked_hits = []
    for idx, score in reranked_indices:
        hit = candidates[idx].copy()
        hit["rerank_score"] = score
        hit["original_rank"] = idx
        reranked_hits.append(hit)
    
    return reranked_hits
```

## Rerank API Request/Response Format

**Standard format (works with Cohere, Jina, custom endpoints)**

**Request:**
```json
{
  "query": "what did kandinsky believe about color?",
  "documents": [
    "Kandinsky viewed color as having spiritual properties...",
    "The artist believed that colors could evoke emotions...",
    "In his treatise, he described the psychological impact..."
  ],
  "top_k": 10,
  "return_documents": false
}
```

**Response (Cohere-style):**
```json
{
  "results": [
    {"index": 0, "relevance_score": 0.954},
    {"index": 2, "relevance_score": 0.891},
    {"index": 1, "relevance_score": 0.823}
  ]
}
```

**Response (Generic):**
```json
{
  "scores": [0.954, 0.823, 0.891]
}
```

The reranker normalizes both formats internally.

---

# Evaluation & Gates Implementation

**Automated quality gates for embedder/retrieval upgrades**

Eval runs golden query sets and blocks deploys if metrics regress.

## Golden Query Format

**File**: `manifests/<container_id>/eval.json`

```json
{
  "queries": [
    {
      "id": "q1",
      "query": "what did kandinsky believe about color?",
      "expect_docs": ["doc-uuid-1", "doc-uuid-2"],
      "expect_keywords": ["kandinsky", "spiritual", "color"],
      "min_score": 0.7
    },
    {
      "id": "q2",
      "query": "define expressionism vs impressionism",
      "expect_docs": ["doc-uuid-3"],
      "expect_keywords": ["expressionism", "impressionism", "movement"],
      "min_score": 0.65
    }
  ],
  "thresholds": {
    "ndcg@10": 0.75,
    "recall@20": 0.85,
    "p95_latency_ms": 200
  }
}
```

## Eval Runner

**Implementation** (`scripts/eval_container.py`):

```python
import json
import sys
from pathlib import Path
from statistics import mean
from dataclasses import dataclass
import httpx

@dataclass
class EvalResult:
    query_id: str
    ndcg: float
    recall: float
    latency_ms: float
    passed: bool

def compute_ndcg(results: list, expected: list, k: int = 10) -> float:
    """Compute Normalized Discounted Cumulative Gain"""
    dcg = 0.0
    for i, result in enumerate(results[:k]):
        if result["doc_id"] in expected:
            # Relevance = 1 if in expected, 0 otherwise
            rel = 1.0
            dcg += rel / math.log2(i + 2)  # +2 because rank starts at 1
    
    # Ideal DCG (all expected docs at top)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(expected), k)))
    
    return dcg / idcg if idcg > 0 else 0.0

def compute_recall(results: list, expected: list, k: int = 20) -> float:
    """Compute Recall@K"""
    retrieved = {r["doc_id"] for r in results[:k]}
    relevant = set(expected)
    
    if not relevant:
        return 0.0
    
    return len(retrieved & relevant) / len(relevant)

async def run_eval_query(query_spec: dict, container_id: str, mcp_token: str) -> EvalResult:
    """Run a single eval query and compute metrics"""
    import time
    
    url = "http://localhost:7801/v1/containers/search"
    headers = {"Authorization": f"Bearer {mcp_token}"}
    payload = {
        "containers": [container_id],
        "query": query_spec["query"],
        "mode": "hybrid",
        "top_k": 20
    }
    
    start = time.time()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
    
    latency_ms = (time.time() - start) * 1000
    
    results = response.json()["hits"]
    
    # Compute metrics
    ndcg = compute_ndcg(results, query_spec["expect_docs"], k=10)
    recall = compute_recall(results, query_spec["expect_docs"], k=20)
    
    # Check pass/fail
    min_score = query_spec.get("min_score", 0.0)
    passed = ndcg >= min_score and recall >= 0.5
    
    return EvalResult(
        query_id=query_spec["id"],
        ndcg=ndcg,
        recall=recall,
        latency_ms=latency_ms,
        passed=passed
    )

async def eval_container(container_id: str, mcp_token: str) -> bool:
    """
    Run full eval suite for a container
    
    Returns:
        True if all gates pass, False otherwise
    """
    # Load golden queries
    eval_file = Path(f"manifests/{container_id}/eval.json")
    if not eval_file.exists():
        print(f"No eval file found: {eval_file}")
        return True  # No eval = pass
    
    with open(eval_file) as f:
        eval_spec = json.load(f)
    
    # Run all queries
    results = []
    for query_spec in eval_spec["queries"]:
        result = await run_eval_query(query_spec, container_id, mcp_token)
        results.append(result)
        
        status = "✓" if result.passed else "✗"
        print(f"{status} {result.query_id}: nDCG={result.ndcg:.3f} Recall={result.recall:.3f} Latency={result.latency_ms:.0f}ms")
    
    # Aggregate metrics
    avg_ndcg = mean(r.ndcg for r in results)
    avg_recall = mean(r.recall for r in results)
    p95_latency = sorted(r.latency_ms for r in results)[int(len(results) * 0.95)]
    
    thresholds = eval_spec.get("thresholds", {})
    
    # Check gates
    gates_passed = True
    
    if avg_ndcg < thresholds.get("ndcg@10", 0.0):
        print(f"❌ GATE FAILED: nDCG@10 = {avg_ndcg:.3f} < {thresholds['ndcg@10']}")
        gates_passed = False
    
    if avg_recall < thresholds.get("recall@20", 0.0):
        print(f"❌ GATE FAILED: Recall@20 = {avg_recall:.3f} < {thresholds['recall@20']}")
        gates_passed = False
    
    if p95_latency > thresholds.get("p95_latency_ms", float('inf')):
        print(f"❌ GATE FAILED: P95 latency = {p95_latency:.0f}ms > {thresholds['p95_latency_ms']}ms")
        gates_passed = False
    
    # Load previous results and check regression
    prev_results_file = Path(f"manifests/{container_id}/eval_last_run.json")
    if prev_results_file.exists():
        with open(prev_results_file) as f:
            prev = json.load(f)
        
        ndcg_drop = (prev["avg_ndcg"] - avg_ndcg) / prev["avg_ndcg"]
        latency_increase = (p95_latency - prev["p95_latency"]) / prev["p95_latency"]
        
        if ndcg_drop > 0.02:  # 2% drop
            print(f"❌ REGRESSION: nDCG dropped {ndcg_drop*100:.1f}%")
            gates_passed = False
        
        if latency_increase > 0.20:  # 20% slower
            print(f"❌ REGRESSION: Latency increased {latency_increase*100:.1f}%")
            gates_passed = False
    
    # Save current results
    current_results = {
        "avg_ndcg": avg_ndcg,
        "avg_recall": avg_recall,
        "p95_latency": p95_latency,
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(prev_results_file, "w") as f:
        json.dump(current_results, f, indent=2)
    
    if gates_passed:
        print(f"✅ All eval gates passed for {container_id}")
    else:
        print(f"❌ Eval gates FAILED for {container_id}")
    
    return gates_passed

if __name__ == "__main__":
    import asyncio
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python eval_container.py <container_id>")
        sys.exit(1)
    
    container_id = sys.argv[1]
    mcp_token = os.getenv("MCP_TOKEN")
    
    passed = asyncio.run(eval_container(container_id, mcp_token))
    sys.exit(0 if passed else 1)
```

## Usage in CI/CD

```bash
# Before deploying embedder upgrade
export MCP_TOKEN="$LLC_MCP_TOKEN"
python scripts/eval_container.py expressionist-art

if [ $? -ne 0 ]; then
  echo "Eval gates failed - blocking deployment"
  exit 1
fi
```

---

# CLI Script Implementations

**Concrete implementations for all CLI tools**

## `scripts/create_container.py`

```python
#!/usr/bin/env python3
import sys
import uuid
import yaml
from pathlib import Path

def create_container(name: str, theme: str, modalities: list[str]):
    """Generate a new container manifest"""
    
    container_id = name.lower().replace(" ", "-")
    
    manifest = {
        "id": container_id,
        "name": name,
        "theme": theme,
        "modalities": modalities,
        "embedder": "nomic-embed-multimodal-7b",
        "embedder_version": "1.0.0",
        "dims": 1408,
        "retrieval": {
            "mode_default": "hybrid",
            "fusion": {"method": "rrf"},
            "freshness": {"enabled": True, "decay_lambda": 0.02},
            "rerank": {"enabled": False, "top_k_in": 50, "top_k_out": 10},
            "debug": {"return_diagnostics": True}
        },
        "chunker": {
            "mode": "semantic_then_fallback",
            "size": 600,
            "overlap": 0.12
        },
        "pdf": {
            "render_dpi": 150,
            "max_pages": 1000
        },
        "image": {
            "thumbnail_max_edge": 2048,
            "compress_quality": 90
        },
        "web": {
            "javascript": False,
            "sanitize_rules": ["strip_nav", "strip_ads"]
        },
        "dedup": {
            "semantic_threshold": 0.92
        },
        "storage": {
            "blobs": {"bucket": f"latent-{container_id}"}
        },
        "eval": {
            "enabled": True,
            "metrics": ["ndcg@10", "recall@20", "latency"]
        },
        "display": {
            "sort": "score_then_freshness",
            "snippet_template": "{title} — {snippet}",
            "max_snippet_chars": 320
        },
        "acl": {
            "roles": {
                "owner": ["local:you"],
                "reader": ["agent:claude", "agent:chatgpt", "agent:local"]
            }
        }
    }
    
    # Write manifest
    manifest_path = Path(f"manifests/{container_id}.yaml")
    manifest_path.parent.mkdir(exist_ok=True)
    
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    
    print(f"✓ Created manifest: {manifest_path}")
    
    # Create eval template
    eval_path = Path(f"manifests/{container_id}/eval.json")
    eval_path.parent.mkdir(exist_ok=True, parents=True)
    
    eval_template = {
        "queries": [],
        "thresholds": {
            "ndcg@10": 0.75,
            "recall@20": 0.85,
            "p95_latency_ms": 200
        }
    }
    
    with open(eval_path, "w") as f:
        json.dump(eval_template, f, indent=2)
    
    print(f"✓ Created eval template: {eval_path}")
    print(f"\nNext steps:")
    print(f"1. Edit {manifest_path} to customize settings")
    print(f"2. Add eval queries to {eval_path}")
    print(f"3. Restart MCP server to load the new container")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a new container")
    parser.add_argument("name", help="Container name")
    parser.add_argument("--theme", required=True, help="Theme (e.g., art, science)")
    parser.add_argument("--modalities", required=True, help="Comma-separated modalities (e.g., text,image)")
    
    args = parser.parse_args()
    
    modalities = [m.strip() for m in args.modalities.split(",")]
    create_container(args.name, args.theme, modalities)
```

## `scripts/search.py`

```python
#!/usr/bin/env python3
import sys
import os
import json
import httpx

def search(query: str, containers: list[str], mode: str = "hybrid", top_k: int = 10):
    """Search containers via MCP API"""
    
    token = os.getenv("MCP_TOKEN")
    if not token:
        print("Error: MCP_TOKEN not set")
        sys.exit(1)
    
    url = "http://localhost:7801/v1/containers/search"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "containers": containers,
        "query": query,
        "mode": mode,
        "top_k": top_k,
        "dedup": True
    }
    
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n🔍 Query: {query}")
        print(f"📦 Containers: {', '.join(containers)}")
        print(f"🎯 Mode: {mode}")
        print(f"\n{'='*80}\n")
        
        for i, hit in enumerate(data["hits"], 1):
            print(f"{i}. [{hit['container_id']}] {hit.get('rendered_snippet', hit.get('snippet', ''))}")
            print(f"   Score: {hit['score']:.3f} | Doc: {hit['doc_id'][:8]}... | {hit['modality']}")
            if "freshness_factor" in hit:
                print(f"   Freshness: {hit['freshness_factor']:.2f}")
            print()
        
        if "diagnostics" in data:
            diag = data["diagnostics"]
            print(f"\n⏱️  Timings: {json.dumps(diag.get('timings_ms', {}), indent=2)}")
        
    except httpx.HTTPError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Search containers")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--containers", required=True, help="Comma-separated container IDs")
    parser.add_argument("--mode", default="hybrid", choices=["semantic", "hybrid", "rerank"])
    parser.add_argument("--k", type=int, default=10, help="Number of results")
    
    args = parser.parse_args()
    
    containers = [c.strip() for c in args.containers.split(",")]
    search(args.query, containers, args.mode, args.k)
```

---

# Error Handling Patterns

**Graceful degradation and structured error responses**

## Error Response Structure

All endpoints return consistent error format:

```python
from fastapi import HTTPException
from pydantic import BaseModel
from enum import Enum

class IssueCode(str, Enum):
    AUTH = "AUTH"
    TIMEOUT = "TIMEOUT"
    NO_HITS = "NO_HITS"
    RATE_LIMIT = "RATE_LIMIT"
    POLICY = "POLICY"
    INGEST_FAIL = "INGEST_FAIL"

class Issue(BaseModel):
    code: IssueCode
    message: str
    details: dict = {}

class BaseResponse(BaseModel):
    request_id: str
    version: str = "v1"
    partial: bool = False
    timings: dict = {}
    issues: list[Issue] = []
```

## Timeout Handling with Partial Results

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def timeout_with_partial(timeout_sec: float, operation_name: str):
    """
    Context manager that allows returning partial results on timeout
    """
    try:
        async with asyncio.timeout(timeout_sec):
            yield {"partial": False, "issues": []}
    except asyncio.TimeoutError:
        yield {
            "partial": True,
            "issues": [Issue(
                code=IssueCode.TIMEOUT,
                message=f"{operation_name} exceeded {timeout_sec}s timeout"
            )]
        }

# Usage in search endpoint
@router.post("/v1/containers/search")
async def search(request: SearchRequest):
    all_hits = []
    all_issues = []
    partial = False
    
    for container_id in request.containers:
        async with timeout_with_partial(1.2, f"vector search in {container_id}") as ctx:
            try:
                hits = await perform_search(container_id, request.query)
                all_hits.extend(hits)
            except Exception as e:
                logger.error(f"Search failed in {container_id}: {e}")
                all_issues.append(Issue(
                    code=IssueCode.TIMEOUT,
                    message=f"Search failed in {container_id}",
                    details={"error": str(e)}
                ))
                partial = True
        
        if ctx["partial"]:
            partial = True
            all_issues.extend(ctx["issues"])
    
    return SearchResponse(
        hits=all_hits,
        partial=partial,
        issues=all_issues
    )
```

## Rate Limit Handling

```python
from fastapi import HTTPException, status

class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )

# In Nomic adapter
class NomicEmbed:
    def embed_text(self, texts: list[str]) -> np.ndarray:
        if not self.rate_limiter.consume(len(texts)):
            raise RateLimitExceeded(retry_after=60)
        
        # ... proceed with embedding
```

---

# Logging Schema

**Structured JSON logging for observability**

## Log Configuration

**Implementation** (`mcp-server/app/core/logging.py`):

```python
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(level: str = "INFO"):
    """Configure structured JSON logging"""
    
    logger = logging.getLogger()
    logger.setLevel(level)
    
    handler = logging.StreamHandler(sys.stdout)
    
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "name": "logger",
            "levelname": "level",
            "message": "msg"
        }
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Usage in endpoints
logger = logging.getLogger(__name__)

@router.post("/v1/containers/search")
async def search(request: SearchRequest):
    logger.info(
        "search_started",
        extra={
            "containers": request.containers,
            "query_length": len(request.query),
            "mode": request.mode,
            "top_k": request.top_k
        }
    )
    
    # ... perform search ...
    
    logger.info(
        "search_completed",
        extra={
            "containers": request.containers,
            "hits": len(hits),
            "latency_ms": latency,
            "partial": partial
        }
    )
```

## Log Examples

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "logger": "app.api.containers",
  "level": "info",
  "msg": "search_completed",
  "containers": ["expressionist-art"],
  "hits": 8,
  "latency_ms": 142,
  "partial": false
}
```

```json
{
  "timestamp": "2025-01-15T10:31:12.456Z",
  "logger": "workers.jobs.ingest",
  "level": "error",
  "msg": "ingestion_failed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "container_id": "quantum-mechanics",
  "error": "Nomic API rate limit exceeded",
  "retry_count": 2
}
```

---

# Healthcheck Implementations

**Service health monitoring**

## MCP Server Healthcheck

**Implementation** (`mcp-server/app/api/health.py`):

```python
from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    services: dict

@router.get("/healthz")
async def healthz():
    """Simple liveness check"""
    return {"status": "ok"}

@router.get("/readyz")
async def readyz():
    """Readiness check - verify all dependencies"""
    
    services = {}
    healthy = True
    
    # Check Postgres
    try:
        await check_postgres()
        services["postgres"] = "ok"
    except Exception as e:
        services["postgres"] = f"error: {e}"
        healthy = False
    
    # Check Qdrant
    try:
        await check_qdrant()
        services["qdrant"] = "ok"
    except Exception as e:
        services["qdrant"] = f"error: {e}"
        healthy = False
    
    # Check MinIO
    try:
        await check_minio()
        services["minio"] = "ok"
    except Exception as e:
        services["minio"] = f"error: {e}"
        healthy = False
    
    status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return HealthResponse(
        status="ok" if healthy else "degraded",
        services=services
    ), status_code
```

## Docker Compose Healthchecks

```yaml
services:
  qdrant:
    # ... other config ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
  
  postgres:
    # ... other config ...
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U local -d registry"]
      interval: 10s
      timeout: 5s
      retries: 3
  
  minio:
    # ... other config ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3
  
  mcp:
    # ... other config ...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7801/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
    depends_on:
      qdrant:
        condition: service_healthy
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
```

## Worker Heartbeat

```python
# workers/jobs/worker.py
import time
import logging

logger = logging.getLogger(__name__)

def worker_loop():
    last_heartbeat = time.time()
    
    while True:
        # Emit heartbeat every 30s
        if time.time() - last_heartbeat > 30:
            logger.info("worker_heartbeat", extra={"status": "alive"})
            last_heartbeat = time.time()
        
        # ... process jobs ...
```

---

# Design Ethos (Non-negotiable)

- **Simplicity is clarity earned.** Keep defaults sensible; complexity behind flags.
- **Provenance is truth.** Every vector carries its lineage.
- **Containers are living rooms, not bins.** Curate themes with intention.
- **Make it inevitable.** Each flow should feel like it could not be any other way.

---

# Agent‑Buildable Spec Pack (No Guesswork Left)

## 1) .env.example (root)

```
NOMIC_API_KEY=replace_me
REG_DB_DSN=postgresql://local:localpw@postgres:5432/registry
QDRANT_URL=http://qdrant:6333
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=localminio
MINIO_SECRET_KEY=localminio123
MCP_BIND=0.0.0.0
MCP_PORT=7801
EMBED_RATE_LIMIT_PER_MIN=120
RERANK_PROVIDER=none   # none|api
RERANK_API_URL=
RERANK_API_KEY=

```

## 2) Dockerfiles

**mcp-server/Dockerfile**

```
FROM python:3.11-slim
WORKDIR /app
COPY mcp-server/requirements.txt .
RUN pip install -r requirements.txt
COPY mcp-server/ .
EXPOSE 7801
CMD ["python","-m","app.main"]

```

**workers/Dockerfile**

```
FROM python:3.11-slim
WORKDIR /app
COPY workers/requirements.txt .
RUN pip install -r requirements.txt
COPY workers/ .
CMD ["python","-m","jobs.worker"]

```

**mcp-server/requirements.txt** (minimal)

```
fastapi==0.115.5
uvicorn[standard]==0.32.0
pydantic==2.9.2
httpx==0.27.2
qdrant-client==1.9.2
psycopg2-binary==2.9.9
minio==7.2.7
python-json-logger==2.0.7
orjson==3.10.7

```

**workers/requirements.txt**

```
pymupdf==1.24.10
trafilatura==1.9.0
readability-lxml==0.9.2
beautifulsoup4==4.12.3
requests==2.32.3
httpx==0.27.2
qdrant-client==1.9.2
psycopg2-binary==2.9.9
minio==7.2.7
orjson==3.10.7
python-slugify==8.0.4

```

## 3) OpenAPI — MCP HTTP surface (v1)

```
openapi: 3.1.0
info:
  title: MCP Containers API
  version: 1.0.0
servers:
  - url: http://localhost:7801
paths:
  /v1/containers/list:
    get:
      operationId: listContainers
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ListContainersResponse'
  /v1/containers/describe:
    get:
      parameters:
        - in: query
          name: container_id
          schema: {type: string}
          required: true
      responses:
        '200': {content: {application/json: {schema: {$ref: '#/components/schemas/DescribeResponse'}}}}
  /v1/containers/add:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema: {$ref: '#/components/schemas/AddRequest'}
      responses:
        '202': {content: {application/json: {schema: {$ref: '#/components/schemas/JobResponse'}}}}
  /v1/containers/search:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema: {$ref: '#/components/schemas/SearchRequest'}
      responses:
        '200': {content: {application/json: {schema: {$ref: '#/components/schemas/SearchResponse'}}}}
  /v1/admin/refresh:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema: {$ref: '#/components/schemas/RefreshRequest'}
      responses:
        '202': {content: {application/json: {schema: {$ref: '#/components/schemas/JobResponse'}}}}
  /v1/containers/export:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema: {$ref: '#/components/schemas/ExportRequest'}
      responses:
        '200': {content: {application/json: {schema: {$ref: '#/components/schemas/ExportResponse'}}}}
components:
  schemas:
    Issue:
      type: object
      properties:
        code: {type: string, enum: [AUTH, TIMEOUT, NO_HITS, RATE_LIMIT, POLICY, INGEST_FAIL]}
        message: {type: string}
    BaseResponse:
      type: object
      properties:
        request_id: {type: string}
        version: {type: string, const: 'v1'}
        partial: {type: boolean}
        timings: {type: object, additionalProperties: {type: number}}
        issues: {type: array, items: {$ref: '#/components/schemas/Issue'}}
    ListContainersResponse:
      allOf:
        - $ref: '#/components/schemas/BaseResponse'
        - type: object
          properties:
            containers:
              type: array
              items:
                type: object
                properties:
                  id: {type: string}
                  name: {type: string}
                  modalities: {type: array, items: {type: string}}
                  dims: {type: integer}
                  state: {type: string}
    DescribeResponse:
      allOf:
        - $ref: '#/components/schemas/BaseResponse'
        - type: object
          properties:
            manifest: {type: object}
            sizes: {type: object}
            last_ingest_at: {type: string, format: date-time}
    AddRequest:
      type: object
      required: [container_id]
      properties:
        container_id: {type: string}
        uri: {type: string}
        file_ref: {type: string}
        modality: {type: string, enum: [auto, text, image]}
    JobResponse:
      allOf:
        - $ref: '#/components/schemas/BaseResponse'
        - type: object
          properties:
            job_id: {type: string}
            status: {type: string}
    SearchRequest:
      type: object
      required: [containers, top_k]
      properties:
        containers: {type: array, items: {type: string}}
        query: {type: string}
        image_ref: {type: string}
        mode: {type: string, enum: [semantic, hybrid, multivector, crossmodal, rerank], default: hybrid}
        top_k: {type: integer, minimum: 1, maximum: 100}
        filters: {type: object}
        rerank_k: {type: integer, default: 50}
        dedup: {type: boolean, default: true}
    Hit:
      type: object
      properties:
        container_id: {type: string}
        doc_id: {type: string}
        chunk_id: {type: string}
        modality: {type: string}
        score: {type: number}
        title: {type: string}
        snippet: {type: string}
        uri: {type: string}
        offsets: {type: array, items: {type: integer}}
        timestamps: {type: array, items: {type: number}}
        provenance: {type: object}
        meta: {type: object}
    SearchResponse:
      allOf:
        - $ref: '#/components/schemas/BaseResponse'
      type: object
      properties:
        hits: {type: array, items: {$ref: '#/components/schemas/Hit'}}
        diagnostics: {type: object}
    RefreshRequest:
      type: object
      properties:
        container_id: {type: string}
        strategy: {type: string, enum: [parallel, inplace], default: parallel}
    ExportRequest:
      type: object
      properties:
        container_id: {type: string}
    ExportResponse:
      allOf:
        - $ref: '#/components/schemas/BaseResponse'
      type: object
      properties:
        url: {type: string}

```

## 4) Qdrant bootstrap (Python)

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

client = QdrantClient(url="http://qdrant:6333")

def ensure_collection(name: str, dim: int):
    if name not in [c.name for c in client.get_collections().collections]:
        client.create_collection(
            collection_name=name,
            vectors=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            hnsw_config=qm.HnswConfigDiff(m=32, ef_construct=256),
            optimizers_config=qm.OptimizersConfigDiff(default_segment_number=2),
        )

```

## 5) Postgres BM25 — `tsvector` trigger

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE FUNCTION chunks_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.tsv := to_tsvector('simple', unaccent(coalesce(NEW.text,'')));
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chunks_tsv ON chunks;
CREATE TRIGGER trg_chunks_tsv BEFORE INSERT OR UPDATE ON chunks
FOR EACH ROW EXECUTE FUNCTION chunks_tsv_update();

```

## 6) Nomic Embed adapter (HTTPX)

```python
import httpx, numpy as np

class NomicEmbed:
    def __init__(self, api_key: str, base_url: str = "https://api.nomic.ai/v1"):
        self.key = api_key
        self.base = base_url
        self.h = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def embed_text(self, texts: list[str]) -> np.ndarray:
        payload = {"model": "nomic-embed-multimodal-7b", "input": texts}
        r = httpx.post(f"{self.base}/embeddings", headers=self.h, json=payload, timeout=60)
        r.raise_for_status()
        vecs = [np.array(d["embedding"], dtype=np.float32) for d in r.json()["data"]]
        # L2 normalize for cosine
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return np.divide(vecs, np.maximum(norms, 1e-12))

```

## 7) MinIO pathing convention

```
s3://{bucket}/{doc_id}/
  original/{filename}
  thumbs/{basename}_2k.jpg
  pdf_pages/{page:04d}.png

```

## 8) Ingestion pseudocode (text/pdf/image)

```python
# TEXT/WEB
doc = fetch(url)
main = extract_main(doc)
chunks = chunk(main, size=600, overlap=0.12)
vecs = nomic.embed_text([c.text for c in chunks])
pg.insert_document(...); pg.insert_chunks(...); qdrant.upsert(...)

# PDF
text_pages, images = parse_pdf(file)
text_chunks = chunk(join(text_pages))
text_vecs = nomic.embed_text([c.text for c in text_chunks])
qdrant.upsert(text_vecs, payload=...)
for page_png in render_pages(file, dpi=150):
    v = nomic.embed_image(page_png)
    qdrant.upsert([v], payload=...)

# IMAGE
thumb = make_thumb(img)
vec = nomic.embed_image(img)
qdrant.upsert([vec], payload=...)

```

## 9) Rerank provider interface

```python
class Reranker:
    def score(self, query: str, candidates: list[str]) -> list[float]:
        return list(range(len(candidates)))  # default no-op stable order

```

## 10) Healthchecks

- MCP: `GET /healthz` → `{status:"ok"}`
- Workers: heartbeat log every 30s; queue depth metric
- Qdrant/Postgres/MinIO: compose `healthcheck:` with `CMD` pings

## 11) Makefile

```
up: ; docker compose up -d
stop: ; docker compose stop
logs: ; docker compose logs -f --tail=200 mcp workers qdrant postgres
ps: ; docker compose ps
shell-pg: ; docker exec -it $$(docker ps -qf name=postgres) psql -U local -d registry

```

## 12) Seed manifest + golden eval

`manifests/expressionist-art.yaml` (already provided) and `manifests/expressionist-art.eval.json`:

```json
{
  "queries": [
    {"q": "what did kandinsky believe about color?", "expect": ["kandinsky","spiritual in art"]},
    {"q": "define expressionism vs impressionism", "expect": ["expressionism","impressionism"]}
  ]
}

```

## 13) Error responses (examples)

```json
{
  "request_id": "9b1d...",
  "version": "v1",
  "partial": true,
  "issues": [{"code":"TIMEOUT","message":"vector search exceeded 1200ms in container expressionist-art"}]
}

```

---

**With this Spec Pack, an AI agent has zero ambiguities:** exact env, Dockerfiles, OpenAPI, DB triggers, Qdrant bootstrap, Nomic adapter, paths, ingestion flow, health, and errors. If you want, we can generate stub code files next, matching these contracts 1:1.
