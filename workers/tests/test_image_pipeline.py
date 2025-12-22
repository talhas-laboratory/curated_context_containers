import io
import uuid
from types import SimpleNamespace

import pytest

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency guard
    pytest.skip("Pillow not available", allow_module_level=True)

from workers import pipelines


class StubCursor:
    def __init__(self, row_batches, queries):
        self._row_batches = row_batches
        self._current_rows = []
        self.queries = queries

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.queries.append((query.strip(), params))
        self._current_rows = self._row_batches.pop(0) if self._row_batches else []

    def fetchone(self):
        if not self._current_rows:
            return None
        return self._current_rows.pop(0)

    def fetchall(self):
        return list(self._current_rows)


class StubConnection:
    def __init__(self, row_batches=None):
        self.row_batches = [list(batch) for batch in (row_batches or [])]
        self.queries = []
        self.commit_count = 0

    def cursor(self):
        return StubCursor(self.row_batches, self.queries)

    def commit(self):
        self.commit_count += 1


class FakeQdrant:
    def __init__(self):
        self.upserts = []
        self.searches = 0

    def search_similar(self, container_id, vector, limit=1, modality="text"):
        self.searches += 1
        # Return below-threshold score to force vector write
        return [SimpleNamespace(payload={"chunk_id": str(uuid.uuid4())}, score=0.1)]

    def upsert(self, container_id, modality, vectors, dims=None):
        self.upserts.append({"container_id": container_id, "modality": modality, "vectors": vectors, "dims": dims})


class FakeMinio:
    def __init__(self):
        self.calls = []

    def store_image(self, container_id, doc_id, original_bytes, thumbnail_bytes=None, filename=None, mime=None):
        self.calls.append(
            {
                "container_id": container_id,
                "doc_id": doc_id,
                "original_bytes": original_bytes,
                "thumbnail_bytes": thumbnail_bytes,
                "filename": filename,
                "mime": mime,
            }
        )
        return {"original": f"{container_id}/{doc_id}/original/img.png", "thumbnail": f"{container_id}/{doc_id}/thumbs/img.jpg"}


class FakeEmbedder:
    def embed_image(self, images):
        return [[0.1, 0.2, 0.3, 0.4] for _ in images]


def _make_image_bytes() -> bytes:
    img = Image.new("RGB", (2, 2), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_pipeline_writes_storage_and_vectors(monkeypatch):
    doc_id = uuid.uuid4()
    conn = StubConnection(
        row_batches=[
            [],  # documents lookup -> none
            [{"id": doc_id}],  # document insert returning
            [],  # embedding cache lookup
        ]
    )
    fake_qdrant = FakeQdrant()
    fake_minio = FakeMinio()
    fake_embedder = FakeEmbedder()
    monkeypatch.setattr(pipelines, "QDRANT", fake_qdrant)
    monkeypatch.setattr(pipelines, "minio_adapter", fake_minio)
    monkeypatch.setattr(pipelines, "EMBEDDER", fake_embedder)

    image_bytes = _make_image_bytes()
    job = {
        "payload": {
            "container_id": str(uuid.uuid4()),
            "container_name": "test-container",
            "container_dims": 4,
            "embedder_version": "v-test",
            "manifest": {"dedup": {"semantic_threshold": 0.5}},
            "source": {"uri": "file://example.png", "meta": {"image_bytes": image_bytes}},
        }
    }

    pipelines._image_pipeline(conn, job, heartbeat=None)

    assert fake_minio.calls, "image should be stored in MinIO"
    assert fake_qdrant.upserts, "vector should be upserted to qdrant"
    assert fake_qdrant.upserts[0]["modality"] == "image"
    assert conn.commit_count >= 1
