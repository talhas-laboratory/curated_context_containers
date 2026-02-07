from __future__ import annotations

from typing import Any

from app.adapters.neo4j import neo4j_adapter


def run_neo4j_migrations() -> dict[str, Any]:
    """Best-effort Neo4j "migrations".

    Neo4j schema (constraints/indexes) can be added here over time as explicit
    steps. For now we validate connectivity.
    """
    ok = neo4j_adapter.healthcheck()
    if not ok:
        raise RuntimeError("neo4j_healthcheck_failed")
    return {"ok": True}

