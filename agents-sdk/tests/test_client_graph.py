import asyncio

import httpx
import pytest

from llc_agents import AgentSession, ContainerClient


def _mock_transport():
  async def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/containers/graph_search":
      return httpx.Response(
        200,
        json={
          "version": "v1",
          "request_id": "req-graph",
          "nodes": [{"id": "node-1", "label": "GraphOS"}],
          "edges": [{"source": "Team", "target": "GraphOS", "type": "WORKS_ON"}],
          "snippets": [{"chunk_id": "chunk-1", "text": "Context"}],
          "diagnostics": {"graph_hits": 1},
          "timings_ms": {"graph_ms": 12},
          "issues": [],
        },
      )
    if request.url.path == "/v1/containers/graph_schema":
      return httpx.Response(
        200,
        json={
          "version": "v1",
          "request_id": "req-schema",
          "schema": {"node_labels": ["LLCNode"], "edge_types": ["LLCEdge"]},
          "diagnostics": {"node_count": 1, "edge_count": 1},
          "issues": [],
        },
      )
    raise AssertionError(f"Unhandled path: {request.url.path}")

  return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_graph_search_and_schema_roundtrip():
  transport = _mock_transport()
  session = AgentSession(agent_id="test-agent", base_url="http://test", token="t")
  session.client = httpx.AsyncClient(transport=transport, base_url="http://test")
  async with session:
    client = ContainerClient(session)
    graph = await client.graph_search(container="expressionist-art", query="graph query")
    assert graph["nodes"][0]["label"] == "GraphOS"
    assert graph["diagnostics"]["graph_hits"] == 1

    schema = await client.graph_schema(container="expressionist-art")
    assert "LLCNode" in schema["schema"]["node_labels"]
