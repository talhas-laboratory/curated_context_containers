"""Rerank adapter with optional HTTP provider and deterministic fallback."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import httpx

from app.core.config import get_settings
from app.models.search import SearchResult

LOGGER = logging.getLogger(__name__)
settings = get_settings()


class RerankError(RuntimeError):
    """Raised when rerank provider cannot serve a request."""

    def __init__(self, message: str, issue_code: str = "RERANK_ERROR") -> None:
        super().__init__(message)
        self.issue_code = issue_code


class RerankAdapter:
    def __init__(self) -> None:
        self.api_url = getattr(settings, "rerank_api_url", "") or ""
        self.api_key = getattr(settings, "rerank_api_key", None)
        self.timeout_ms = getattr(settings, "rerank_timeout_ms", 200)

    async def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k_in: int,
        top_k_out: int,
        timeout_ms: int | None = None,
    ) -> Tuple[List[SearchResult], Dict[str, object], List[str]]:
        """Rerank candidates using an HTTP provider when configured, otherwise fallback."""
        diagnostics: Dict[str, object] = {
            "rerank_applied": False,
            "rerank_provider": self.api_url or "disabled",
            "rerank_top_k_in": top_k_in,
            "rerank_top_k_out": top_k_out,
        }
        if not candidates:
            return candidates, diagnostics, []

        # Clamp boundaries
        top_k_in = max(1, min(top_k_in or len(candidates), len(candidates)))
        top_k_out = max(1, min(top_k_out or top_k_in, top_k_in))
        timeout = (timeout_ms or self.timeout_ms) / 1000.0
        selected = candidates[:top_k_in]

        if not self.api_url:
            # No provider configured; deterministic pass-through to keep ordering stable.
            return selected[:top_k_out] + candidates[top_k_in:], diagnostics, []

        payload = {
            "query": query,
            "documents": [
                {
                    "id": cand.chunk_id,
                    "text": cand.snippet or "",
                    "title": cand.title or "",
                    "meta": cand.meta,
                }
                for cand in selected
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise RerankError(str(exc), issue_code="RERANK_TIMEOUT") from exc
        except Exception as exc:  # pragma: no cover - defensive network guard
            LOGGER.error("rerank_provider_failed", exc_info=exc)
            raise RerankError(str(exc), issue_code="RERANK_DOWN") from exc

        scored: List[tuple[str, float]] = []
        raw_results = data.get("results") or data.get("rerankings") or data.get("re_rank") or []
        for idx, item in enumerate(raw_results):
            if isinstance(item, dict):
                chunk_id = item.get("id") or item.get("chunk_id") or item.get("document_id")
                score = item.get("score")
            else:
                chunk_id = None
                score = None
            if not chunk_id:
                # Allow index-based responses if provider only returns positions.
                chunk_id = selected[idx].chunk_id if idx < len(selected) else None
            if chunk_id is None:
                continue
            try:
                score_val = float(score) if score is not None else float(len(raw_results) - idx)
            except Exception:
                score_val = float(len(raw_results) - idx)
            scored.append((str(chunk_id), score_val))

        if not scored:
            # Provider responded but lacked usable scores; do not error, keep original ordering.
            diagnostics["rerank_applied"] = False
            return selected[:top_k_out] + candidates[top_k_in:], diagnostics, []

        by_id = {res.chunk_id: res for res in selected}
        ranked: List[SearchResult] = []
        seen: set[str] = set()
        for chunk_id, _score in sorted(scored, key=lambda kv: kv[1], reverse=True):
            res = by_id.get(chunk_id)
            if res and chunk_id not in seen:
                ranked.append(res)
                seen.add(chunk_id)

        # Fill any missing (e.g., provider dropped some) preserving original order.
        for res in selected:
            if res.chunk_id not in seen:
                ranked.append(res)

        diagnostics["rerank_applied"] = True
        top_slice = ranked[:top_k_out]
        top_ids = {res.chunk_id for res in top_slice}
        reranked = top_slice + [r for r in candidates if r.chunk_id not in top_ids]
        return reranked, diagnostics, []


rerank_adapter = RerankAdapter()
