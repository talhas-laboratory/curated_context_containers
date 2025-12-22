import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from httpx import Headers
from qdrant_client.http.exceptions import UnexpectedResponse

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from workers.adapters.qdrant import QdrantAdapter  # noqa: E402  pylint: disable=wrong-import-position


class FakeQdrantClient:
    def __init__(self, existing=None, search_error=False):
        self.collections = set(existing or [])
        self.created = []
        self.search_error = search_error
        self.search_calls = 0

    def get_collection(self, name):
        if name not in self.collections:
            raise UnexpectedResponse(503, "missing", b"", Headers())

    def create_collection(self, collection_name, vectors_config):  # pylint: disable=unused-argument
        self.collections.add(collection_name)
        self.created.append(collection_name)

    def upsert(self, **kwargs):  # pylint: disable=unused-argument
        return None

    def search(self, **kwargs):  # pylint: disable=unused-argument
        self.search_calls += 1
        if self.search_error:
            raise RuntimeError("search failure")
        return [SimpleNamespace(payload={"chunk_id": "abc"}, score=0.97)]


class QdrantAdapterTest(unittest.TestCase):
    def test_ensure_collection_creates_when_missing(self):
        client = FakeQdrantClient()
        adapter = QdrantAdapter(client=client)

        adapter.ensure_collection("container-1", "text")

        self.assertIn("c_container-1_text", client.created)
        # second call should use cache and not re-create
        adapter.ensure_collection("container-1", "text")
        self.assertEqual(client.created.count("c_container-1_text"), 1)

    def test_search_similar_handles_errors(self):
        client = FakeQdrantClient(existing=["c_container-1_text"], search_error=True)
        adapter = QdrantAdapter(client=client)
        adapter.collections.add("c_container-1_text")

        results = adapter.search_similar("container-1", [0.1, 0.2], modality="text")
        self.assertEqual(results, [])

    def test_search_similar_returns_hits(self):
        client = FakeQdrantClient(existing=["c_container-1_text"], search_error=False)
        adapter = QdrantAdapter(client=client)
        adapter.collections.add("c_container-1_text")

        results = adapter.search_similar("container-1", [0.1, 0.2], modality="text")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].payload["chunk_id"], "abc")


if __name__ == "__main__":
    unittest.main()
