# Production Readiness Build Plans (Non-Security/Auth)

Assumptions: single-host Docker Compose, moderate data sizes, no HA requirement.

## Automated DB Migrations (Prod)
1. [x] Add a one-shot `migrations` service in `docker/compose.prod.yaml` that runs `alembic upgrade head` on startup.
2. [x] Make `mcp` and `workers` depend on `migrations` completion (health or `condition: service_completed_successfully`).
3. [x] Update `docs/deployment_guide.md` to make migrations part of deploy flow.
4. [x] Add a CI check that ensures new migrations exist for model changes (e.g., enforce Alembic autogen diff is empty).
5. [x] Add a rollback playbook (e.g., `alembic downgrade -1`) and document constraints.
Acceptance criteria: `docker compose up -d` applies schema automatically; app starts cleanly on empty DB; new migrations are applied on deploy.

## Backups + Restore
1. [x] Define backup targets for Postgres, Qdrant, MinIO, Neo4j and where they live (e.g., `/srv/llc/backups`).
2. [x] Add scripts to create backups (pg_dump, Qdrant snapshot, MinIO bucket export, Neo4j dump).
3. [x] Add scripts to restore from backups (documented sequence and safety checks).
4. [x] Add a cron/automation entry (host-level or containerized) to run backups on schedule.
5. [x] Add retention policy and a quick verification check (list latest backup, optionally checksum).
Acceptance criteria: one command produces full backup set; restore steps work on a fresh host; scheduled backups exist with rotation.

## Observability (Logs, Metrics, Alerts)
1. [x] Choose minimal stack (e.g., Loki + Promtail + Grafana) or a hosted option.
2. [x] Add log shipping for `mcp`, `workers`, and core data services.
3. [x] Add basic metrics endpoints or exporters where available (Postgres, Neo4j, Qdrant, MinIO).
4. [x] Create a small dashboard: ingest rate, search latency, error rate, DB size, container health.
5. [x] Add alert rules for service down, error spikes, and backup failures.
Acceptance criteria: dashboards show live data; alerts fire on simulated failure; logs searchable by service.

## Image/Version Pinning
1. [x] Replace `:latest` tags with pinned versions for all services.
2. [x] Add image digest pinning for critical services if you want stronger immutability.
3. [x] Document how to update versions safely (test in staging, then prod).
4. [x] Add CI check to block `:latest` tags in compose.
Acceptance criteria: no `latest` tags in prod compose; rollbacks possible by pinning previous versions.

## Readiness/Health Checks
1. [x] Add health checks for `frontend` and `workers` (e.g., HTTP health endpoint or simple process checks).
2. [x] Ensure `reverse-proxy` depends on `frontend` being healthy, not just started.
3. [x] Add a lightweight readiness endpoint to MCP that validates DB/graph/vector storage connectivity.
4. [x] Add a deploy smoke check that verifies the full request path.
Acceptance criteria: compose waits for healthy services before routing; health checks fail when dependencies are down; smoke check passes after deploy.
