from types import SimpleNamespace
from uuid import UUID

import pytest

from app.models.search import SearchRequest, SearchResult
from app.services import search as search_service
from app.services.diagnostics import StageTiming
from app.adapters.rerank import rerank_adapter


class FakeResult:
    def __init__(self, data):
        self._data = data

    def scalars(self):
        return self

    def all(self):
        return self._data


class FakeSession:
    def __init__(self, containers):
        self.containers = containers

    async def execute(self, _stmt):
        return FakeResult(self.containers)


def _container():
    return SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000123"),
        modalities=["text"],
        policy={},
        acl={},
        state="active",
        name="c1",
    )


def _result(container_id: UUID) -> SearchResult:
    return SearchResult(
        chunk_id="chunk-1",
        doc_id="doc-1",
        container_id=container_id.hex,
        container_name="c1",
        title="doc",
        snippet="body text",
        uri="s3://bucket/doc-1",
        score=0.9,
        stage_scores={"bm25": 0.9},
        modality="text",
        provenance={"source": "test"},
        meta={},
    )


@pytest.mark.asyncio
async def test_search_sets_partial_when_latency_over_budget(monkeypatch):
    container = _container()
    session = FakeSession([container])
    monkeypatch.setattr(search_service.manifests, "load_manifest", lambda name: {})
    monkeypatch.setattr(search_service.settings, "search_latency_budget_ms", 100)

    bm25_timer = StageTiming(label="bm25", started_at=0.0, duration_ms=450)
    async def fake_bm25_stage(_session, _request, _container_ids, _container_map, _modalities):
        res = _result(container.id)
        return [res], [res.chunk_id], bm25_timer

    async def fake_vector_stage(_session, _request, _container_ids, _container_map, _modalities):
        return [], [], StageTiming("embed", 0.0, 0), StageTiming("vector", 0.0, 0), []

    def fake_summarize(timers):
        return {"bm25_ms": bm25_timer.duration_ms, "expand_ms": 10, "total_ms": bm25_timer.duration_ms + 10}

    monkeypatch.setattr(search_service, "_bm25_stage", fake_bm25_stage)
    monkeypatch.setattr(search_service, "_vector_stage", fake_vector_stage)
    monkeypatch.setattr(search_service, "summarize_timings", fake_summarize)

    request = SearchRequest(query="slow query", container_ids=[container.id.hex], mode="bm25", k=3)
    response = await search_service.search_response(session, request)

    assert response.partial is True
    assert "LATENCY_BUDGET_EXCEEDED" in response.issues
    assert response.diagnostics["latency_over_budget_ms"] == 360
    assert response.returned == 1


@pytest.mark.asyncio
async def test_search_propagates_vector_down_issue(monkeypatch):
    container = _container()
    session = FakeSession([container])
    monkeypatch.setattr(search_service.manifests, "load_manifest", lambda name: {})

    async def fake_bm25_stage(_session, _request, _container_ids, _container_map, _modalities):
        res = _result(container.id)
        return [res], [res.chunk_id], StageTiming("bm25", 0.0, 5)

    async def fake_vector_stage(_session, _request, _container_ids, _container_map, _modalities):
        return [], [], StageTiming("embed", 0.0, 0), StageTiming("vector", 0.0, 0), ["VECTOR_DOWN"]

    def fake_summarize(timers):
        return {"total_ms": 5, "bm25_ms": 5}

    monkeypatch.setattr(search_service, "_bm25_stage", fake_bm25_stage)
    monkeypatch.setattr(search_service, "_vector_stage", fake_vector_stage)
    monkeypatch.setattr(search_service, "summarize_timings", fake_summarize)

    request = SearchRequest(query="vector down", container_ids=[container.id.hex], mode="hybrid", k=3)
    response = await search_service.search_response(session, request)

    assert "VECTOR_DOWN" in response.issues
    assert response.returned == 1


@pytest.mark.asyncio
async def test_search_marks_no_hits_when_empty(monkeypatch):
    container = _container()
    session = FakeSession([container])
    monkeypatch.setattr(search_service.manifests, "load_manifest", lambda name: {})

    async def fake_bm25_stage(_session, _request, _container_ids, _container_map, _modalities):
        return [], [], StageTiming("bm25", 0.0, 0)

    async def fake_vector_stage(_session, _request, _container_ids, _container_map, _modalities):
        return [], [], StageTiming("embed", 0.0, 0), StageTiming("vector", 0.0, 0), []

    def fake_summarize(timers):
        return {"total_ms": 0}

    monkeypatch.setattr(search_service, "_bm25_stage", fake_bm25_stage)
    monkeypatch.setattr(search_service, "_vector_stage", fake_vector_stage)
    monkeypatch.setattr(search_service, "summarize_timings", fake_summarize)

    request = SearchRequest(query="none", container_ids=[container.id.hex], mode="hybrid", k=3)
    response = await search_service.search_response(session, request)

    assert response.total_hits == 0
    assert "NO_HITS" in response.issues


@pytest.mark.asyncio
async def test_search_clamps_rerank_timeout_to_latency_budget(monkeypatch):
    container = _container()
    session = FakeSession([container])
    # Force manifest-driven rerank config and tighter latency budget.
    monkeypatch.setattr(
        search_service.manifests,
        "load_manifest",
        lambda name: {
            "retrieval": {
                "latency_budget_ms": 75,
                "rerank": {"enabled": True, "timeout_ms": 200, "top_k_in": 5, "top_k_out": 3},
            }
        },
    )
    monkeypatch.setattr(search_service.settings, "search_latency_budget_ms", 150)

    bm25_timer = StageTiming(label="bm25", started_at=0.0, duration_ms=10)

    async def fake_bm25_stage(_session, _request, _container_ids, _container_map, _modalities):
        res = _result(container.id)
        return [res], [res.chunk_id], bm25_timer

    async def fake_vector_stage(_session, _request, _container_ids, _container_map, _modalities):
        return [], [], StageTiming("embed", 0.0, 0), StageTiming("vector", 0.0, 0), []

    captured = {}

    async def fake_rerank(query, candidates, top_k_in, top_k_out, timeout_ms=None):
        captured["timeout_ms"] = timeout_ms
        diagnostics = {"rerank_applied": True, "rerank_provider": "test"}
        return candidates, diagnostics, []

    monkeypatch.setattr(search_service, "_bm25_stage", fake_bm25_stage)
    monkeypatch.setattr(search_service, "_vector_stage", fake_vector_stage)
    monkeypatch.setattr(rerank_adapter, "rerank", fake_rerank)

    request = SearchRequest(query="rerank budget", container_ids=[container.id.hex], mode="bm25", k=3, rerank=True)
    response = await search_service.search_response(session, request)

    assert captured["timeout_ms"] == 75  # min(rerank_timeout_ms, latency_budget)
    assert response.diagnostics.get("rerank_applied") is True


@pytest.mark.skip("Rate limiting not implemented; add coverage once path exists.")
def test_rate_limit_stub():
    """Placeholder to ensure rate-limit path is covered when implemented."""
    assert True
