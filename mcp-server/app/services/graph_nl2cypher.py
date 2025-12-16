"""Helpers for NL → Cypher translation and safety validation."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Tuple

import httpx

from app.core.config import Settings

LOGGER = logging.getLogger(__name__)

_DISALLOWED = [
    r"(?i)\bcreate\b",
    r"(?i)\bmerge\b",
    r"(?i)\bdelete\b",
    r"(?i)\bremove\b",
    r"(?i)\bdrop\b",
    r"(?i)\bset\s+",
    r"(?i)\bcall\s+db\.",
    r"(?i)apoc\.",
    r"(?i)\bload\s+csv\b",
    r"(?i)\bperiodic\b",
    r"(?i)\bindex\b",
    r"(?i)\bconstraint\b",
]


def _ensure_limit(cypher: str, k: int) -> tuple[str, bool]:
    """Ensure a LIMIT exists; append if missing."""
    if "limit" in cypher.lower():
        return cypher, False
    cypher = cypher.rstrip().rstrip(";")
    return f"{cypher}\nLIMIT {k}", True


def _strip_code_fences(text: str) -> str:
    text = text or ""
    if "```" in text:
        text = text.replace("```cypher", "```")
        if text.count("```") >= 2:
            parts = text.split("```")
            return parts[1].strip()
    return text.strip()


def _extract_first_cypher(text: str) -> str:
    """
    Heuristic: pull the first Cypher-looking block starting at the first MATCH/WITH/RETURN.
    This strips away prose the model might prepend (which can include banned words like APOC).
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"(?i)^(match|optional match|with|unwind|return|call)", ln):
            start = i
            break
    if start is None:
        return text.strip()
    return "\n".join(lines[start:]).strip()


def _strip_apoc(text: str) -> str:
    """Replace apoc.convert.toJson(...) with a simple properties() projection."""
    return re.sub(
        r"apoc\.convert\.toJson\(([^)]+)\)",
        r"properties(\1)",
        text,
        flags=re.IGNORECASE,
    )


def _build_prompt(
    query: str,
    schema: dict,
    max_hops: int,
    k: int,
    container_id: str,
    meta: dict | None = None,
) -> list[dict]:
    node_labels = schema.get("node_labels") or []
    edge_types = schema.get("edge_types") or []
    allowed_labels = ", ".join(sorted(set(node_labels + ["LLCNode"])))
    allowed_rels = ", ".join(sorted(set(edge_types + ["LLCEdge"])))
    meta = meta or {}
    intent = meta.get("intent")
    focus_nodes = meta.get("focus_node_types") or []
    focus_props = meta.get("focus_properties") or []
    answer_shape = meta.get("answer_shape")
    constraints = meta.get("constraints") or {}

    meta_lines = []
    if intent:
        meta_lines.append(f"- Intent: {intent}")
    if focus_nodes:
        meta_lines.append(f"- Focus node types: {', '.join(focus_nodes)}")
    if focus_props:
        meta_lines.append(f"- Focus properties: {', '.join(focus_props)}")
    if answer_shape:
        meta_lines.append(f"- Desired answer shape: {answer_shape}")
    if constraints:
        meta_lines.append(f"- Constraints: {constraints}")

    # Provide an example template that works
    example_cypher = f"""MATCH (n:LLCNode {{container_id: $cid}})
WHERE toLower(coalesce(n.summary, '')) CONTAINS 'keyword'
WITH collect(DISTINCT n)[0..{k}] AS seed_nodes
OPTIONAL MATCH (seed:LLCNode)-[r:LLCEdge*1..{max_hops}]-(neighbor:LLCNode {{container_id: $cid}})
WHERE seed IN seed_nodes
WITH seed_nodes + collect(DISTINCT neighbor)[0..{k}] AS all_nodes, collect(DISTINCT r) AS rel_lists
WITH all_nodes, reduce(all_rels = [], rel_list IN rel_lists | all_rels + rel_list)[0..{k}] AS rels
UNWIND all_nodes AS node
WITH collect(DISTINCT node)[0..{k}] AS nodes, rels
RETURN
  [n IN nodes | {{
    node_id: n.node_id,
    label: n.label,
    type: n.type,
    summary: n.summary,
    properties_json: coalesce(n.properties_json, '{{{{}}}}'),
    source_chunk_ids: n.source_chunk_ids
  }}] AS nodes,
  [rel IN rels | {{
    source: startNode(rel).node_id,
    target: endNode(rel).node_id,
    type: type(rel),
    properties_json: coalesce(rel.properties_json, '{{{{}}}}'),
    source_chunk_ids: rel.source_chunk_ids
  }}] AS rel_maps
LIMIT {k}"""

    system = (
        "You are a Cypher query generator for Neo4j. Generate safe, read-only queries.\n\n"
        "RULES:\n"
        "1. ALWAYS use $cid parameter to filter by container_id on ALL nodes\n"
        f"2. Use ONLY these node labels: {allowed_labels}\n"
        f"3. Use ONLY these relationship types: {allowed_rels}\n"
        "4. NEVER use APOC, CALL db.*, CREATE, MERGE, DELETE, SET, DROP, INDEX, or CONSTRAINT\n"
        f"5. Keep relationship hops <= {max_hops}\n"
        f"6. Include LIMIT {k}\n"
        "7. Return exactly two columns named 'nodes' and 'rel_maps' as lists of maps\n\n"
        "REQUIRED OUTPUT FORMAT:\n"
        "- nodes: list of maps with keys: node_id, label, type, summary, properties_json, source_chunk_ids\n"
        "- rel_maps: list of maps with keys: source, target, type, properties_json, source_chunk_ids\n\n"
        f"EXAMPLE TEMPLATE (adapt the WHERE clause for the question):\n```cypher\n{example_cypher}\n```\n\n"
        "Output ONLY the Cypher query, no explanations."
    )
    user = (
        f"Container ID: {container_id}\n"
        f"Question: {query.strip()}\n"
        + ("\n".join(meta_lines) + "\n" if meta_lines else "")
        + "\nGenerate a Cypher query that answers this question. Use text matching on n.summary or n.label fields."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def translate_nl_to_cypher(
    *,
    query: str,
    schema: dict,
    settings: Settings,
    max_hops: int,
    k: int,
    container_id: str,
    meta: dict | None = None,
) -> Tuple[str | None, dict, List[str]]:
    """Call external model to translate NL to Cypher."""
    if not settings.graph_nl2cypher_enabled or not settings.graph_nl2cypher_url:
        return None, {"reason": "disabled"}, ["NL2CYPHER_DISABLED"]
    if not query or not query.strip():
        return None, {"reason": "empty_query"}, ["INVALID_PARAMS"]

    messages = _build_prompt(query, schema, max_hops, k, container_id, meta=meta)
    payload: Dict[str, Any] = {
        "model": settings.graph_nl2cypher_model,
        "temperature": 0,
        "messages": messages,
    }
    headers = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://local-latent-containers",
        "X-Title": "Graph NL2Cypher",
    }
    if settings.graph_nl2cypher_api_key:
        headers["Authorization"] = f"Bearer {settings.graph_nl2cypher_api_key}"
    timeout = settings.graph_nl2cypher_timeout_ms / 1000.0
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(settings.graph_nl2cypher_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # pragma: no cover - runtime guard
        LOGGER.warning("nl2cypher_call_failed", exc_info=exc)
        return None, {"reason": "llm_error"}, ["NL2CYPHER_FAILED"]

    content = (
        (data.get("choices") or [{}])[0]
        .get("message", {})
        .get("content")
        if isinstance(data, dict)
        else None
    )
    if not content and isinstance(data, dict):
        content = data.get("output") or data.get("text")
    if not content and isinstance(data, dict):
        content = json.dumps(data)
    cypher = _strip_code_fences(content or "")
    if not cypher:
        return None, {"reason": "empty_llm"}, ["NL2CYPHER_FAILED"]
    cypher = _extract_first_cypher(cypher)
    cypher = _strip_apoc(cypher)
    # Ensure a LIMIT exists to satisfy safety validation
    cypher, limit_added = _ensure_limit(cypher, k)
    diags = {"model": payload["model"]}
    if limit_added:
        diags["limit_added"] = True
    return cypher, diags, []


def build_fallback_cypher(container_id: str, max_hops: int, k: int, query: str | None = None) -> str:
    """Build a simple fallback Cypher query that returns nodes and edges.
    
    This is used when NL translation fails or is disabled, providing a basic
    graph traversal that returns content matching the query terms if possible.
    """
    # Simple query that returns nodes with their relationships
    # Uses text matching on summary/label if query is provided
    if query and query.strip():
        # Extract keywords for basic text matching (escape regex special chars)
        keywords = [re.escape(w.lower()) for w in query.split() if len(w) > 2]
        if keywords:
            keyword_pattern = "|".join(keywords)
            return f"""
MATCH (n:LLCNode {{container_id: $cid}})
WHERE n.summary IS NOT NULL 
  AND (toLower(n.summary) =~ '.*({keyword_pattern}).*' 
       OR toLower(coalesce(n.label, '')) =~ '.*({keyword_pattern}).*')
WITH n
LIMIT {k}
WITH collect(n) AS seed_nodes
CALL {{
  WITH seed_nodes
  UNWIND seed_nodes AS seed
  OPTIONAL MATCH (seed)-[r:LLCEdge]-(neighbor:LLCNode {{container_id: $cid}})
  RETURN collect(DISTINCT neighbor) AS neighbors, collect(DISTINCT r) AS rels
}}
WITH seed_nodes + neighbors AS all_nodes, rels
UNWIND all_nodes AS node
WITH collect(DISTINCT node)[0..{k}] AS nodes, rels
RETURN
  [n IN nodes | {{
    node_id: n.node_id,
    label: n.label,
    type: n.type,
    summary: n.summary,
    properties_json: coalesce(n.properties_json, '{{{{}}}}'),
    source_chunk_ids: n.source_chunk_ids
  }}] AS nodes,
  [rel IN rels | {{
    source: startNode(rel).node_id,
    target: endNode(rel).node_id,
    type: type(rel),
    properties_json: coalesce(rel.properties_json, '{{{{}}}}'),
    source_chunk_ids: rel.source_chunk_ids
  }}] AS rel_maps
"""
    # Generic fallback: just return some nodes and edges
    return f"""
MATCH (n:LLCNode {{container_id: $cid}})
WITH n
LIMIT {k}
WITH collect(n) AS seed_nodes
CALL {{
  WITH seed_nodes
  UNWIND seed_nodes AS seed
  OPTIONAL MATCH (seed)-[r:LLCEdge]-(neighbor:LLCNode {{container_id: $cid}})
  RETURN collect(DISTINCT neighbor) AS neighbors, collect(DISTINCT r) AS rels
}}
WITH seed_nodes + neighbors AS all_nodes, rels
UNWIND all_nodes AS node
WITH collect(DISTINCT node)[0..{k}] AS nodes, rels
RETURN
  [n IN nodes | {{
    node_id: n.node_id,
    label: n.label,
    type: n.type,
    summary: n.summary,
    properties_json: coalesce(n.properties_json, '{{{{}}}}'),
    source_chunk_ids: n.source_chunk_ids
  }}] AS nodes,
  [rel IN rels | {{
    source: startNode(rel).node_id,
    target: endNode(rel).node_id,
    type: type(rel),
    properties_json: coalesce(rel.properties_json, '{{{{}}}}'),
    source_chunk_ids: rel.source_chunk_ids
  }}] AS rel_maps
"""


def validate_cypher(cypher: str, schema: dict, max_hops: int, k: int) -> Tuple[bool, List[str], dict]:
    """Static validation for safety before executing Cypher."""
    diagnostics: dict[str, Any] = {}
    if not cypher or not cypher.strip():
        return False, ["NL2CYPHER_INVALID"], {"reason": "empty"}
    lower = cypher.lower()
    issues: list[str] = []

    for pattern in _DISALLOWED:
        if re.search(pattern, cypher):
            issues.append("NL2CYPHER_INVALID")
            diagnostics["blocked_pattern"] = pattern
            break

    if "limit" not in lower:
        issues.append("NL2CYPHER_INVALID")
        diagnostics["missing_limit"] = True

    if "$cid" not in lower:
        issues.append("NL2CYPHER_INVALID")
        diagnostics["missing_cid"] = True

    hop_matches = re.findall(r"\*\s*(\d+)(?:\.\.(\d+))?", cypher)
    if hop_matches:
        max_seen = 0
        for start, end in hop_matches:
            if end:
                max_seen = max(max_seen, int(end))
            elif start:
                max_seen = max(max_seen, int(start))
        if max_seen > max_hops:
            issues.append("NL2CYPHER_INVALID")
            diagnostics["max_hops_exceeded"] = max_seen

    # Match node labels: look for patterns like (n:Label or (:Label
    # This regex specifically targets node patterns, not relationship patterns
    allowed_labels = set((schema.get("node_labels") or []) + ["LLCNode"])
    node_label_matches = re.findall(r"\(\s*\w*\s*:`?([A-Za-z0-9_]+)`?", cypher)
    for label in node_label_matches:
        if label not in allowed_labels:
            diagnostics.setdefault("unknown_labels", []).append(label)

    # Match relationship types: look for patterns like -[r:TYPE]- or -[:TYPE]-
    allowed_rels = set((schema.get("edge_types") or []) + ["LLCEdge"])
    rel_matches = re.findall(r"-\s*\[\s*\w*\s*:`?([A-Za-z0-9_]+)`?", cypher)
    for rel in rel_matches:
        if rel not in allowed_rels:
            diagnostics.setdefault("unknown_rels", []).append(rel)

    if issues:
        return False, list(dict.fromkeys(issues)), diagnostics
    diagnostics["validated"] = True
    return True, [], diagnostics
