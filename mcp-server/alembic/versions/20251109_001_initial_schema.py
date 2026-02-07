"""Initial schema bootstrap.

NOTE: This revision embeds the SQL so it can run inside Docker images where the
repo-root `migrations/` directory may not exist in the build context.
"""
from __future__ import annotations

from alembic import op

revision = "20251109_001"
down_revision = None
branch_labels = None
depends_on = None


INITIAL_SCHEMA_SQL = r"""
-- Phase 1 canonical schema derived from single_source_of_truth/architecture/DATA_MODEL.md

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enum types
do $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'container_state') THEN
        CREATE TYPE container_state AS ENUM ('active','paused','archived');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_kind') THEN
        CREATE TYPE job_kind AS ENUM ('ingest','refresh','export');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
        CREATE TYPE job_status AS ENUM ('queued','running','done','failed');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'modality') THEN
        CREATE TYPE modality AS ENUM ('text','pdf','image','web');
    END IF;
END$$;

-- Utility function to bump updated_at
CREATE OR REPLACE FUNCTION set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- containers table
CREATE TABLE IF NOT EXISTS containers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE CHECK (name ~ '^[a-z0-9_-]+$'),
    theme TEXT NOT NULL,
    description TEXT,
    modalities modality[] NOT NULL CHECK (array_length(modalities, 1) > 0),
    embedder TEXT NOT NULL,
    embedder_version TEXT NOT NULL,
    dims INT NOT NULL CHECK (dims > 0),
    policy JSONB NOT NULL,
    acl JSONB NOT NULL DEFAULT '{}',
    state container_state NOT NULL DEFAULT 'active',
    stats JSONB NOT NULL DEFAULT jsonb_build_object('document_count',0,'chunk_count',0,'size_mb',0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_containers_state ON containers(state);
CREATE INDEX IF NOT EXISTS idx_containers_theme ON containers(theme);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_containers_updated' AND tgrelid = 'containers'::regclass
    ) THEN
        CREATE TRIGGER trg_containers_updated
            BEFORE UPDATE ON containers
            FOR EACH ROW EXECUTE FUNCTION set_timestamp();
    END IF;
END;
$$;

-- container_versions
CREATE TABLE IF NOT EXISTS container_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    manifest JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_container_versions_container ON container_versions(container_id);

-- documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    uri TEXT,
    mime TEXT NOT NULL,
    hash TEXT NOT NULL,
    title TEXT,
    size_bytes BIGINT,
    meta JSONB,
    state TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(container_id, hash)
);
CREATE INDEX IF NOT EXISTS idx_documents_container ON documents(container_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_documents_updated' AND tgrelid = 'documents'::regclass
    ) THEN
        CREATE TRIGGER trg_documents_updated
            BEFORE UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION set_timestamp();
    END IF;
END;
$$;

-- chunks
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    modality modality NOT NULL,
    text TEXT,
    offsets INT4RANGE,
    tsrange TSRANGE,
    provenance JSONB NOT NULL,
    meta JSONB,
    embedding_version TEXT NOT NULL,
    dedup_of UUID REFERENCES chunks(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tsv TSVECTOR
);
CREATE INDEX IF NOT EXISTS idx_chunks_container ON chunks(container_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_modality ON chunks(modality);
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON chunks USING GIN(tsv);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_chunks_updated' AND tgrelid = 'chunks'::regclass
    ) THEN
        CREATE TRIGGER trg_chunks_updated
            BEFORE UPDATE ON chunks
            FOR EACH ROW EXECUTE FUNCTION set_timestamp();
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION chunks_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.tsv := setweight(to_tsvector('english', coalesce(unaccent(NEW.text),'')), 'A');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_chunks_tsv' AND tgrelid = 'chunks'::regclass
    ) THEN
        CREATE TRIGGER trg_chunks_tsv
            BEFORE INSERT OR UPDATE ON chunks
            FOR EACH ROW EXECUTE FUNCTION chunks_tsv_update();
    END IF;
END;
$$;

-- jobs
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind job_kind NOT NULL,
    status job_status NOT NULL DEFAULT 'queued',
    container_id UUID REFERENCES containers(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,
    error TEXT,
    retries INT NOT NULL DEFAULT 0,
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_container ON jobs(container_id);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_jobs_updated' AND tgrelid = 'jobs'::regclass
    ) THEN
        CREATE TRIGGER trg_jobs_updated
            BEFORE UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION set_timestamp();
    END IF;
END;
$$;

-- job events
CREATE TABLE IF NOT EXISTS job_events (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status job_status NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);

-- embedding cache
CREATE TABLE IF NOT EXISTS embedding_cache (
    cache_key TEXT PRIMARY KEY,
    modality modality NOT NULL,
    dims INT NOT NULL,
    vector BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_embedding_cache_last_used ON embedding_cache(last_used_at);

-- diagnostics
CREATE TABLE IF NOT EXISTS diagnostics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_diagnostics_endpoint ON diagnostics(endpoint);

-- helper view for search convenience (materialized via refresh)
CREATE OR REPLACE VIEW chunks_search_view AS
SELECT
    c.id AS chunk_id,
    c.container_id,
    c.doc_id,
    c.modality,
    c.text,
    c.tsv,
    c.dedup_of,
    c.meta,
    c.provenance,
    d.title,
    d.uri,
    d.meta AS document_meta
FROM chunks c
JOIN documents d ON d.id = c.doc_id
WHERE d.state = 'active';
"""


def upgrade() -> None:
    op.execute(INITIAL_SCHEMA_SQL)


def downgrade() -> None:
    raise RuntimeError("Downgrades are not supported for the initial schema")
