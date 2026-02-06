from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services import lifecycle as lifecycle_service
from app.services.search import _expand_container_tree
from app.models.agent import CreateContainerRequest, DeleteContainerRequest


@dataclass
class DummyContainer:
    id: UUID
    parent_id: UUID | None
    name: str


def test_expand_container_tree_by_parent_name():
    parent_id = uuid4()
    child_id = uuid4()
    grandchild_id = uuid4()

    containers = [
        DummyContainer(id=parent_id, parent_id=None, name="parent"),
        DummyContainer(id=child_id, parent_id=parent_id, name="child"),
        DummyContainer(id=grandchild_id, parent_id=child_id, name="grandchild"),
    ]

    expanded, expanded_ids = _expand_container_tree(containers, ["parent"])
    expanded_set = {str(c.id) for c in expanded}

    assert str(parent_id) in expanded_set
    assert str(child_id) in expanded_set
    assert str(grandchild_id) in expanded_set
    assert set(expanded_ids) == expanded_set


def test_expand_container_tree_by_child_id():
    parent_id = uuid4()
    child_id = uuid4()
    sibling_id = uuid4()

    containers = [
        DummyContainer(id=parent_id, parent_id=None, name="parent"),
        DummyContainer(id=child_id, parent_id=parent_id, name="child"),
        DummyContainer(id=sibling_id, parent_id=parent_id, name="sibling"),
    ]

    expanded, expanded_ids = _expand_container_tree(containers, [str(child_id)])
    expanded_set = {str(c.id) for c in expanded}

    assert expanded_set == {str(child_id)}
    assert expanded_ids == [str(child_id)]


def test_expand_container_tree_unknown_returns_empty():
    containers = [DummyContainer(id=uuid4(), parent_id=None, name="parent")]

    expanded, expanded_ids = _expand_container_tree(containers, ["missing"])

    assert expanded == []
    assert expanded_ids == []


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.added = None
        self.executed = []

    async def execute(self, statement):
        self.executed.append(statement)
        return FakeResult(self.result)

    def add(self, obj):
        self.added = obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


@pytest.mark.asyncio
async def test_create_container_inherits_parent_policy(monkeypatch):
    parent_policy = {"privacy": "local_only", "retention_days": 30}
    parent = SimpleNamespace(id=uuid4(), policy=parent_policy)

    async def fake_get_container_by_ref(session, ref):
        return parent

    monkeypatch.setattr(lifecycle_service, "_get_container_by_ref", fake_get_container_by_ref)

    session = FakeSession(result=None)
    request = CreateContainerRequest(
        name="child",
        theme="child theme",
        parent_id=str(parent.id),
        policy={"privacy": "exportable"},
    )

    created = await lifecycle_service.create_container(session, request, agent_id="tester")

    assert created.parent_id == parent.id
    assert created.policy == parent_policy
    assert created.policy is not parent_policy  # policy copied to avoid mutations


@pytest.mark.asyncio
async def test_delete_container_cascades_permanent(monkeypatch):
    parent = SimpleNamespace(id=uuid4(), modalities=["text"], state="active", updated_at=None)
    child = SimpleNamespace(id=uuid4(), modalities=["pdf"], state="active", updated_at=None)

    async def fake_collect_descendants(session, root):
        return [parent, child]

    async def fake_qdrant_delete(container_id, modalities=None):
        calls["qdrant"].append((container_id, modalities))

    async def fake_minio_delete(container_id):
        calls["minio"].append(container_id)

    monkeypatch.setattr(lifecycle_service, "_collect_descendants", fake_collect_descendants)
    monkeypatch.setattr(lifecycle_service.qdrant_adapter, "delete_container", fake_qdrant_delete)
    monkeypatch.setattr(lifecycle_service.minio_adapter, "delete_container", fake_minio_delete)

    session = FakeSession(result=parent)
    calls = {"qdrant": [], "minio": []}

    request = DeleteContainerRequest(container=str(parent.id), permanent=True)
    await lifecycle_service.delete_container(session, request, agent_id="tester")

    delete_tables = {
        getattr(stmt, "table", None).name
        for stmt in session.executed
        if getattr(stmt, "table", None) is not None
    }
    assert {"chunks", "documents", "jobs", "container_versions", "containers"}.issubset(delete_tables)

    qdrant_ids = {cid for cid, _ in calls["qdrant"]}
    minio_ids = set(calls["minio"])
    assert qdrant_ids == {str(parent.id), str(child.id)}
    assert minio_ids == {str(parent.id), str(child.id)}


@pytest.mark.asyncio
async def test_delete_container_cascades_archive(monkeypatch):
    parent = SimpleNamespace(id=uuid4(), modalities=["text"], state="active", updated_at=None)
    child = SimpleNamespace(id=uuid4(), modalities=["pdf"], state="active", updated_at=None)

    async def fake_collect_descendants(session, root):
        return [parent, child]

    async def fake_qdrant_delete(*args, **kwargs):
        calls["qdrant"].append(args)

    async def fake_minio_delete(*args, **kwargs):
        calls["minio"].append(args)

    monkeypatch.setattr(lifecycle_service, "_collect_descendants", fake_collect_descendants)
    monkeypatch.setattr(lifecycle_service.qdrant_adapter, "delete_container", fake_qdrant_delete)
    monkeypatch.setattr(lifecycle_service.minio_adapter, "delete_container", fake_minio_delete)

    session = FakeSession(result=parent)
    calls = {"qdrant": [], "minio": []}

    request = DeleteContainerRequest(container=str(parent.id), permanent=False)
    await lifecycle_service.delete_container(session, request, agent_id="tester")

    assert parent.state == "archived"
    assert child.state == "archived"
    assert calls["qdrant"] == []
    assert calls["minio"] == []
