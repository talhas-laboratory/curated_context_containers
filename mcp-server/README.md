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
