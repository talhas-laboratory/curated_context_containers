"""Graph service scaffolding."""
from __future__ import annotations

import json
import logging
from time import perf_counter
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embedder import embedding_client
from app.adapters.qdrant import qdrant_adapter
from app.adapters.neo4j import neo4j_adapter
from app.db.models import Container, Chunk, Document
from app.models.graph import (
    GraphEdge,
    GraphNode,
    GraphSchemaResponse,
    GraphSearchRequest,
    GraphSearchResponse,
    GraphUpsertRequest,
    GraphUpsertResponse,
)
from app.core.config import get_settings
from app.services import manifests, graph_nl2cypher

LOGGER = logging.getLogger(__name__)
settings = get_settings()
MAX_NODES_PER_UPSERT = 2000
MAX_EDGES_PER_UPSERT = 5000
GRAPH_NODE_COLLECTION_FMT = "c_{cid}_graph_node"


def _parse_properties(raw: Any) -> dict:
    """Normalize Neo4j property payloads into dicts."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:  # pragma: no cover - defensive parsing
            return {}
    return {}


def _maybe_uuid(value: str | None) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


async def _get_container(session: AsyncSession, container_ref: str) -> Container | None:
    stmt = select(Container).where(
        or_(
            Container.name == container_ref,
            *([Container.id == _maybe_uuid(container_ref)] if _maybe_uuid(container_ref) else []),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _graph_enabled(container: Container, manifest: dict | None) -> bool:
    manifest_graph = (manifest or {}).get("graph") or {}
    if manifest_graph.get("enabled") is False:
        return False
    return bool(manifest_graph.get("enabled") or getattr(container, "graph_enabled", True))


async def _validate_chunk_ownership(
    session: AsyncSession, container: Container, chunk_ids: set[str]
) -> tuple[bool, list[str]]:
    """Ensure provided chunk IDs belong to the container."""
    valid_ids = [UUID(cid) for cid in chunk_ids if _maybe_uuid(cid)]
    if not valid_ids and chunk_ids:
        return False, list(chunk_ids)
    if not valid_ids:
        return True, []
    stmt = select(Chunk.id).where(Chunk.container_id == container.id, Chunk.id.in_(valid_ids))
    rows = await session.execute(stmt)
    found = {str(row[0]) for row in rows.all()}
    missing = [cid for cid in chunk_ids if cid not in found]
    return len(missing) == 0, missing


def _graph_node_collection_name(container_id: str) -> str:
    return GRAPH_NODE_COLLECTION_FMT.format(cid=container_id)


def _graph_node_vector_seed_chunk_ids(container_id: str, vector: list[float], limit: int) -> list[str]:
    """Search graph node embeddings and return linked chunk ids."""
    collection = _graph_node_collection_name(container_id)
    try:
        search_fn = (
            getattr(qdrant_adapter.client, "query_points", None)
            or getattr(qdrant_adapter.client, "search_points", None)
            or getattr(qdrant_adapter.client, "search", None)
        )
        if not search_fn:
            return []
        kwargs = {
            "collection_name": collection,
            "limit": limit,
            "with_vectors": False,
            "with_payload": True,
        }
        if "query_vector" in search_fn.__code__.co_varnames or search_fn.__name__ == "search_points":
            kwargs["query_vector"] = vector
        else:
            kwargs["query"] = vector
        result = search_fn(**kwargs)
        hits = list(getattr(result, "points", None) or result or [])
        chunk_ids: set[str] = set()
        for hit in hits:
            payload = getattr(hit, "payload", None) or {}
            chunk_ids.update(payload.get("source_chunk_ids") or [])
        return list(chunk_ids)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("graph_node_vector_seed_failed container=%s", container_id, exc_info=exc)
        return []


def _as_str(value: Any) -> str | None:
    """Coerce arbitrary values to strings for graph ids."""
    if value is None:
        return None
    try:
        return str(value)
    except Exception:  # pragma: no cover - defensive
        return None


def _normalize_ids(values: list[Any]) -> list[str]:
    """Return a list of string ids, dropping non-convertible items."""
    normalized: list[str] = []
    for val in values or []:
        sval = _as_str(val)
        if sval:
            normalized.append(sval)
    return normalized


async def graph_upsert(session: AsyncSession, request: GraphUpsertRequest) -> GraphUpsertResponse:
    request_id = str(uuid4())
    container = await _get_container(session, request.container)
    manifest = (
        manifests.load_manifest(str(request.container))
        or manifests.load_manifest(str(getattr(container, "name", "")))
        or manifests.load_manifest(str(getattr(container, "id", "")))
    )
    if not container:
        return GraphUpsertResponse(
            request_id=request_id,
            issues=["CONTAINER_NOT_FOUND"],
            partial=False,
        )
    if not _graph_enabled(container, manifest):
        return GraphUpsertResponse(
            request_id=request_id,
            issues=["GRAPH_DISABLED"],
            partial=False,
        )
    if len(request.nodes) > MAX_NODES_PER_UPSERT or len(request.edges) > MAX_EDGES_PER_UPSERT:
        return GraphUpsertResponse(
            request_id=request_id,
            issues=["INVALID_PARAMS"],
            partial=False,
        )
    # Validate chunk IDs belong to container
    chunk_id_set: set[str] = set()
    for node in request.nodes:
        chunk_id_set.update(node.source_chunk_ids or [])
    for edge in request.edges:
        chunk_id_set.update(edge.source_chunk_ids or [])
    ok, missing = await _validate_chunk_ownership(session, container, chunk_id_set)
    if not ok:
        LOGGER.warning("graph_upsert_invalid_chunks missing=%s container=%s", missing, str(container.id))
        return GraphUpsertResponse(
            request_id=request_id,
            issues=["INVALID_PARAMS"],
            partial=False,
        )
    driver = neo4j_adapter.connect()
    start = perf_counter()
    inserted_nodes = 0
    inserted_edges = 0
    updated_nodes = 0
    updated_edges = 0
    cid = str(container.id)
    with driver.session() as session_:
        if request.mode == "replace":
            session_.run("MATCH (n:LLCNode {container_id:$cid}) DETACH DELETE n", {"cid": cid})
        # Upsert nodes
        for node in request.nodes:
            result = session_.run(
                """
                MERGE (n:LLCNode {node_id: $node_id, container_id: $container_id})
                ON CREATE SET n.created_at = timestamp()
                SET n.updated_at = timestamp()
                SET n.label = $label,
                    n.type = $type,
                    n.summary = $summary,
                    n.properties_json = $properties_json,
                    n.source_chunk_ids = $source_chunk_ids
                """,
                {
                    "node_id": _as_str(node.id) or "",
                    "container_id": cid,
                    "label": node.label,
                    "type": node.type,
                    "summary": node.summary,
                    "properties_json": json.dumps(node.properties or {}),
                    "source_chunk_ids": _normalize_ids(node.source_chunk_ids),
                },
            )
            summary = result.consume()
            created_nodes = getattr(summary, "nodes_created", None)
            if created_nodes is None and hasattr(summary, "counters"):
                created_nodes = summary.counters.nodes_created
            if (created_nodes or 0) > 0:
                inserted_nodes += 1
            else:
                updated_nodes += 1
        # Upsert edges
        for edge in request.edges:
            result = session_.run(
                """
                MERGE (s:LLCNode {node_id: $source, container_id: $container_id})
                MERGE (t:LLCNode {node_id: $target, container_id: $container_id})
                MERGE (s)-[r:LLCEdge {type: $type, container_id: $container_id}]->(t)
                ON CREATE SET r.created_at = timestamp()
                SET r.updated_at = timestamp()
                SET r.properties_json = $properties_json,
                    r.source_chunk_ids = $source_chunk_ids
                """,
                {
                    "source": _as_str(edge.source) or "",
                    "target": _as_str(edge.target) or "",
                    "type": edge.type or "RELATED",
                    "container_id": cid,
                    "properties_json": json.dumps(edge.properties or {}),
                    "source_chunk_ids": _normalize_ids(edge.source_chunk_ids),
                },
            )
            summary = result.consume()
            created_rels = getattr(summary, "relationships_created", None)
            if created_rels is None and hasattr(summary, "counters"):
                created_rels = summary.counters.relationships_created
            if (created_rels or 0) > 0:
                inserted_edges += 1
            else:
                updated_edges += 1
    elapsed = int((perf_counter() - start) * 1000)
    return GraphUpsertResponse(
        request_id=request_id,
        inserted_nodes=inserted_nodes,
        inserted_edges=inserted_edges,
        updated_nodes=updated_nodes,
        updated_edges=updated_edges,
        timings_ms={"graph_ms": elapsed},
        issues=[],
    )


async def graph_schema(session: AsyncSession, container_ref: str) -> GraphSchemaResponse:
    request_id = str(uuid4())
    container = await _get_container(session, container_ref)
    manifest = (
        manifests.load_manifest(str(container_ref))
        or manifests.load_manifest(str(getattr(container, "name", "")))
        or manifests.load_manifest(str(getattr(container, "id", "")))
    )
    if not container:
        return GraphSchemaResponse(request_id=request_id, issues=["CONTAINER_NOT_FOUND"])
    if not _graph_enabled(container, manifest):
        return GraphSchemaResponse(request_id=request_id, issues=["GRAPH_DISABLED"])
    driver = neo4j_adapter.connect()
    labels, rels, diagnostics = _load_schema(driver, str(container.id))
    schema_cache = getattr(container, "graph_schema", None) or {}
    return GraphSchemaResponse(
        request_id=request_id,
        schema={
            "node_labels": labels,
            "edge_types": rels,
            "cached": schema_cache,
        },
        diagnostics=diagnostics,
        issues=[],
    )


def _load_schema(driver, cid: str) -> tuple[list[str], list[str], dict]:
    with driver.session() as session_:
        labels = session_.run(
            """
            MATCH (n:LLCNode {container_id:$cid})
            UNWIND labels(n) AS l
            RETURN collect(DISTINCT l) AS labels
            """,
            {"cid": cid},
        ).single()
        rels = session_.run(
            """
            MATCH ()-[r:LLCEdge {container_id:$cid}]->()
            RETURN collect(DISTINCT type(r)) AS rels
            """,
            {"cid": cid},
        ).single()
        counts = session_.run(
            "MATCH (n:LLCNode {container_id:$cid}) RETURN count(n) AS nodes",
            {"cid": cid},
        ).single()
        edge_counts = session_.run(
            "MATCH ()-[r:LLCEdge {container_id:$cid}]->() RETURN count(r) AS edges",
            {"cid": cid},
        ).single()
    diagnostics = {
        "node_count": counts.get("nodes") if counts else 0,
        "edge_count": edge_counts.get("edges") if edge_counts else 0,
    }
    return (labels.get("labels") if labels else []), (rels.get("rels") if rels else []), diagnostics


async def graph_search(session: AsyncSession, request: GraphSearchRequest) -> GraphSearchResponse:
    request_id = str(uuid4())
    container = await _get_container(session, request.container)
    manifest = (
        manifests.load_manifest(str(request.container))
        or manifests.load_manifest(str(getattr(container, "name", "")))
        or manifests.load_manifest(str(getattr(container, "id", "")))
    )
    if not container:
        return GraphSearchResponse(request_id=request_id, issues=["CONTAINER_NOT_FOUND"])
    if not _graph_enabled(container, manifest):
        return GraphSearchResponse(request_id=request_id, issues=["GRAPH_DISABLED"])
    if request.mode == "cypher" and not settings.graph_enable_raw_cypher:
        return GraphSearchResponse(request_id=request_id, issues=["GRAPH_CYPHER_DISABLED"])
    cid = str(container.id)
    if request.expand_from_vector:
        query_text = (request.expand_from_vector or {}).get("query") if isinstance(request.expand_from_vector, dict) else None
        top_k = (request.expand_from_vector or {}).get("top_k_chunks") if isinstance(request.expand_from_vector, dict) else None
        try:
            top_k = int(top_k) if top_k is not None else 5
        except Exception:
            top_k = 5
        if not query_text:
            return GraphSearchResponse(request_id=request_id, issues=["INVALID_PARAMS"])
        try:
            vector = (await embedding_client.embed_text([query_text]))[0]
        except Exception as exc:  # pragma: no cover - runtime guard
            LOGGER.warning("graph_expand_vector_failed", exc_info=exc)
            return GraphSearchResponse(request_id=request_id, issues=["VECTOR_DOWN"], diagnostics={"mode": "expand"})
        # Vector search for seeds
        try:
            hits = await qdrant_adapter.search(session, [container.id], vector, top_k, modalities=None)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("graph_expand_qdrant_failed", exc_info=exc)
            return GraphSearchResponse(request_id=request_id, issues=["VECTOR_DOWN"], diagnostics={"mode": "expand"})
        chunk_ids = [str(chunk.id) for chunk, _doc, _score in hits]
        # Include graph-node embedding seeds
        chunk_ids.extend(_graph_node_vector_seed_chunk_ids(cid, vector, top_k))
        if not chunk_ids:
            return GraphSearchResponse(
                request_id=request_id,
                issues=["NO_HITS"],
                diagnostics={"mode": "expand", "graph_hits": 0},
            )
        graph_resp = await graph_expand_from_chunks(
            session=session,
            container_ref=str(container.id),
            chunk_ids=chunk_ids,
            max_hops=request.max_hops,
            k=min(request.k, top_k),
        )
        graph_resp.request_id = request_id
        diags = graph_resp.diagnostics or {}
        diags["strategy"] = "expand_from_vector"
        graph_resp.diagnostics = diags
        return graph_resp
    driver = neo4j_adapter.connect()
    start = perf_counter()
    cid = str(container.id)
    max_hops = max(1, min(3, int(request.max_hops)))
    k_limit = max(1, int(request.k))
    params = {"cid": cid}
    labels, rels, schema_diags = _load_schema(driver, cid)
    schema = {"node_labels": labels, "edge_types": rels}
    cypher_to_run = ""
    diagnostics: dict[str, Any] = {"mode": request.mode, "schema": schema_diags}
    use_fallback = False
    fallback_reason = None
    if request.mode == "nl":
        cypher_to_run, llm_diags, llm_issues = await graph_nl2cypher.translate_nl_to_cypher(
            query=request.query or "",
            schema=schema,
            settings=settings,
            max_hops=max_hops,
            k=k_limit,
            container_id=cid,
            meta={
                "intent": request.intent,
                "focus_node_types": request.focus_node_types,
                "focus_properties": request.focus_properties,
                "answer_shape": request.answer_shape,
                "constraints": request.constraints,
            },
        )
        diagnostics["translator"] = llm_diags
        if llm_issues:
            # Instead of failing, use fallback query
            use_fallback = True
            fallback_reason = "nl_translation_failed"
            LOGGER.info("nl2cypher_failed_using_fallback issues=%s query=%s", llm_issues, request.query)
        else:
            valid, validation_issues, validator_diags = graph_nl2cypher.validate_cypher(
                cypher_to_run, schema, max_hops, k_limit
            )
            diagnostics["validator"] = validator_diags
            if validation_issues or not valid:
                # Instead of failing, use fallback query
                use_fallback = True
                fallback_reason = "validation_failed"
                LOGGER.info("nl2cypher_validation_failed_using_fallback issues=%s query=%s", validation_issues, request.query)
    
    if use_fallback:
        cypher_to_run = graph_nl2cypher.build_fallback_cypher(cid, max_hops, k_limit, request.query)
        diagnostics["fallback"] = {"reason": fallback_reason, "used": True}
    else:
        cypher_to_run = (request.query or "").strip()
        if not cypher_to_run:
            return GraphSearchResponse(
                request_id=request_id,
                issues=["INVALID_PARAMS"],
                diagnostics=diagnostics,
            )
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    source_chunk_ids: set[str] = set()
    with driver.session() as session_:
        exec_kwargs = {}
        if settings.graph_query_timeout_ms:
            exec_kwargs["timeout"] = settings.graph_query_timeout_ms / 1000.0
        try:
            record = session_.run(cypher_to_run, params, **exec_kwargs).single()
        except Exception as exc:
            LOGGER.warning("graph_query_failed: %s", cypher_to_run[:200], exc_info=exc)
            # If we haven't already tried fallback, try it now
            if not use_fallback and request.mode == "nl":
                LOGGER.info("graph_query_failed_trying_fallback query=%s", request.query)
                fallback_cypher = graph_nl2cypher.build_fallback_cypher(cid, max_hops, k_limit, request.query)
                diagnostics["fallback"] = {"reason": "query_execution_failed", "used": True}
                try:
                    record = session_.run(fallback_cypher, params, **exec_kwargs).single()
                except Exception as fallback_exc:
                    LOGGER.warning("graph_fallback_query_also_failed", exc_info=fallback_exc)
                    elapsed = int((perf_counter() - start) * 1000)
                    return GraphSearchResponse(
                        request_id=request_id,
                        issues=["GRAPH_QUERY_INVALID"],
                        timings_ms={"graph_ms": elapsed},
                        diagnostics=diagnostics,
                    )
            else:
                elapsed = int((perf_counter() - start) * 1000)
                return GraphSearchResponse(
                    request_id=request_id,
                    issues=["GRAPH_QUERY_INVALID"],
                    timings_ms={"graph_ms": elapsed},
                    diagnostics=diagnostics,
                )
        raw_nodes = record.get("nodes") if record else []
        raw_rels = record.get("rel_maps") if record else []
        for rn in raw_nodes or []:
            node_id = _as_str(rn.get("node_id"))
            if not node_id:
                continue
            chunk_ids = _normalize_ids(rn.get("source_chunk_ids") or [])
            source_chunk_ids.update(chunk_ids)
            props = _parse_properties(rn.get("properties_json") or rn.get("properties"))
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=rn.get("label"),
                    type=rn.get("type"),
                    summary=rn.get("summary"),
                    properties=props,
                    source_chunk_ids=chunk_ids,
                    score=1.0,
                )
            )
        for rel in raw_rels or []:
            source_id = _as_str(rel.get("source"))
            target_id = _as_str(rel.get("target"))
            if not source_id or not target_id:
                continue
            chunk_ids = _normalize_ids(rel.get("source_chunk_ids") or [])
            source_chunk_ids.update(chunk_ids)
            props = _parse_properties(rel.get("properties_json") or rel.get("properties"))
            edges.append(
                GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=rel.get("type"),
                    properties=props,
                    source_chunk_ids=chunk_ids,
                    score=1.0,
                )
            )
    snippets: list[dict] = []
    if source_chunk_ids:
        chunk_stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.doc_id)
            .where(Chunk.id.in_([UUID(cid) for cid in source_chunk_ids if _maybe_uuid(cid)]))
        )
        chunk_rows = (await session.execute(chunk_stmt)).all()
        for chunk, doc in chunk_rows:
            snippets.append(
                {
                    "chunk_id": str(chunk.id),
                    "doc_id": str(chunk.doc_id),
                    "uri": doc.uri,
                    "title": doc.title,
                    "text": (chunk.text or "")[:320],
                }
            )
    elapsed = int((perf_counter() - start) * 1000)
    timings = {"graph_ms": elapsed}
    diagnostics["graph_hits"] = len(nodes)
    return GraphSearchResponse(
        request_id=request_id,
        nodes=nodes,
        edges=edges,
        snippets=snippets,
        diagnostics=diagnostics,
        timings_ms=timings,
        issues=[],
    )


async def graph_expand_from_chunks(
    session: AsyncSession,
    container_ref: str,
    chunk_ids: list[str],
    max_hops: int,
    k: int,
) -> GraphSearchResponse:
    """Expand graph context from chunk ids."""
    request_id = str(uuid4())
    container = await _get_container(session, container_ref)
    manifest = (
        manifests.load_manifest(str(container_ref))
        or manifests.load_manifest(str(getattr(container, "name", "")))
        or manifests.load_manifest(str(getattr(container, "id", "")))
    )
    if not container:
        return GraphSearchResponse(request_id=request_id, issues=["CONTAINER_NOT_FOUND"])
    if not _graph_enabled(container, manifest):
        return GraphSearchResponse(request_id=request_id, issues=["GRAPH_DISABLED"])
    if not chunk_ids:
        return GraphSearchResponse(request_id=request_id, issues=["NO_CHUNKS"])
    driver = neo4j_adapter.connect()
    start = perf_counter()
    cid = str(container.id)
    max_hops_safe = max(1, min(3, int(max_hops)))
    k_limit = max(1, int(k))
    params = {
        "cid": cid,
        "chunk_ids": [cid_ for cid_ in chunk_ids if _maybe_uuid(cid_)],
    }
    query = f"""
    MATCH (n:LLCNode {{container_id:$cid}})
    WHERE any(c IN coalesce(n.source_chunk_ids,[]) WHERE c IN $chunk_ids)
    WITH collect(DISTINCT n)[0..{k_limit}] AS seeds
    OPTIONAL MATCH path=(seed:LLCNode)-[rel:LLCEdge*1..{max_hops_safe}]-(m:LLCNode {{container_id:$cid}})
    WHERE seed IN seeds
    WITH seeds, collect(DISTINCT m)[0..{k_limit}] AS neighbors, collect(DISTINCT rel) AS rel_lists
    WITH seeds + neighbors AS nodes, rel_lists
    WITH nodes, reduce(all_rels = [], rel_list IN rel_lists | all_rels + rel_list)[0..{k_limit}] AS rels
    UNWIND nodes AS node
    WITH collect(DISTINCT node)[0..{k_limit}] AS nodes, rels
    RETURN
      [n IN nodes | {{
        node_id: n.node_id,
        label: n.label,
        type: n.type,
        summary: n.summary,
        properties_json: coalesce(n.properties_json, '{{}}'),
        source_chunk_ids: n.source_chunk_ids
      }}] AS nodes,
      [rel IN rels | {{
        source: startNode(rel).node_id,
        target: endNode(rel).node_id,
        type: type(rel),
        properties_json: coalesce(rel.properties_json, '{{}}'),
        source_chunk_ids: rel.source_chunk_ids
      }}] AS rel_maps
    """
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    source_chunk_ids: set[str] = set()
    with driver.session() as session_:
        exec_kwargs: dict[str, Any] = {}
        if settings.graph_query_timeout_ms:
            exec_kwargs["timeout"] = settings.graph_query_timeout_ms / 1000.0
        record = session_.run(query, params, **exec_kwargs).single()
        raw_nodes = record.get("nodes") if record else []
        raw_rels = record.get("rel_maps") if record else []
        for rn in raw_nodes or []:
            node_id = _as_str(rn.get("node_id"))
            if not node_id:
                continue
            chunk_ids_local = _normalize_ids(rn.get("source_chunk_ids") or [])
            source_chunk_ids.update(chunk_ids_local)
            props = _parse_properties(rn.get("properties_json") or rn.get("properties"))
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=rn.get("label"),
                    type=rn.get("type"),
                    summary=rn.get("summary"),
                    properties=props,
                    source_chunk_ids=chunk_ids_local,
                    score=1.0,
                )
            )
        for rel in raw_rels or []:
            source_id = _as_str(rel.get("source"))
            target_id = _as_str(rel.get("target"))
            if not source_id or not target_id:
                continue
            chunk_ids_local = _normalize_ids(rel.get("source_chunk_ids") or [])
            source_chunk_ids.update(chunk_ids_local)
            props = _parse_properties(rel.get("properties_json") or rel.get("properties"))
            edges.append(
                GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=rel.get("type"),
                    properties=props,
                    source_chunk_ids=chunk_ids_local,
                    score=1.0,
                )
            )
    snippets: list[dict] = []
    if source_chunk_ids:
        chunk_stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.doc_id)
            .where(Chunk.id.in_([UUID(cid) for cid in source_chunk_ids if _maybe_uuid(cid)]))
        )
        chunk_rows = (await session.execute(chunk_stmt)).all()
        for chunk, doc in chunk_rows:
            snippets.append(
                {
                    "chunk_id": str(chunk.id),
                    "doc_id": str(chunk.doc_id),
                    "uri": doc.uri,
                    "title": doc.title,
                    "text": (chunk.text or "")[:320],
                }
            )
    elapsed = int((perf_counter() - start) * 1000)
    return GraphSearchResponse(
        request_id=request_id,
        nodes=nodes,
        edges=edges,
        snippets=snippets,
        diagnostics={"mode": "expand", "graph_hits": len(nodes)},
        timings_ms={"graph_ms": elapsed},
        issues=[],
    )
