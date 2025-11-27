# Runbook — Local Setup & Baseline Checks

**Purpose:** Stand up the full MCP stack locally and validate baseline health (migrate, smoke, golden). Applies to fresh clones and CI runners alike.

---

## Prerequisites
- Tooling: Docker + docker-compose, Python 3.11, Node 18+, npm, psql client, curl.
- Secrets: `LLC_MCP_TOKEN` or `docker/mcp_token.txt`; optional `NOMIC_API_KEY` if you want real embeddings (falls back to zeros otherwise).
- Ports free: 5433 (Postgres), 6333/6334 (Qdrant), 9000/9001 (MinIO), 7801 (MCP API), 3000 (frontend).

## Environment
```bash
export LLC_POSTGRES_DSN=postgresql://local:localpw@localhost:5433/registry
export LLC_QDRANT_URL=http://localhost:6333
export LLC_MINIO_ENDPOINT=http://localhost:9000
export LLC_MINIO_ACCESS_KEY=localminio
export LLC_MINIO_SECRET_KEY=localminio123
# Optional for real embeddings
export NOMIC_API_KEY=...
```

## Bring up the stack
```bash
# From repo root
docker compose -f docker/compose.local.yaml up -d --build

# Bootstrap DB schema + seed container
./scripts/bootstrap_db.sh

# Health checks
curl -sf http://localhost:7801/health
psql "$LLC_POSTGRES_DSN" -c "SELECT COUNT(*) FROM containers;"
```

## Smoke test (ingest + search)
```bash
make smoke
```
Expected: hybrid search returns ≥1 result, dedup works (1 doc), embedding cache populated; script exits 0.

## Golden queries
```bash
./scripts/run_golden_queries.sh --budget-ms 900
# Output: .artifacts/golden_summary.json (fails if over budget or zero results)
```

## Frontend (optional)
```bash
cd frontend
npm install
NEXT_PUBLIC_MCP_BASE_URL=http://localhost:7801 NEXT_PUBLIC_MCP_TOKEN=local-dev-token npm run dev
# Visit http://localhost:3000/containers/expressionist-art/search
```

## Cleanup
```bash
docker compose -f docker/compose.local.yaml down -v
```
