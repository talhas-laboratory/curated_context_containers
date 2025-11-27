import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import workers.pipelines as pipelines  # noqa: E402  pylint: disable=wrong-import-position


class CacheTTLTest(unittest.TestCase):
    def setUp(self):
        self.original_ttl = pipelines.CACHE_TTL_SECONDS

    def tearDown(self):
        pipelines.CACHE_TTL_SECONDS = self.original_ttl

    def test_not_stale_when_ttl_zero(self):
        pipelines.CACHE_TTL_SECONDS = 0
        past = datetime.now(timezone.utc) - timedelta(days=365)
        self.assertFalse(pipelines._is_cache_entry_stale(past))  # pylint: disable=protected-access

    def test_stale_when_age_exceeds_ttl(self):
        pipelines.CACHE_TTL_SECONDS = 100
        past = datetime.now(timezone.utc) - timedelta(seconds=150)
        self.assertTrue(pipelines._is_cache_entry_stale(past))  # pylint: disable=protected-access

    def test_recent_entry_not_stale(self):
        pipelines.CACHE_TTL_SECONDS = 100
        recent = datetime.now(timezone.utc) - timedelta(seconds=10)
        self.assertFalse(pipelines._is_cache_entry_stale(recent))  # pylint: disable=protected-access

    def test_none_timestamp_never_stale(self):
        pipelines.CACHE_TTL_SECONDS = 100
        self.assertFalse(pipelines._is_cache_entry_stale(None))  # pylint: disable=protected-access

    def test_stale_entry_triggers_delete_and_recompute(self):
        pipelines.CACHE_TTL_SECONDS = 1

        class FakeCursor:
            def __init__(self):
                self.executed = []
                self.rows = [(pipelines._vector_to_bytes([1.0, 0.0]), datetime.now(timezone.utc) - timedelta(seconds=5))]

            def execute(self, query, params=None):
                self.executed.append(query.strip())

            def fetchone(self):
                return self.rows.pop(0) if self.rows else None

        class FakeEmbedder:
            def __init__(self):
                self.called = False

            def embed_text(self, texts):
                self.called = True
                return [[0.5, 0.5]]

        cur = FakeCursor()
        vector, hit, miss = pipelines._embedding_from_cache_or_compute(
            cur, "cache-key", "text chunk", "text", embedder=FakeEmbedder()
        )

        self.assertEqual(miss, 1)
        self.assertEqual(hit, 0)
        self.assertTrue(any("DELETE FROM embedding_cache" in q for q in cur.executed))
        self.assertTrue(any("INSERT INTO embedding_cache" in q for q in cur.executed))
        self.assertEqual(vector, [0.5, 0.5])

    def test_fresh_entry_hits_cache(self):
        pipelines.CACHE_TTL_SECONDS = 60

        class FakeCursor:
            def __init__(self):
                self.executed = []
                self.rows = [(pipelines._vector_to_bytes([1.0, 0.0]), datetime.now(timezone.utc))]

            def execute(self, query, params=None):
                self.executed.append(query.strip())

            def fetchone(self):
                return self.rows.pop(0) if self.rows else None

        cur = FakeCursor()
        vector, hit, miss = pipelines._embedding_from_cache_or_compute(cur, "cache-key", "text chunk", "text")

        self.assertEqual(hit, 1)
        self.assertEqual(miss, 0)
        self.assertTrue(any("UPDATE embedding_cache" in q for q in cur.executed))
        self.assertEqual(vector, [1.0, 0.0])


if __name__ == "__main__":
    unittest.main()
