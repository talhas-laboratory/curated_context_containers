"""Image helpers for ingestion pipelines."""
from __future__ import annotations

import base64
import io
import structlog
import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency guard
    Image = None

LOGGER = structlog.get_logger()


def _extract_storage_path(uri: str) -> tuple[str, str] | None:
    """Extract bucket and object path from storage URL."""
    parsed = urlparse(uri)
    
    if '/storage/' in parsed.path:
        path_parts = parsed.path.split('/storage/', 1)
        if len(path_parts) == 2:
            object_full_path = path_parts[1]
            parts = object_full_path.split('/', 1)
            if len(parts) == 2:
                return (parts[0], parts[1])
            return ("sandbox", object_full_path)
    
    return None


def _fetch_bytes_from_uri(uri: str) -> bytes | None:
    # Try MinIO direct fetch for storage URLs
    storage_path = _extract_storage_path(uri)
    if storage_path:
        bucket, object_path = storage_path
        try:
            from workers.adapters.minio import minio_adapter
            
            response = minio_adapter.client.get_object(bucket, object_path)
            content = response.read()
            response.close()
            response.release_conn()
            
            LOGGER.debug("minio_direct_fetch_success", bucket=bucket, object_path=object_path, size=len(content))
            return content
        except Exception as exc:
            LOGGER.warning("minio_direct_fetch_failed", bucket=bucket, object_path=object_path, error=str(exc))
            # Fall through to HTTP fetch
    
    parsed = urlparse(uri)
    if parsed.scheme in {"http", "https"}:
        try:
            resp = httpx.get(uri, timeout=15.0)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # pragma: no cover - network edge
            LOGGER.warning("image_fetch_failed", uri=uri, error=str(exc))
            return None
    path = Path(parsed.path or uri)
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except Exception as exc:  # pragma: no cover - filesystem edge
        LOGGER.warning("image_read_failed", path=str(path), error=str(exc))
        return None


def load_image_bytes(source: dict) -> Tuple[bytes | None, str | None, str | None]:
    """Load image bytes from meta (base64/raw) or URI."""
    meta = source.get("meta") or {}
    raw = meta.get("image_bytes")
    if raw:
        if isinstance(raw, str):
            raw = raw.encode()
        return raw, meta.get("mime") or source.get("mime"), meta.get("filename")

    if meta.get("image_base64"):
        try:
            decoded = base64.b64decode(meta["image_base64"])
            return decoded, meta.get("mime") or source.get("mime"), meta.get("filename")
        except Exception as exc:  # pragma: no cover - malformed base64
            LOGGER.warning("image_base64_decode_failed", error=str(exc))

    uri = source.get("uri")
    if uri:
        content = _fetch_bytes_from_uri(uri)
        parsed = urlparse(uri)
        filename = Path(parsed.path or "").name or None
        mime = meta.get("mime") or source.get("mime") or mimetypes.guess_type(uri)[0]
        return content, mime, filename
    return None, None, None


def make_thumbnail(
    image_bytes: bytes,
    max_edge: int = 2048,
    quality: int = 90,
) -> tuple[bytes | None, dict]:
    """Generate a JPEG thumbnail, respecting max edge while preserving aspect ratio."""
    if not image_bytes or Image is None:
        return None, {}
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        longest = max(width, height)
        if max_edge and longest > max_edge:
            scale = max_edge / float(longest)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            img = img.resize(new_size, Image.LANCZOS)
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        thumb_bytes = buf.getvalue()
        return thumb_bytes, {"width": img.width, "height": img.height, "format": "JPEG"}
    except Exception as exc:  # pragma: no cover - transformation edge cases
        LOGGER.warning("image_thumbnail_failed", error=str(exc))
        return None, {}


def infer_mime(mime_hint: str | None, filename: str | None) -> str | None:
    """Resolve mime type from explicit hint or filename extension."""
    if mime_hint:
        return mime_hint
    if filename:
        return mimetypes.guess_type(filename)[0]
    return None
