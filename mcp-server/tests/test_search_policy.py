from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.models.search import SearchRequest
from app.services import search as search_service


class FakeResult:
    def __init__(self, data):
        self._data = data

    def scalars(self):
        return self

    def all(self):
        return self._data


class FakeSession:
    """Minimal async session stub that returns canned results sequentially."""

    def __init__(self, containers, chunk_rows=None):
        self.containers = containers
        self.chunk_rows = chunk_rows or []
        self.calls = 0

    async def execute(self, _stmt):
        self.calls += 1
        if self.calls == 1:
            return FakeResult(self.containers)
        return FakeResult(self.chunk_rows)


def _container(acl_roles, modalities=("text",)):
    cid = UUID("00000000-0000-0000-0000-000000000123")
    return SimpleNamespace(
        id=cid,
        name="locked-container",
        modalities=list(modalities),
        policy={},
        acl={"roles": acl_roles},
        state="active",
    )


def _chunk(container_id, modality="text"):
    chunk_id = uuid4()
    doc_id = uuid4()
    chunk = SimpleNamespace(
        id=chunk_id,
        doc_id=doc_id,
        container_id=container_id,
        modality=modality,
        text="searchable text",
        provenance={},
        meta={},
        offsets=None,
        dedup_of=None,
        created_at=datetime.now(timezone.utc),
    )
    doc = SimpleNamespace(id=doc_id, title="Doc", uri="https://example.com/doc")
    return (chunk, doc, 1.0)


@pytest.mark.asyncio
async def test_search_blocks_acl_forbidden_container():
    """Containers with ACL that exclude the default principal should be blocked."""
    container = _container(acl_roles={"owner": ["someone_else"]})
    session = FakeSession([container])
    request = SearchRequest(query="test", container_ids=[container.id.hex], mode="bm25", k=5)

    response = await search_service.search_response(session, request)

    assert response.issues == ["CONTAINER_NOT_FOUND"]
    assert response.total_hits == 0
    assert response.diagnostics.get("blocked_containers") == [container.id.hex]


@pytest.mark.asyncio
async def test_search_filters_disallowed_modalities():
    """Results with modalities outside the manifest/container allowlist are dropped."""
    container = _container(acl_roles={"reader": ["agent:local"]}, modalities=("text",))
    chunk_row = _chunk(container.id, modality="image")
    session = FakeSession([container], [chunk_row])
    request = SearchRequest(query="test", container_ids=[container.id.hex], mode="bm25", k=5)

    response = await search_service.search_response(session, request)

    assert response.total_hits == 0
    assert "NO_HITS" in response.issues
    assert response.diagnostics["bm25_hits"] == 0


def test_latency_budget_override_selects_manifest_minimum():
    """Latency budget falls back to the minimum across manifest overrides."""
    cid_one = UUID("00000000-0000-0000-0000-000000000111")
    cid_two = UUID("00000000-0000-0000-0000-000000000222")
    c1 = SimpleNamespace(id=cid_one, modalities=["text"], policy={}, acl={}, state="active", name="c1")
    c2 = SimpleNamespace(id=cid_two, modalities=["text"], policy={}, acl={}, state="active", name="c2")
    manifest_map = {
        cid_one.hex: {"retrieval": {"latency_budget_ms": 750}},
        cid_two.hex: {"retrieval": {"latency_budget_ms": 650}},
    }

    budget = search_service._latency_budget([c1, c2], manifest_map)

    assert budget == 650
