# Migrations

Phase 1 exposes both the raw SQL migration (canonical contract) and an Alembic wrapper located in `mcp-server/alembic/`. Until full SQLAlchemy models exist we still apply the SQL directly, but the Alembic revision simply executes the same file so CI and local workflows stay aligned.

The current workflow is:

1. Export `LLC_POSTGRES_DSN` or pass explicit `psql` connection parameters.
2. Apply `001_initial_schema.sql` to bootstrap extensions, enum types, and tables.
3. Commit any follow-up migration files in numeric order (`002_*.sql`, `003_*.sql`, ...).

```bash
# Example (from repo root)
export LLC_POSTGRES_DSN="postgresql://local:localpw@localhost:5432/registry"
psql "$LLC_POSTGRES_DSN" -f migrations/001_initial_schema.sql
```

When richer migrations are needed, create new Alembic revisions that either call additional SQL files in this directory or use standard Alembic operations.
