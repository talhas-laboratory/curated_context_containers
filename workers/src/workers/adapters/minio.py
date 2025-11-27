"""MinIO adapter."""
from __future__ import annotations

import io
import logging
from urllib.parse import urlparse

from minio import Minio

from workers.config import settings

LOGGER = logging.getLogger(__name__)


def _endpoint_from_url(url: str) -> tuple[str, bool]:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc, parsed.scheme == "https"
    return url.replace("http://", "").replace("https://", ""), parsed.scheme == "https"


class MinioAdapter:
    def __init__(self, client: Minio | None = None, bucket: str | None = None) -> None:
        if client is None:
            endpoint, inferred_secure = _endpoint_from_url(settings.minio_endpoint)
            secure = settings.minio_secure or inferred_secure
            client = Minio(
                endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=secure,
            )
        self.client = client
        self.bucket = bucket or settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as exc:  # pragma: no cover - requires MinIO running
            LOGGER.warning("minio_bucket_init_failed error=%s", exc)

    def store_raw(self, container_id: str, doc_id: str, source_uri: str | None, content: str) -> None:
        data = content.encode("utf-8")
        object_name = f"{container_id}/{doc_id}.txt"
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type="text/plain",
            )
        except Exception as exc:  # pragma: no cover - requires MinIO running
            LOGGER.warning("minio_store_failed object=%s error=%s", object_name, exc)


minio_adapter = MinioAdapter()
