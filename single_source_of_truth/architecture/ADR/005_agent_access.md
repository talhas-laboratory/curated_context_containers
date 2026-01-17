# ADR-005: Agent Access and Multi-Agent Collaboration

**Status:** Accepted  
**Date:** 2025-11-27  
**Authors:** Silent Architect, Orchestrator  
**Supersedes:** N/A

## Context

Local Latent Containers was initially designed for human users accessing curated context via a web UI. However, AI agents represent a powerful use case: they can autonomously search, curate, and collaborate using containers as shared knowledge bases. This ADR documents the architecture for agent access and multi-agent collaboration patterns.

## Decision

We will expose LLC as an **agent-accessible platform** with three access patterns:

1. **MCP Gateway** - MCP protocol server for interactive agents (Claude Desktop, Cursor)
2. **Python SDK** - Programmatic library for autonomous agents
3. **Framework Integrations** - LangChain and LlamaIndex retriever implementations

Additionally, we extend the backend with:
- **Container Lifecycle API** - Agents can create/update/delete containers
- **Agent Tracking** - Track agent identity and activity
- **Collaboration Features** - Links, subscriptions, and shared container registries

## Architecture

### MCP Gateway

```
┌─────────────────┐
│  Claude Desktop │ (or Cursor, custom agent)
└────────┬────────┘
         │ MCP Protocol (stdio)
         ▼
┌─────────────────┐
│  MCP Gateway    │ (Python, mcp-server-gateway/)
│  - Tool defs    │
│  - Validation   │
│  - Mapping      │
└────────┬────────┘
         │ HTTP/JSON + Bearer token
         ▼
┌─────────────────┐
│  LLC Backend    │ (FastAPI on :7801)
└─────────────────┘
```

**Tools exposed:**
- `containers_list` - Discover containers
- `containers_describe` - Get container details
- `containers_search` - Semantic search
- `containers_add` - Add sources
- `jobs_status` - Monitor ingestion

### Python SDK

```python
from llc_agents import ContainerClient, AgentSession

session = AgentSession(
    agent_id="research-bot-001",
    token="..."
)

client = ContainerClient(session)
results = await client.search(
    query="expressionist color theory",
    containers=["expressionist-art"]
)
```

**Key classes:**
- `AgentSession` - Auth + HTTP session management
- `ContainerClient` - High-level API wrapper
- `SearchBuilder` - Fluent query builder

### Backend Extensions

#### 1. Container Lifecycle API

New endpoints for agent-driven container management:

- `POST /v1/containers/create` - Create container
- `PATCH /v1/containers/{id}/update` - Update metadata
- `DELETE /v1/containers/{id}` - Archive/delete container

Containers gain agent-tracking fields:
- `created_by_agent` - Agent identity
- `mission_context` - Why this container exists
- `visibility` - private/team/public
- `collaboration_policy` - read-only/contribute
- `auto_refresh` - Auto-update policy

#### 2. Agent Tracking

Middleware captures agent identity from request headers:
- `X-Agent-ID` - Unique agent identifier
- `X-Agent-Name` - Human-readable name

New table: `agent_sessions`
- Tracks when agents first seen, last active
- Enables observability and metrics per agent

#### 3. Collaboration Features

**Container Links:**
```
POST /v1/collaboration/link
{
  "source_container": "expressionist-art",
  "target_container": "bauhaus-design",
  "relationship": "influenced_by"
}
```

Enables knowledge graph navigation across containers.

**Container Subscriptions:**
```
POST /v1/collaboration/subscribe
{
  "container": "expressionist-art",
  "events": ["source_added"],
  "webhook_url": "https://agent.example.com/webhook"
}
```

Agents get notified of container changes.

**Shared Registry:**
Extended `containers.list` with:
- `created_by_agent` filter
- `visibility` field
- `collaboration_policy` field

## Consequences

### Positive

1. **Zero-Code Access** - Claude Desktop users can immediately leverage containers via MCP
2. **Programmatic Control** - Python SDK enables sophisticated autonomous agents
3. **Framework Integration** - Easy to use with LangChain/LlamaIndex RAG pipelines
4. **Multi-Agent Collaboration** - Agents can discover, share, and coordinate via containers
5. **Observability** - Agent tracking provides visibility into agent activity
6. **Extensibility** - Clear patterns for adding more agent capabilities

### Negative

1. **Complexity** - Three access patterns increases surface area
2. **Migration Burden** - Database migration required for agent tracking
3. **MCP Maintenance** - MCP protocol changes may require gateway updates
4. **Authentication** - Agents need token management (not currently automated)
5. **Rate Limiting** - May need per-agent rate limits (not yet implemented)

### Neutral

1. **Backward Compatibility** - Existing UI and API remain unchanged
2. **Optional Features** - Agents can use basic search without lifecycle/collaboration APIs
3. **Performance** - Agent tracking middleware adds minimal latency (<5ms)

## Implementation

### Phase 1: MCP Gateway ✅
- [x] Standalone MCP server exposing API as tools
- [x] Tool descriptors for all v1 endpoints
- [x] Claude Desktop configuration example
- [x] README with setup guide

### Phase 2: Python SDK ✅
- [x] Core SDK (AgentSession, ContainerClient)
- [x] Async support
- [x] SearchBuilder fluent interface
- [x] Comprehensive README

### Phase 3: Framework Integrations ✅
- [x] LangChain retriever
- [x] LlamaIndex retriever
- [x] Example notebooks

### Phase 4: Backend Extensions ✅
- [x] Container lifecycle endpoints
- [x] Agent tracking middleware
- [x] Database migration (agent_sessions, container fields)

### Phase 5: Collaboration ✅
- [x] Container links API
- [x] Container subscriptions API
- [x] Shared registry extensions

### Phase 6: Documentation & Examples ✅
- [x] Agent Quickstart Guide
- [x] Research agent example
- [x] Curator agent example
- [x] Multi-agent collaboration demo

## Alternatives Considered

### 1. Direct Database Access

Agents could connect directly to PostgreSQL/Qdrant.

**Rejected because:**
- Breaks encapsulation
- No auth/validation
- Bypasses policy enforcement
- Tight coupling to schema

### 2. GraphQL API

Could expose GraphQL instead of REST for richer queries.

**Rejected because:**
- MCP protocol is REST-based
- Framework integrations expect REST
- Would require dual API maintenance

### 3. Agent-Specific Endpoints

Could create separate `/agent/*` endpoints.

**Rejected because:**
- Unnecessary duplication
- Existing REST API works fine
- Only need lifecycle extensions, not new search/retrieval

## References

- **MCP Specification:** https://modelcontextprotocol.io/
- **LangChain Retrievers:** https://python.langchain.com/docs/modules/data_connection/retrievers/
- **LlamaIndex:** https://docs.llamaindex.ai/en/stable/

## Related ADRs

- ADR-001: Postgres-native job queue
- ADR-002: Rerank execution strategy
- ADR-003: Embedding cache strategy

## Migration Path

### For Existing Users

No changes required. UI and existing API remain unchanged.

### For New Agent Users

1. Install MCP gateway or Python SDK
2. Get the MCP token from your environment or secrets store
3. Configure client/gateway with token
4. Start using tools/SDK

### Database Migration

Run Alembic migration:
```bash
cd mcp-server
alembic upgrade head
```

This adds:
- `agent_sessions` table
- Agent tracking fields to `containers`
- `container_links` table
- `container_subscriptions` table

## Metrics

We will measure success via:

1. **Adoption:** Number of unique agent IDs per week
2. **Usage:** Agent API calls per day
3. **Collaboration:** Container links and subscriptions created
4. **Performance:** P95 latency with agent tracking middleware (<5ms overhead)
5. **Quality:** Agent-created containers that are reused by other agents

## Security Considerations

1. **Authentication:** Agents use same bearer token as humans (future: agent-specific tokens)
2. **Authorization:** Agents respect container ACLs (future: agent-specific permissions)
3. **Rate Limiting:** Not yet implemented (future: per-agent quotas)
4. **Audit Trail:** Agent identity logged with all operations
5. **Visibility Control:** Containers can be private/team/public

## Future Enhancements

1. **Agent-Specific Tokens** - Generate tokens per agent, with revocation
2. **Agent Permissions** - Fine-grained ACLs (read-only agents, curator agents, etc.)
3. **Agent Marketplace** - Registry of shareable agent implementations
4. **WebSocket API** - Real-time updates for subscriptions
5. **Container Recommendations** - ML-based container discovery for missions
6. **Cross-Container Search** - Follow links during search
7. **Agent-to-Agent Messaging** - Direct coordination via LLC

## Conclusion

Agent access transforms LLC from a human-only tool into a **multi-agent collaboration platform**. The three-tier access pattern (MCP, SDK, frameworks) provides flexibility for different use cases, while lifecycle and collaboration APIs enable sophisticated multi-agent workflows.

This architecture positions LLC as infrastructure for **agentic systems** where autonomous agents curate, search, and collaborate on shared knowledge bases.






















