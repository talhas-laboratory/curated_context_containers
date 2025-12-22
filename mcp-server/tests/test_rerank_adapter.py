import asyncio
import pytest

from app.adapters.rerank import RerankAdapter
from app.models.search import SearchResult


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    call_count = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        FakeClient.call_count += 1
        # Favor chunk_id "b" over "a"
        return FakeResponse({"results": [{"id": "b", "score": 0.9}, {"id": "a", "score": 0.1}]})


@pytest.mark.asyncio
async def test_rerank_adapter_uses_cache(monkeypatch):
    monkeypatch.setattr("app.adapters.rerank.httpx.AsyncClient", FakeClient)
    adapter = RerankAdapter()
    adapter.api_url = "http://fake-provider"
    adapter.api_key = None
    adapter.cache_ttl_seconds = 300
    adapter.cache_size = 4

    candidates = [
        SearchResult(chunk_id="a", doc_id="d1", container_id="c1", container_name=None, title=None, snippet="A", uri=None, score=0.1, stage_scores={}, modality="text", provenance={}, meta={}),
        SearchResult(chunk_id="b", doc_id="d2", container_id="c1", container_name=None, title=None, snippet="B", uri=None, score=0.2, stage_scores={}, modality="text", provenance={}, meta={}),
    ]

    ranked1, diags1, issues1 = await adapter.rerank("q", candidates, top_k_in=2, top_k_out=1)
    assert ranked1[0].chunk_id == "b"
    assert diags1["rerank_applied"] is True
    assert diags1["rerank_cache_hit"] is False
    assert issues1 == []

    ranked2, diags2, issues2 = await adapter.rerank("q", candidates, top_k_in=2, top_k_out=1)
    assert FakeClient.call_count == 1, "second call should hit cache"
    assert ranked2[0].chunk_id == "b"
    assert diags2["rerank_cache_hit"] is True
    assert issues2 == []
