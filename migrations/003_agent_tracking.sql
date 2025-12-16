-- Add agent tracking and container lifecycle fields

-- Add fields to containers table
ALTER TABLE containers
    ADD COLUMN IF NOT EXISTS created_by_agent TEXT,
    ADD COLUMN IF NOT EXISTS mission_context TEXT,
    ADD COLUMN IF NOT EXISTS auto_refresh BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'private',
    ADD COLUMN IF NOT EXISTS collaboration_policy TEXT NOT NULL DEFAULT 'read-only';

COMMENT ON COLUMN containers.created_by_agent IS 'Agent ID that created this container';
COMMENT ON COLUMN containers.mission_context IS 'Mission context or purpose for this container';
COMMENT ON COLUMN containers.auto_refresh IS 'Whether to auto-refresh from manifests';
COMMENT ON COLUMN containers.visibility IS 'Visibility level: private, team, or public';
COMMENT ON COLUMN containers.collaboration_policy IS 'Collaboration policy: contribute or read-only';

-- Create agent_sessions table for tracking agent activity
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    agent_name TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent_id ON agent_sessions(agent_id);

COMMENT ON TABLE agent_sessions IS 'Tracks active agent sessions and their activity';

-- Create container_links table for multi-agent collaboration
CREATE TABLE IF NOT EXISTS container_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    target_container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_container_links_source ON container_links(source_container_id);
CREATE INDEX IF NOT EXISTS idx_container_links_target ON container_links(target_container_id);

COMMENT ON TABLE container_links IS 'Links between containers for multi-agent collaboration';

-- Create container_subscriptions table for event notifications
CREATE TABLE IF NOT EXISTS container_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    container_id UUID NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    webhook_url TEXT,
    events TEXT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_notified TIMESTAMPTZ,
    UNIQUE(container_id, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_container_subscriptions_container ON container_subscriptions(container_id);
CREATE INDEX IF NOT EXISTS idx_container_subscriptions_agent ON container_subscriptions(agent_id);

COMMENT ON TABLE container_subscriptions IS 'Agent subscriptions to container events';
