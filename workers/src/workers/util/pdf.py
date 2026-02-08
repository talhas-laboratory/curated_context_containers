"""PDF extraction utilities."""
from __future__ import annotations

import base64
import io
import structlog
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

import httpx

try:  # Optional dependency to keep worker runtime lean.
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional import guard
    PdfReader = None

from workers.config import settings

LOGGER = structlog.get_logger()


def _extract_storage_path(uri: str) -> tuple[str, str] | None:
    """Extract bucket and object path from storage URL.
    
    Returns (bucket, object_path) or None if not a storage URL.
    Example:
      http://talhas-laboratory.tailefe062.ts.net:3001/storage/sandbox/file.pdf?X-Amz-...
      -> ("sandbox", "file.pdf")
    """
    parsed = urlparse(uri)
    
    if '/storage/' in parsed.path:
        path_parts = parsed.path.split('/storage/', 1)
        if len(path_parts) == 2:
            object_full_path = path_parts[1]  # e.g., "sandbox/file.pdf"
            # Split into bucket (first part) and object path (rest)
            parts = object_full_path.split('/', 1)
            if len(parts) == 2:
                bucket, object_path = parts
                return (bucket, object_path)
            # If no slash, treat entire path as bucket+object
            return (object_full_path.split('/')[0] if '/' in object_full_path else "sandbox", 
                    object_full_path.split('/', 1)[-1] if '/' in object_full_path else object_full_path)
    
    return None


def _load_bytes_from_uri(uri: str) -> Optional[bytes]:
    """Load bytes from file:// or http(s) URI."""
    # Check if this is a storage URL that we can fetch from MinIO directly
    storage_path = _extract_storage_path(uri)
    if storage_path:
        bucket, object_path = storage_path
        try:
            # Import MinIO adapter lazily to avoid circular imports
            from workers.adapters.minio import minio_adapter
            
            # Get object from MinIO
            response = minio_adapter.client.get_object(bucket, object_path)
            content = response.read()
            response.close()
            response.release_conn()
            
            LOGGER.debug("minio_direct_fetch_success", bucket=bucket, object_path=object_path, size=len(content))
            return content
        except Exception as exc:
            LOGGER.warning("minio_direct_fetch_failed", bucket=bucket, object_path=object_path, error=str(exc))
            # Fall through to try regular HTTP fetch
    
    parsed = urlparse(uri)
    if parsed.scheme in {"file", ""}:
        path = Path(parsed.path or uri)
        if path.exists():
            try:
                return path.read_bytes()
            except Exception as exc:  # pragma: no cover - filesystem edge
                LOGGER.warning("pdf_read_failed", uri=uri, error=str(exc))
                return None
        return None

    if parsed.scheme in {"http", "https"}:
        try:
            resp = httpx.get(uri, timeout=15.0)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # pragma: no cover - network edge
            LOGGER.warning("pdf_fetch_failed", uri=uri, error=str(exc))
            return None
    return None


def extract_pdf_text(content: bytes | None) -> str:
    """Extract text from PDF bytes via pypdf if available."""
    if not content:
        return ""
    if PdfReader is None:
        LOGGER.warning("pypdf_missing", hint="install pypdf>=4 to enable PDF text extraction")
        return ""
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        combined = "\n\n".join(pages).strip()
        return combined
    except Exception as exc:  # pragma: no cover - extraction edge cases
        LOGGER.warning("pdf_extract_failed", error=str(exc))
        return ""


def extract_text_from_source(source: dict) -> str:
    """Extract PDF text using any available hints or bytes in the source."""
    meta = source.get("meta") or {}
    if meta.get("pdf_text"):
        return meta["pdf_text"]

    if meta.get("pdf_base64"):
        try:
            return extract_pdf_text(base64.b64decode(meta["pdf_base64"]))
        except Exception as exc:  # pragma: no cover - malformed base64
            LOGGER.warning("pdf_base64_decode_failed", error=str(exc))

    uri = source.get("uri")
    content = _load_bytes_from_uri(uri) if uri else None
    text = extract_pdf_text(content)
    return text
