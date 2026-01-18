"""PDF extraction utilities."""
from __future__ import annotations

import base64
import io
import structlog
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

try:  # Optional dependency to keep worker runtime lean.
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional import guard
    PdfReader = None

LOGGER = structlog.get_logger()


def _load_bytes_from_uri(uri: str) -> Optional[bytes]:
    """Load bytes from file:// or http(s) URI."""
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
