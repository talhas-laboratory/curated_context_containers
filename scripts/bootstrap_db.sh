#!/usr/bin/env bash
set -euo pipefail

SCHEMA_PATH="$(cd "$(dirname "$0")/.." && pwd)/migrations/001_initial_schema.sql"
DSN=${LLC_POSTGRES_DSN:-"postgresql://local:localpw@localhost:5433/registry"}

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required. Install PostgreSQL client tools first." >&2
  exit 1
fi

echo "Applying schema from $SCHEMA_PATH to $DSN"
psql "$DSN" -f "$SCHEMA_PATH"

psql "$DSN" <<'SQL'
TRUNCATE TABLE jobs, job_events, chunks, documents, embedding_cache, diagnostics RESTART IDENTITY;
DELETE FROM containers WHERE name = 'expressionist-art';
INSERT INTO containers (
    id, name, theme, description, modalities, embedder, embedder_version, dims,
    policy, acl, state, stats
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'expressionist-art',
    'German Expressionism',
    'Seed container for smoke tests',
    ARRAY['text','pdf','image']::modality[],
    'google-gemma3-text',
    '1.0.0',
    768,
    '{"privacy": "local_only", "diagnostics_enabled": true}'::jsonb,
    '{}'::jsonb,
    'active',
    '{"document_count":0,"chunk_count":0,"size_mb":0}'::jsonb
)
ON CONFLICT (name) DO NOTHING;
SQL
