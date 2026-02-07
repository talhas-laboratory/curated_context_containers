from __future__ import annotations

from typing import Any

from app.adapters.qdrant import qdrant_adapter


def run_qdrant_migrations() -> dict[str, Any]:
    """Best-effort Qdrant "migrations".

    Today the system creates collections lazily during ingest/search, so the
    main value here is sanity-checking connectivity and reporting state.
    """
    collections = qdrant_adapter.client.get_collections()
    names = [c.name for c in (collections.collections or [])]
    return {"collection_count": len(names), "collections": names[:25]}

