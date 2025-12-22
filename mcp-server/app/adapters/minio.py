"""MinIO adapter for document lifecycle operations."""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

LOGGER = logging.getLogger(__name__)
settings = get_settings()


def _endpoint_from_url(url: str) -> tuple[str, bool]:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc, parsed.scheme == "https"
    return url.replace("http://", "").replace("https://", ""), parsed.scheme == "https"


class MinioAdapter:
    """Small helper around MinIO SDK for removing stored artifacts."""

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
        except Exception as exc:  # pragma: no cover - requires MinIO
            LOGGER.warning("minio_bucket_init_failed error=%s", exc)

    async def delete_document(self, container_id: str, document_id: str) -> None:
        """Delete objects associated with a document (best-effort)."""
        if not container_id or not document_id:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._delete_document_sync, container_id, document_id)

    def _delete_document_sync(self, container_id: str, document_id: str) -> None:
        prefix = f"{container_id}/{document_id}"
        targets = [f"{prefix}.txt", f"{prefix}.json"]
        for target in targets:
            try:
                self.client.remove_object(self.bucket, target)
            except S3Error as exc:  # pragma: no cover - requires MinIO
                if exc.code not in {"NoSuchKey", "NoSuchObject"}:
                    LOGGER.warning("minio_remove_failed object=%s error=%s", target, exc)
            except Exception as exc:  # pragma: no cover - requires MinIO
                LOGGER.warning("minio_remove_failed object=%s error=%s", target, exc)

        try:
            objects = list(
                self.client.list_objects(self.bucket, prefix=f"{prefix}/", recursive=True)
            )
            for obj in objects:
                try:
                    self.client.remove_object(self.bucket, obj.object_name)
                except Exception as exc:  # pragma: no cover - requires MinIO
                    LOGGER.warning(
                        "minio_remove_failed object=%s error=%s", obj.object_name, exc
                    )
        except Exception as exc:  # pragma: no cover - requires MinIO
            LOGGER.warning("minio_list_failed prefix=%s error=%s", prefix, exc)


minio_adapter = MinioAdapter()









