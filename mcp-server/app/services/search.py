"""Search service implementing manifest-aware retrieval."""
from __future__ import annotations

import base64
import logging
import math
import inspect
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.rerank import RerankError, rerank_adapter
from app.adapters.embedder import EmbeddingError, embedding_client
from app.adapters.qdrant import qdrant_adapter
from app.core.config import get_settings
from app.core.metrics import observe_search
from app.db.models import Chunk, Container, Document
from app.models.search import SearchRequest, SearchResponse, SearchResult
from app.models.graph import GraphSearchRequest
from app.services import manifests
from app.services import graph as graph_service
from app.services.diagnostics import baseline_diagnostics, stage_timer, summarize_timings
from app.services.fusion import reciprocal_rank_fusion

settings = get_settings()
LOGGER = logging.getLogger(__name__)
DEFAULT_PRINCIPAL = "agent:local"
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "by",
    "at",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
}

SYNONYMS = {
    "expressionist": ["expressionism", "expressive"],
    "brushwork": ["stroke", "strokes", "mark"],
    "color": ["colour", "hue"],
    "colour": ["color", "hue"],
    "impasto": ["thick", "texture", "textured"],
    "broken": ["fragmented", "optical"],
    "warm": ["hot"],
    "cool": ["cold"],
    "spiritual": ["inner", "soulful"],
    "abstract": ["nonliteral", "nonobjective"],
}


def _render_snippet(chunk: Chunk) -> str:
    """Render snippet respecting offsets and provenance hints."""
    text = (chunk.text or "").strip()
    offsets = getattr(chunk, "offsets", None)
    if offsets:
        try:
            start = offsets.lower or 0
            end = offsets.upper or len(text)
            snippet_body = text[start:end] if end else text[start:]
        except Exception:
            snippet_body = text
    else:
        snippet_body = text
    snippet_body = " ".join((snippet_body or "").split())
    provenance = getattr(chunk, "provenance", {}) or {}
    prefix_parts = []
    if provenance.get("page"):
        prefix_parts.append(f"[p.{provenance['page']}]")
    if provenance.get("section"):
        prefix_parts.append(f"[{provenance['section']}]")
    prefix = " ".join(prefix_parts)
    snippet = f"{prefix} {snippet_body}".strip()
    return snippet[:320]


def _freshness_weight(provenance: dict, created_at, decay_lambda: float) -> float:
    """Compute exponential freshness weight based on ingested timestamp."""
    if not decay_lambda or decay_lambda <= 0:
        return 1.0
    ts = None
    if isinstance(created_at, datetime):
        ts = created_at
    if not ts:
        raw = (provenance or {}).get("ingested_at")
        if raw:
            try:
                ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                ts = None
    if not ts:
        return 1.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age_days = max((now - ts).total_seconds() / 86400.0, 0)
    return math.exp(-decay_lambda * age_days)


def _build_result(
    chunk: Chunk,
    doc: Document,
    container_map,
    score: float,
    stage_scores: Dict[str, float] | None = None,
) -> SearchResult:
    cont = container_map.get(chunk.container_id.hex)
    meta = chunk.meta.copy() if chunk.meta else {}
    dedup_of = getattr(chunk, "dedup_of", None)
    if dedup_of:
        meta["dedup_of"] = str(dedup_of)
    return SearchResult(
        chunk_id=str(chunk.id),
        doc_id=str(chunk.doc_id),
        container_id=str(chunk.container_id),
        container_name=cont.name if cont else None,
        title=doc.title,
        snippet=_render_snippet(chunk),
        uri=doc.uri,
        score=score,
        stage_scores=stage_scores or {},
        modality=chunk.modality,
        provenance=chunk.provenance or {},
        meta=meta,
    )


def _allowed_modalities(container: Container, manifest: dict | None) -> List[str]:
    manifest_modalities = (manifest or {}).get("modalities") or []
    return list(manifest_modalities or container.modalities or [])


def _freshness_lambda(container: Container, manifest: dict | None) -> float:
    retrieval = (manifest or {}).get("retrieval") or {}
    freshness = retrieval.get("freshness") or {}
    if freshness.get("enabled"):
        return float(freshness.get("decay_lambda", 0.0))
    policy = container.policy or {}
    return float(policy.get("freshness_lambda") or 0.0)


def _latency_budget(containers: List[Container], manifest_map: Dict[str, dict]) -> int:
    budget = settings.search_latency_budget_ms
    for c in containers:
        manifest = manifest_map.get(c.id.hex) or {}
        retrieval = manifest.get("retrieval") or {}
        budget_override = retrieval.get("latency_budget_ms")
        if budget_override:
            budget = min(budget, int(budget_override))
    return budget


def _rerank_config(retrieval_configs: Dict[str, dict]) -> dict:
    """Return the first enabled rerank config, if any."""
    for cfg in retrieval_configs.values():
        rerank_cfg = (cfg.get("rerank") or {})
        if rerank_cfg.get("enabled"):
            return rerank_cfg
    return {}


def _expand_query(query: str) -> List[str]:
    """Deterministic, lightweight query expansion."""
    if not query:
        return []
    original = query
    lowered = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in query)
    tokens = [tok for tok in lowered.split() if tok and tok not in STOPWORDS and len(tok) > 2]
    # Apply synonyms
    expanded_tokens: List[str] = []
    for tok in tokens:
        expanded_tokens.append(tok)
        for syn in SYNONYMS.get(tok, []):
            expanded_tokens.append(syn)
    keyword_variant = " ".join(dict.fromkeys(expanded_tokens))  # preserve order, dedup
    expansions = [original]
    if keyword_variant and keyword_variant != original:
        expansions.append(keyword_variant)
    # If original and keyword are same, still return at least original
    return expansions or [original]


def _keyword_overlap(query: str, text: str) -> float:
    """Compute simple keyword overlap ratio."""
    q_tokens = {tok for tok in query.lower().split() if tok not in STOPWORDS and len(tok) > 2}
    if not q_tokens:
        return 0.0
    text_tokens = {tok for tok in text.lower().split() if tok not in STOPWORDS and len(tok) > 2}
    if not text_tokens:
        return 0.0
    overlap = len(q_tokens & text_tokens) / len(q_tokens)
    return overlap


def _latency_budget_info(total_ms: int, budget: int | None = None):
    """Return diagnostic helpers for latency budget adherence."""
    budget = budget or settings.search_latency_budget_ms
    over_budget = max(total_ms - budget, 0)
    diagnostics = {
        "latency_budget_ms": budget,
        "latency_over_budget_ms": over_budget,
    }
    issues: List[str] = []
    if over_budget > 0:
        issues.append("LATENCY_BUDGET_EXCEEDED")
    return diagnostics, issues


def _apply_freshness(result: SearchResult, decay_lambda: float) -> None:
    if not decay_lambda:
        return
    weight = _freshness_weight(result.provenance, None, decay_lambda)
    if weight != 1.0:
        result.score = result.score * weight
        result.stage_scores["freshness"] = weight


def _dedup_results(results: List[SearchResult]) -> List[SearchResult]:
    unique: List[SearchResult] = []
    seen: set[str] = set()
    for res in results:
        if res.meta.get("dedup_of"):
            continue
        if res.chunk_id in seen:
            continue
        seen.add(res.chunk_id)
        unique.append(res)
    return unique


async def _bm25_stage(
    session: AsyncSession,
    request: SearchRequest,
    container_ids: List[UUID] | None,
    container_map: dict,
    modalities: Dict[str, List[str]],
) -> Tuple[List[SearchResult], List[str], object]:
    timer = stage_timer("bm25")
    stmt = select(Chunk, Document)
    stmt = stmt.join(Document, Document.id == Chunk.doc_id)
    if container_ids:
        stmt = stmt.where(Chunk.container_id.in_(container_ids))
    ts_query = None
    if request.query:
        # Use websearch_to_tsquery to avoid over-restrictive AND semantics on long natural language queries.
        ts_query = func.websearch_to_tsquery("english", request.query)
        stmt = stmt.add_columns(func.ts_rank_cd(Chunk.tsv.cast(TSVECTOR), ts_query).label("rank"))
        stmt = stmt.where(Chunk.tsv.op("@@")(ts_query))
        stmt = stmt.order_by(func.ts_rank_cd(Chunk.tsv.cast(TSVECTOR), ts_query).desc())
    else:
        stmt = stmt.order_by(Chunk.created_at.desc())
    stmt = stmt.where(Chunk.dedup_of.is_(None))
    stmt = stmt.limit(max(request.k * 2, request.k))

    rows = (await session.execute(stmt)).all()
    results: List[SearchResult] = []
    ranking: List[str] = []
    for row in rows:
        if ts_query is not None:
            chunk, doc, rank = row
            score = float(rank or 0.0)
        else:
            chunk, doc = row
            score = 0.0
        allowed = modalities.get(chunk.container_id.hex)
        if allowed and chunk.modality not in allowed:
            continue
        results.append(_build_result(chunk, doc, container_map, score, {"bm25": score}))
        ranking.append(str(chunk.id))

    timer.stop()
    return results, ranking, timer


async def _vector_stage(
    session: AsyncSession,
    request: SearchRequest,
    container_ids: List[UUID] | None,
    container_map: dict,
    modalities: Dict[str, List[str]],
    query_vector: List[float] | None = None,
) -> Tuple[List[SearchResult], List[str], object, object, List[str]]:
    embed_timer = stage_timer("embed")
    embed_issue: List[str] = []
    vector: List[float] | None = query_vector
    if vector is None:
        try:
            if request.query_image_base64:
                vector = (await embedding_client.embed_image([base64.b64decode(request.query_image_base64)]))[0]
            else:
                vector = (await embedding_client.embed_text([request.query or ""]))[0]
        except (EmbeddingError, Exception) as exc:  # pragma: no cover - defensive runtime path
            LOGGER.error("embedding_failed", exc_info=exc)
            embed_timer.stop()
            vector_timer = stage_timer("vector")
            vector_timer.stop()
            return [], [], embed_timer, vector_timer, ["VECTOR_DOWN"]
    embed_timer.stop()
    target_containers = container_ids or [UUID(hex_id) for hex_id in container_map.keys()]
    vector_timer = stage_timer("vector")
    chunk_rows = await qdrant_adapter.search(
        session,
        target_containers,
        vector,
        request.k,
        modalities=list({m for mods in modalities.values() for m in mods if m} if modalities else []),
    )
    vector_timer.stop()
    results: List[SearchResult] = []
    ranking: List[str] = []
    for chunk, doc, score in chunk_rows:
        allowed = modalities.get(chunk.container_id.hex)
        if allowed and chunk.modality not in allowed:
            continue
        results.append(_build_result(chunk, doc, container_map, score, {"vector": score}))
        ranking.append(str(chunk.id))
    return results, ranking, embed_timer, vector_timer, embed_issue


async def search_response(session: AsyncSession, request: SearchRequest) -> SearchResponse:
    request_id = str(uuid4())
    container_id_filters = request.container_ids or []
    container_uuid_filters: list[UUID] = []
    container_name_filters: list[str] = []
    for cid in container_id_filters:
        try:
            container_uuid_filters.append(UUID(cid))
        except Exception:
            container_name_filters.append(cid)
    diagnostics = baseline_diagnostics(request.mode, request.container_ids)
    if request.query_image_base64 and request.query:
        diagnostics["query_type"] = "mixed"
    elif request.query_image_base64:
        diagnostics["query_type"] = "image"
    else:
        diagnostics["query_type"] = "text"
    if request.mode == "graph":
        # Graph-only path: call graph search and return graph_context envelope.
        primary_container = request.container_ids[0] if request.container_ids else ""
        graph_req = GraphSearchRequest(
            container=primary_container,
            query=request.query,
            mode="nl",
            max_hops=(request.graph or {}).get("max_hops", 2) if request.graph else 2,
            k=request.k,
            diagnostics=request.diagnostics,
        )
        graph_resp = await graph_service.graph_search(session, graph_req)
        issues = list(graph_resp.issues)
        diagnostics.update(graph_resp.diagnostics or {})
        diagnostics["graph_hits"] = len(graph_resp.nodes)
        timings_ms = graph_resp.timings_ms or {}
        return SearchResponse(
            request_id=request_id,
            query=request.query,
            results=[],
            total_hits=0,
            returned=0,
            diagnostics=diagnostics,
            timings_ms=timings_ms,
            issues=issues or [],
            graph_context={
                "nodes": [n.model_dump() for n in graph_resp.nodes],
                "edges": [e.model_dump() for e in graph_resp.edges],
                "snippets": graph_resp.snippets,
            },
        )
    expand_timer = stage_timer("expand")
    expanded_queries = _expand_query(request.query or "")
    expand_timer.stop()
    if not expanded_queries:
        expanded_queries = [request.query or ""]
    diagnostics["expanded_queries"] = expanded_queries
    diagnostics["expansion_count"] = len(expanded_queries)
    LOGGER.info(
        "search_start",
        extra={
            "request_id": request_id,
            "mode": request.mode,
            "k": request.k,
            "containers": request.container_ids or "all",
        },
    )

    container_stmt = select(Container).where(Container.state != "archived")
    if container_uuid_filters or container_name_filters:
        predicates = []
        if container_uuid_filters:
            predicates.append(Container.id.in_(container_uuid_filters))
        if container_name_filters:
            predicates.append(Container.name.in_(container_name_filters))
        container_stmt = container_stmt.where(or_(*predicates))
    containers = (await session.execute(container_stmt)).scalars().all()
    manifest_map: Dict[str, dict] = {}
    container_map = {}
    blocked: List[str] = []
    principal = getattr(settings, "default_principal", DEFAULT_PRINCIPAL)
    for c in containers:
        manifest = manifests.load_manifest(c.name) or {}
        manifest_map[c.id.hex] = manifest
        acl_data = (manifest.get("acl") or {}) or (c.acl or {})
        acl_roles = acl_data.get("roles", acl_data)
        allowed_principals = set(acl_roles.get("owner", [])) | set(acl_roles.get("reader", []))
        if allowed_principals and principal not in allowed_principals:
            blocked.append(c.id.hex)
            continue
        container_map[c.id.hex] = c

    if blocked:
        diagnostics["blocked_containers"] = blocked
    if not container_map:
        diagnostics["containers"] = request.container_ids
        diagnostics["latency_budget_ms"] = settings.search_latency_budget_ms
        diagnostics["latency_over_budget_ms"] = 0
        response = SearchResponse(
            request_id=request_id,
            query=request.query,
            results=[],
            total_hits=0,
            returned=0,
            timings_ms={},
            diagnostics=diagnostics,
            issues=["CONTAINER_NOT_FOUND"],
        )
        observe_search(request.mode, {}, 0, request.container_ids, response.issues)
        return response

    target_container_ids = [UUID(cid) for cid in container_map.keys()]
    retrieval_configs = {cid: manifest_map[cid].get("retrieval", {}) for cid in container_map.keys()}
    latency_budget = _latency_budget(list(container_map.values()), manifest_map)
    modality_allowlist = {
        cid: _allowed_modalities(container_map[cid], manifest_map.get(cid)) for cid in container_map.keys()
    }
    freshness_lambdas = {cid: _freshness_lambda(container_map[cid], manifest_map.get(cid)) for cid in container_map.keys()}
    rerank_cfg = _rerank_config(retrieval_configs)
    rerank_enabled = request.rerank or bool(rerank_cfg.get("enabled"))
    rerank_top_k_in = int(rerank_cfg.get("top_k_in") or settings.rerank_top_k_in)
    rerank_top_k_out = int(rerank_cfg.get("top_k_out") or settings.rerank_top_k_out or request.k)
    rerank_timeout_ms = int(rerank_cfg.get("timeout_ms") or settings.rerank_timeout_ms)

    bm25_results: List[SearchResult] = []
    bm25_ranking: List[str] = []
    timers = []
    vector_results: List[SearchResult] = []
    vector_ranking: List[str] = []
    issues: List[str] = []

    # Collect results over expanded queries; include original query as-is.
    aggregate_results: Dict[str, SearchResult] = {}
    original_query = request.query or ""
    precomputed_image_vector: List[float] | None = None
    vector_stage_fn = _vector_stage
    vector_supports_query = "query_vector" in inspect.signature(vector_stage_fn).parameters
    for expanded_query in expanded_queries:
        local_request = request.model_copy(update={"query": expanded_query})

        if request.mode in ("bm25", "hybrid", "crossmodal") and local_request.query:
            bm25_results, bm25_ranking, bm25_timer = await _bm25_stage(
                session, local_request, target_container_ids, container_map, modality_allowlist
            )
            timers.append(bm25_timer)
            diagnostics["bm25_hits"] = diagnostics.get("bm25_hits", 0) + len(bm25_results)
        else:
            bm25_results = []
            bm25_ranking = []

        if request.mode in ("semantic", "hybrid", "crossmodal"):
            if request.query_image_base64 and precomputed_image_vector is None:
                # compute once for image queries
                try:
                    precomputed_image_vector = (await embedding_client.embed_image([base64.b64decode(request.query_image_base64)]))[0]
                except Exception as exc:  # pragma: no cover - runtime guard
                    LOGGER.error("embedding_failed", exc_info=exc)
                    issues.append("VECTOR_DOWN")
                    precomputed_image_vector = None
            if vector_supports_query:
                vector_results, vector_ranking, embed_timer, vector_timer, embed_issues = await vector_stage_fn(
                    session,
                    local_request,
                    target_container_ids,
                    container_map,
                    modality_allowlist,
                    query_vector=precomputed_image_vector,
                )
            else:
                vector_results, vector_ranking, embed_timer, vector_timer, embed_issues = await vector_stage_fn(
                    session,
                    local_request,
                    target_container_ids,
                    container_map,
                    modality_allowlist,
                )
            timers.extend([embed_timer, vector_timer])
            diagnostics["vector_hits"] = diagnostics.get("vector_hits", 0) + len(vector_results)
            issues.extend(embed_issues)
        else:
            vector_results = []
            vector_ranking = []

        # Fuse per expanded query.
        if request.mode == "semantic":
            combined = vector_results
        elif request.mode == "bm25":
            combined = bm25_results
        elif request.mode in ("hybrid", "crossmodal"):
            fusion_timer = stage_timer("fusion")
            fusion_scores = reciprocal_rank_fusion([bm25_ranking, vector_ranking])
            tmp: dict[str, SearchResult] = {res.chunk_id: res for res in bm25_results + vector_results}
            for chunk_id, result in tmp.items():
                if chunk_id in fusion_scores:
                    result.score = fusion_scores[chunk_id]
                    result.stage_scores["fusion"] = fusion_scores[chunk_id]
            combined = sorted(tmp.values(), key=lambda r: r.score, reverse=True)[: local_request.k]
            fusion_timer.stop()
            timers.append(fusion_timer)
        else:
            combined = bm25_results

        for res in combined:
            # Keep highest score per chunk across expansions
            prev = aggregate_results.get(res.chunk_id)
            if prev is None or res.score > prev.score:
                aggregate_results[res.chunk_id] = res

    final_results = list(aggregate_results.values())

    for res in final_results:
        decay = freshness_lambdas.get(res.container_id) or 0.0
        _apply_freshness(res, decay)
    final_results = _dedup_results(final_results)

    # Pseudo-rerank: blend vector/bm25/keyword overlap scores.
    pseudo_timer = stage_timer("pseudo_rerank")
    scored_results: List[tuple[SearchResult, float]] = []
    for res in final_results:
        bm25_score = res.stage_scores.get("bm25", 0.0)
        vec_score = res.stage_scores.get("vector", 0.0)
        overlap = _keyword_overlap(original_query, res.snippet or "")
        final_score = 0.4 * vec_score + 0.4 * bm25_score + 0.2 * overlap
        scored_results.append((res, final_score))
    scored_results.sort(key=lambda x: x[1], reverse=True)
    final_results = [res for res, _score in scored_results[: request.k]]
    pseudo_timer.stop()
    timings = summarize_timings(timers + [pseudo_timer])
    timings["expand_ms"] = expand_timer.duration_ms

    if rerank_enabled and not request.query and request.query_image_base64:
        diagnostics["rerank_applied"] = False
        diagnostics["rerank_skipped"] = "no_text_query"
        issues.append("RERANK_SKIPPED_NO_TEXT")
        rerank_enabled = False

    if rerank_enabled and final_results:
        rerank_timer = stage_timer("rerank")
        try:
            final_results, rerank_diags, rerank_issues = await rerank_adapter.rerank(
                query=request.query or "",
                candidates=final_results,
                top_k_in=rerank_top_k_in,
                top_k_out=min(rerank_top_k_out, request.k),
                timeout_ms=min(rerank_timeout_ms, latency_budget),
            )
            diagnostics.update(rerank_diags)
            issues.extend(rerank_issues)
        except RerankError as exc:
            diagnostics["rerank_applied"] = False
            diagnostics["rerank_error"] = str(exc)
            issues.append(getattr(exc, "issue_code", "RERANK_ERROR"))
        rerank_timer.stop()
        timers.append(rerank_timer)
    elif rerank_enabled:
        diagnostics["rerank_applied"] = False

    timings = summarize_timings(timers)
    timings["expand_ms"] = expand_timer.duration_ms
    graph_context = None
    if request.mode == "hybrid_graph":
        primary_container = request.container_ids[0] if request.container_ids else ""
        neighbor_k = int((request.graph or {}).get("neighbor_k") or 10)
        max_hops = int((request.graph or {}).get("max_hops") or settings.graph_max_hops_default)
        chunk_ids = [res.chunk_id for res in final_results[:neighbor_k]]
        graph_resp = await graph_service.graph_expand_from_chunks(
            session=session,
            container_ref=primary_container,
            chunk_ids=chunk_ids,
            max_hops=max_hops,
            k=neighbor_k,
        )
        graph_context = {
            "nodes": [n.model_dump() for n in graph_resp.nodes],
            "edges": [e.model_dump() for e in graph_resp.edges],
            "snippets": graph_resp.snippets,
        }
        diagnostics.update(graph_resp.diagnostics or {})
        diagnostics["graph_hits"] = len(graph_resp.nodes)
        if graph_resp.timings_ms:
            timings.update(graph_resp.timings_ms)
        issues.extend(graph_resp.issues or [])

    total_ms = timings.get("total_ms", 0)
    over_budget = max(total_ms - latency_budget, 0)
    diagnostics["containers"] = request.container_ids or list(container_map.keys())
    diagnostics["latency_budget_ms"] = latency_budget
    diagnostics["latency_over_budget_ms"] = over_budget

    if over_budget > 0:
        issues.append("LATENCY_BUDGET_EXCEEDED")
    if not final_results and "CONTAINER_NOT_FOUND" not in issues:
        issues.append("NO_HITS")

    response = SearchResponse(
        request_id=request_id,
        query=request.query,
        results=final_results,
        total_hits=len(final_results),
        returned=len(final_results),
        timings_ms=timings,
        diagnostics=diagnostics,
        issues=issues,
        partial=over_budget > 0,
        graph_context=graph_context,
    )
    observe_search(
        request.mode,
        timings,
        response.returned,
        request.container_ids or list(container_map.keys()),
        issues,
    )
    LOGGER.info(
        "search_complete",
        extra={
            "request_id": request_id,
            "mode": request.mode,
            "k": request.k,
            "containers": diagnostics.get("containers"),
            "issues": issues,
            "timings_ms": timings,
            "returned": response.returned,
        },
    )
    return response
