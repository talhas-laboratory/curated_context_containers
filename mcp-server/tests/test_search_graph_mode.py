import pytest

from app.models.graph import GraphEdge, GraphNode, GraphSearchResponse
from app.models.search import SearchRequest
from app.services import search as search_service


@pytest.mark.asyncio
async def test_search_graph_mode_populates_results_from_graph_snippets(monkeypatch):
    async def fake_graph_search(_session, _req):
        return GraphSearchResponse(
            request_id="req-graph",
            nodes=[GraphNode(id="node-1", label="Node 1")],
            edges=[GraphEdge(source="node-1", target="node-1", type="SELF")],
            snippets=[
                {
                    "chunk_id": "chunk-1",
                    "doc_id": "doc-1",
                    "uri": "doc://1",
                    "title": "Doc 1",
                    "text": "Snippet text",
                }
            ],
            diagnostics={"mode": "nl", "graph_hits": 1},
            timings_ms={"graph_ms": 5},
            issues=[],
        )

    monkeypatch.setattr(search_service.graph_service, "graph_search", fake_graph_search)

    request = SearchRequest(query="q", container_ids=["self-knowledge"], mode="graph", k=10, diagnostics=True)
    response = await search_service.search_response(object(), request)

    assert response.issues == []
    assert response.total_hits == 1
    assert response.returned == 1
    assert len(response.results) == 1
    assert response.results[0].chunk_id == "chunk-1"
    assert response.results[0].doc_id == "doc-1"
    assert response.results[0].container_id == "self-knowledge"
    assert response.graph_context is not None
    assert len((response.graph_context.get("nodes") or [])) == 1
