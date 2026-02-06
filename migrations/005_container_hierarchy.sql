-- Phase 3 (prework): container hierarchy support

ALTER TABLE containers
    ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES containers(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_containers_parent ON containers(parent_id);
