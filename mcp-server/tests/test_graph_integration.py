"""Integration test for graph ingestion and search using Neo4j (requires services)."""
from __future__ import annotations

import os
import uuid

import pytest

from app.adapters.neo4j import neo4j_adapter
from app.models.graph import GraphSearchRequest
from app.services import graph as graph_service
from app.db.session import get_session

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://local:localpw@localhost:5432/registry")
NEO4J_URI = os.getenv("LLC_NEO4J_URI", "bolt://localhost:7687")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_ingest_and_search_end_to_end():
    if os.getenv("CI_INTEGRATION") == "0":
        pytest.skip("integration tests disabled via CI_INTEGRATION=0")

    # Quick service availability checks
    try:
        driver = neo4j_adapter.connect()
        with driver.session() as session:
            session.run("RETURN 1")
    except Exception as exc:  # pragma: no cover - network/service guard
        pytest.skip(f"Neo4j not reachable at {NEO4J_URI}: {exc}")

    # Build fake container context
    container_id = uuid.uuid4()
    container_ref = str(container_id)

    class FakeContainer:
        def __init__(self, cid):
            self.id = cid
            self.name = str(cid)
            self.graph_enabled = True

    async def fake_get_container(_session, _ref):
        return FakeContainer(container_id)

    # Patch manifest and container lookup
    graph_service.manifests.load_manifest = lambda *_args, **_kwargs: {"graph": {"enabled": True}}
    graph_service._get_container = fake_get_container  # type: ignore[attr-defined]
    async def _fake_validate_chunks(*_args, **_kwargs):
        return True, []

    graph_service._validate_chunk_ownership = _fake_validate_chunks  # type: ignore[attr-defined]

    # Upsert minimal graph
    upsert_req = graph_service.GraphUpsertRequest(
        container=container_ref,
        nodes=[
            graph_service.GraphNode(
                id="node-1",
                label="GraphOS",
                type="Project",
                summary="Platform",
                source_chunk_ids=[str(uuid.uuid4())],
            )
        ],
        edges=[
            graph_service.GraphEdge(
                source="node-1",
                target="node-2",
                type="LINKS",
                source_chunk_ids=[str(uuid.uuid4())],
            )
        ],
    )

    async for session in get_session():
        upsert_resp = await graph_service.graph_upsert(session, upsert_req)
        assert not upsert_resp.issues
        assert upsert_resp.inserted_nodes == 1

        search_req = GraphSearchRequest(container=container_ref, query="graphos", mode="nl", max_hops=2, k=5)
        search_resp = await graph_service.graph_search(session, search_req)
        assert not search_resp.issues
        assert len(search_resp.nodes) >= 1
        assert search_resp.timings_ms.get("graph_ms") is not None
