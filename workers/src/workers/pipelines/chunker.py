"""Utilities for splitting text into chunks with overlap."""
from __future__ import annotations

from typing import Iterable, List


DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 80


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Split text into chunks with overlap; ensures non-empty chunks."""
    sanitized = (text or "").strip()
    if not sanitized:
        return []

    tokens: List[str] = []
    start = 0
    length = len(sanitized)
    while start < length:
        end = min(length, start + chunk_size)
        tokens.append(sanitized[start:end].strip())
        if end == length:
            break
        start = max(0, end - overlap)
    return [t for t in tokens if t]


def deduplicate_hashes(hashes: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    uniques: List[str] = []
    for value in hashes:
        if value in seen:
            continue
        seen.add(value)
        uniques.append(value)
    return uniques
