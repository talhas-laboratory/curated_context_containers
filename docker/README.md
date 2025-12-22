# Local Compose Stack

`compose.local.yaml` boots the stack (Postgres, Qdrant, Neo4j, MinIO, MCP server, and workers). Example:

```bash
cd docker
NOMIC_API_KEY=sk-local docker compose -f compose.local.yaml up --build
```

Once running:
- MCP server health: http://localhost:7801/health
- Postgres: localhost:5432 (user `local`/`localpw`)
- Qdrant dashboard: http://localhost:6333
- MinIO console: http://localhost:9001 (localminio/localminio123)
- Neo4j: bolt://localhost:7687 (http://localhost:7474 browser, auth `neo4j/localneo4j`)

The compose file references the Postgres-backed job queue decision from ADR-001 and keeps the stack within MacBook Air resource limits.
