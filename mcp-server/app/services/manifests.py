"""Manifest loading utilities."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from app.core.config import get_settings


@lru_cache(maxsize=64)
def _manifest_cache() -> dict[str, dict[str, Any]]:
    """Initialize cache container."""
    return {}


def _manifest_path(container_name: str) -> Path:
    settings = get_settings()
    manifest_root = Path(settings.manifests_path)
    return manifest_root / f"{container_name}.yaml"


def load_manifest(container_name: str) -> Optional[dict[str, Any]]:
    """Load manifest YAML for container name/id, returning None if missing."""
    cache = _manifest_cache()
    key = container_name.lower()
    if key in cache:
        return cache[key]

    path = _manifest_path(container_name)
    if not path.exists():
        cache[key] = None
        return None

    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    cache[key] = data
    return data


def refresh_manifest_cache(container_name: str | None = None) -> None:
    """Invalidate cache for specific container or all."""
    cache = _manifest_cache()
    if container_name:
        cache.pop(container_name.lower(), None)
    else:
        cache.clear()
