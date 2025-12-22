"""MinIO adapter."""
from __future__ import annotations

import io
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio

from workers.config import settings

LOGGER = logging.getLogger(__name__)


def _endpoint_from_url(url: str) -> tuple[str, bool]:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc, parsed.scheme == "https"
    return url.replace("http://", "").replace("https://", ""), parsed.scheme == "https"


def _ext_from_mime(mime: str | None) -> str:
    if not mime:
        return "bin"
    guessed = mimetypes.guess_extension(mime.split(";")[0].strip()) or ""
    return guessed.lstrip(".") or "bin"


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

    def store_image(
        self,
        container_id: str,
        doc_id: str,
        original_bytes: bytes,
        thumbnail_bytes: bytes | None = None,
        filename: str | None = None,
        mime: str | None = None,
    ) -> dict[str, str | None]:
        """Persist original image + optional thumbnail. Best-effort; logs on failure."""
        paths: dict[str, str | None] = {"original": None, "thumbnail": None}
        base_name = Path(filename or "image").name
        ext = _ext_from_mime(mime)
        if "." not in base_name:
            base_name = f"{base_name}.{ext}"

        original_key = f"{container_id}/{doc_id}/original/{base_name}"
        try:
            self.client.put_object(
                self.bucket,
                original_key,
                io.BytesIO(original_bytes),
                length=len(original_bytes),
                content_type=mime or "application/octet-stream",
            )
            paths["original"] = original_key
        except Exception as exc:  # pragma: no cover - requires MinIO running
            LOGGER.warning("minio_store_image_failed object=%s error=%s", original_key, exc)

        if thumbnail_bytes:
            thumb_name = f"{Path(base_name).stem}_thumb.jpg"
            thumb_key = f"{container_id}/{doc_id}/thumbs/{thumb_name}"
            try:
                self.client.put_object(
                    self.bucket,
                    thumb_key,
                    io.BytesIO(thumbnail_bytes),
                    length=len(thumbnail_bytes),
                    content_type="image/jpeg",
                )
                paths["thumbnail"] = thumb_key
            except Exception as exc:  # pragma: no cover - requires MinIO running
                LOGGER.warning("minio_store_thumb_failed object=%s error=%s", thumb_key, exc)

        return paths


minio_adapter = MinioAdapter()
