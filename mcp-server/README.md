# MCP Server

Deterministic FastAPI service exposing Model Context Protocol (MCP) tools for Local Latent Containers. This package hosts the HTTP API surface (`/v1/*`) and MCP manifest, orchestrates retrieval/ingestion services, and exposes observability endpoints.

## Layout

```
mcp-server/
├─ app/
│  ├─ main.py           # FastAPI application entrypoint
│  ├─ api/              # Routers per domain (containers, admin, health)
│  └─ core/             # Settings, logging, lifetime hooks
├─ pyproject.toml       # Build + dependency metadata
└─ Dockerfile           # Runtime image for docker compose
```

Implementation will grow vertically (services, adapters, models) as contracts from `single_source_of_truth/architecture/` are implemented.

## Database migrations

Alembic is configured under `alembic/`. Postgres migrations are **required** (the API will refuse to start if they fail).

By default the server attempts to run migrations on startup (`LLC_AUTO_MIGRATE=true`). You can disable this in some environments with `LLC_AUTO_MIGRATE=false` and run Alembic manually.

Run migrations with:

```bash
cd mcp-server
LLC_POSTGRES_DSN=postgresql://local:localpw@localhost:5432/registry alembic upgrade head
```

Startup visibility:
- `GET /ready` returns 503 when any dependency is down and includes a `migrations` report.
- `GET /v1/system/status` always returns 200 and is intended for UI/agents to display degraded-service state.

## Graph configuration

Graph RAG depends on Neo4j running (see `docker/compose.local.yaml`). Key env vars:

- `LLC_NEO4J_URI` (default `bolt://neo4j:7687`)
- `LLC_NEO4J_USER` / `LLC_NEO4J_PASSWORD`
- `LLC_GRAPH_MAX_HOPS_DEFAULT` (default 2)
- `LLC_GRAPH_QUERY_TIMEOUT_MS` (default 1200)
- `LLC_GRAPH_ENABLE_RAW_CYPHER` (default false; enable to allow `mode=cypher`)
- `LLC_GRAPH_NL2CYPHER_ENABLED` (default false; enable to call NL→Cypher model)
- `LLC_GRAPH_NL2CYPHER_URL` (required when enabled; POST endpoint for Qwen NL→Cypher)
- `LLC_GRAPH_NL2CYPHER_API_KEY` (optional bearer for the endpoint)
- `LLC_GRAPH_NL2CYPHER_TIMEOUT_MS` (default 12000)

Ensure manifests set `graph.enabled: true` for containers that should participate in graph modes.
