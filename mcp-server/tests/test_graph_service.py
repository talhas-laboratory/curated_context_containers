"""Unit tests for graph service behaviors without hitting Neo4j."""
from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from app.models.graph import GraphSearchRequest, GraphUpsertRequest
from app.services import graph as graph_service


class _FakeAsyncResult:
    def all(self):
        return []


class _FakeAsyncSession:
    async def execute(self, *_args, **_kwargs):
        return _FakeAsyncResult()


class _FakeRecord:
    def __init__(self, nodes: list[dict], rels: list[dict]):
        self._nodes = nodes
        self._rels = rels

    def get(self, key: str):
        if key == "nodes":
            return self._nodes
        if key == "rel_maps":
            return self._rels
        return None


class _FakeRun:
    def __init__(self, record: _FakeRecord):
        self._record = record

    def single(self):
        return self._record


class _FakeSessionCtx:
    def __init__(self, record: _FakeRecord):
        self._record = record

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def run(self, *_args, **_kwargs):
        return _FakeRun(self._record)


class _FakeDriver:
    def __init__(self, record: _FakeRecord):
        self._record = record

    def session(self):
        return _FakeSessionCtx(self._record)


@pytest.mark.asyncio
async def test_graph_search_returns_nodes_and_edges(monkeypatch):
    fake_container = type("Container", (), {"id": UUID("12345678-1234-5678-1234-567812345678"), "name": "c", "graph_enabled": True})

    async def fake_get_container(_session, _ref):
        return fake_container

    monkeypatch.setattr(graph_service, "_get_container", fake_get_container)
    monkeypatch.setattr(graph_service.manifests, "load_manifest", lambda *_args, **_kwargs: {"graph": {"enabled": True}})

    record = _FakeRecord(
        nodes=[
          {"node_id": "node-1", "label": "GraphOS", "type": "Project", "summary": "Platform", "properties": {}, "source_chunk_ids": ["chunk-1"]}
        ],
        rels=[
          {"source": "Team", "target": "GraphOS", "type": "WORKS_ON", "properties": {}, "source_chunk_ids": ["chunk-2"]}
        ],
    )
    fake_driver = _FakeDriver(record)
    monkeypatch.setattr(graph_service.neo4j_adapter, "connect", lambda: fake_driver)
    async def fake_translate_nl_to_cypher(**_kwargs):
        return (
            "MATCH (n:LLCNode {container_id:$cid}) RETURN [] AS nodes, [] AS rel_maps",
            {"model": "test"},
            [],
        )

    monkeypatch.setattr(graph_service.graph_nl2cypher, "translate_nl_to_cypher", fake_translate_nl_to_cypher)
    monkeypatch.setattr(
        graph_service.graph_nl2cypher,
        "validate_cypher",
        lambda cypher, schema, max_hops, k: (True, [], {"validated": True}),
    )
    monkeypatch.setattr(
        graph_service,
        "_load_schema",
        lambda _driver, _cid: (["LLCNode"], ["LLCEdge"], {"node_count": 1, "edge_count": 1}),
    )

    request = GraphSearchRequest(container="c", query="graph", mode="nl", max_hops=2, k=5, diagnostics=True)
    response = await graph_service.graph_search(_FakeAsyncSession(), request)

    assert not response.issues
    assert len(response.nodes) == 1
    assert len(response.edges) == 1
    assert response.timings_ms.get("graph_ms") is not None
    assert response.diagnostics.get("graph_hits") == 1


@pytest.mark.asyncio
async def test_graph_search_coerces_integer_ids(monkeypatch):
    fake_container = type("Container", (), {"id": UUID("12345678-1234-5678-1234-567812345678"), "name": "c", "graph_enabled": True})

    async def fake_get_container(_session, _ref):
        return fake_container

    monkeypatch.setattr(graph_service, "_get_container", fake_get_container)
    monkeypatch.setattr(graph_service.manifests, "load_manifest", lambda *_args, **_kwargs: {"graph": {"enabled": True}})

    record = _FakeRecord(
        nodes=[
            {"node_id": 594, "label": "Poster", "type": "Concept", "summary": "Typography", "properties": {}, "source_chunk_ids": [469]}
        ],
        rels=[
            {"source": 594, "target": 470, "type": "LLCEdge", "properties": {}, "source_chunk_ids": [469]}
        ],
    )
    fake_driver = _FakeDriver(record)
    monkeypatch.setattr(graph_service.neo4j_adapter, "connect", lambda: fake_driver)

    async def fake_translate_nl_to_cypher(**_kwargs):
        return (
            "MATCH (n:LLCNode {container_id:$cid}) RETURN [] AS nodes, [] AS rel_maps",
            {"model": "test"},
            [],
        )

    monkeypatch.setattr(graph_service.graph_nl2cypher, "translate_nl_to_cypher", fake_translate_nl_to_cypher)
    monkeypatch.setattr(
        graph_service.graph_nl2cypher,
        "validate_cypher",
        lambda cypher, schema, max_hops, k: (True, [], {"validated": True}),
    )
    monkeypatch.setattr(
        graph_service,
        "_load_schema",
        lambda _driver, _cid: (["LLCNode"], ["LLCEdge"], {"node_count": 1, "edge_count": 1}),
    )

    request = GraphSearchRequest(container="c", query="graph", mode="nl", max_hops=2, k=5, diagnostics=True)
    response = await graph_service.graph_search(_FakeAsyncSession(), request)

    assert not response.issues
    assert len(response.nodes) == 1
    assert response.nodes[0].id == "594"
    assert len(response.edges) == 1
    assert response.edges[0].source == "594"
    assert response.edges[0].target == "470"


@pytest.mark.asyncio
async def test_graph_upsert_requires_graph_enabled(monkeypatch):
    fake_container = type("Container", (), {"id": UUID("12345678-1234-5678-1234-567812345678"), "name": "c", "graph_enabled": False})

    async def fake_get_container(_session, _ref):
        return fake_container

    monkeypatch.setattr(graph_service, "_get_container", fake_get_container)
    monkeypatch.setattr(graph_service.manifests, "load_manifest", lambda *_args, **_kwargs: {"graph": {"enabled": False}})

    request = GraphUpsertRequest(container="c", nodes=[], edges=[], mode="merge")
    response = await graph_service.graph_upsert(_FakeAsyncSession(), request)

    assert response.issues == ["GRAPH_DISABLED"]
    assert response.inserted_nodes == 0
    assert response.inserted_edges == 0
