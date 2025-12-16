-- Add graph-related fields to containers for Graph RAG

ALTER TABLE containers
    ADD COLUMN IF NOT EXISTS graph_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS graph_url TEXT,
    ADD COLUMN IF NOT EXISTS graph_schema JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN containers.graph_enabled IS 'Whether graph features are enabled for this container';
COMMENT ON COLUMN containers.graph_url IS 'External or override graph endpoint (defaults to local Neo4j)';
COMMENT ON COLUMN containers.graph_schema IS 'Optional schema/introspection cache for graph nodes/edges';
