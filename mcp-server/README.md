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

Alembic is configured under `alembic/` with an initial revision that executes the canonical SQL schema from `../migrations/001_initial_schema.sql`. Run migrations with:

```bash
cd mcp-server
LLC_POSTGRES_DSN=postgresql://local:localpw@localhost:5432/registry alembic upgrade head
```

The raw SQL migration remains the source of truth and is reused by Alembic to avoid duplication while we build out SQLAlchemy models.

Graph fields (Neo4j enablement) are added in `migrations/002_graph_fields.sql` and Alembic revision `20251205_001_graph_fields.py`. Apply both migrations in order before running graph modes.

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
