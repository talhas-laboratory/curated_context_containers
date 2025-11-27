import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from workers.adapters.minio import MinioAdapter, _endpoint_from_url  # noqa: E402  pylint: disable=wrong-import-position


class FakeMinioClient:
    def __init__(self, exists: bool = True):
        self.exists = exists
        self.created = False
        self.stored = []

    def bucket_exists(self, bucket):  # pylint: disable=unused-argument
        return self.exists

    def make_bucket(self, bucket):  # pylint: disable=unused-argument
        self.created = True
        self.exists = True

    def put_object(self, bucket, object_name, data, length, content_type):  # pylint: disable=unused-argument
        if bucket == "fail":
            raise RuntimeError("boom")
        self.stored.append((bucket, object_name, length, content_type))


class MinioAdapterTest(unittest.TestCase):
    def test_endpoint_parser_handles_scheme(self):
        endpoint, secure = _endpoint_from_url("https://example.com:9000")
        self.assertEqual(endpoint, "example.com:9000")
        self.assertTrue(secure)

    def test_bucket_creation_when_missing(self):
        client = FakeMinioClient(exists=False)
        adapter = MinioAdapter(client=client, bucket="test")
        self.assertTrue(client.created)
        self.assertEqual(adapter.bucket, "test")

    def test_store_raw_handles_errors(self):
        client = FakeMinioClient(exists=True)
        adapter = MinioAdapter(client=client, bucket="fail")
        adapter.store_raw("container", "doc", None, "hello world")
        # When bucket forces failure, nothing is appended but no exception should escape
        self.assertEqual(client.stored, [])

    def test_store_raw_success(self):
        client = FakeMinioClient(exists=True)
        adapter = MinioAdapter(client=client, bucket="ok")
        adapter.store_raw("container", "doc", None, "hello world")
        self.assertEqual(len(client.stored), 1)
        bucket, object_name, length, content_type = client.stored[0]
        self.assertEqual(bucket, "ok")
        self.assertEqual(object_name, "container/doc.txt")
        self.assertEqual(length, len("hello world"))
        self.assertEqual(content_type, "text/plain")


if __name__ == "__main__":
    unittest.main()
