"""Migration orchestration for external systems.

Postgres remains the source of truth via Alembic.
Other subsystems (Qdrant/Neo4j) are best-effort and reported via system status.
"""

