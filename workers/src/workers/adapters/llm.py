"""OpenRouter LLM adapter for graph extraction."""
from __future__ import annotations

import json
import structlog
from typing import Any, Tuple

import requests

from workers.config import settings

LOGGER = structlog.get_logger()


def _clean_relation_type(rel_type: str) -> str:
    allowed = {
        "WORKS_ON",
        "OWNS",
        "MANAGES",
        "AUTHORED_BY",
        "MENTIONS",
        "USES",
        "DEPENDS_ON",
        "HAS_DECISION",
        "AFFECTS",
        "PART_OF",
        "IMPLEMENTS",
        "RELATED_TO",
    }
    normalized = (rel_type or "").upper()
    return normalized if normalized in allowed else "RELATED_TO"


def _clean_entity_type(entity_type: str) -> str:
    allowed = {
        "Person",
        "Organization",
        "Project",
        "Document",
        "Decision",
        "Product",
        "Team",
        "Risk",
        "Concept",
        "Other",
    }
    if entity_type in allowed:
        return entity_type
    return "Concept"


SYSTEM_PROMPT = """You are the Graph Extraction Engine for the Local Latent Containers system.
- Read short text chunks and emit ONLY structured JSON describing entities and relations.
- The graph is container-scoped; chunk_ids provide provenance and must be preserved.
- Entity ids are lowercase_snake_case and stable within the request. Prefer concise ids, e.g., project_graphos.
- Relation types must be one of: WORKS_ON, OWNS, MANAGES, AUTHORED_BY, MENTIONS, USES, DEPENDS_ON, HAS_DECISION, AFFECTS, PART_OF, IMPLEMENTS, RELATED_TO (fallback).
- Do NOT invent chunk_ids. If no entities/relations are evident, return {"entities": [], "relations": []}.
Output JSON ONLY; no comments or prose."""


def _user_prompt(container_id: str, document_id: str, chunk_id: str, chunk_text: str) -> str:
    return f"""Context:
- container_id: "{container_id}"
- document_id: "{document_id}"

Chunk:
[chunk_id={chunk_id}]
{chunk_text}

Extract entities and relations that are clearly supported by this chunk.
JSON schema:
{{
  "entities": [{{"id": "...", "name": "...", "type": "...", "description": "...", "source_chunk_ids": ["{chunk_id}"]}}],
  "relations": [{{"source_id": "...", "target_id": "...", "type": "...", "description": "...", "source_chunk_ids": ["{chunk_id}"]}}]
}}

Return JSON with keys "entities" and "relations" only."""


def call_llm_for_graph(
    *,
    container_id: str,
    document_id: str,
    chunk_id: str,
    chunk_text: str,
) -> Tuple[list[dict], list[dict]]:
    """Invoke OpenRouter to extract entities/relations from a chunk."""
    if not settings.openrouter_api_key or not settings.graph_llm_enabled:
        return [], []
    text = (chunk_text or "")[:4000]  # keep prompt bounded
    if not text.strip():
        return [], []
    payload: dict[str, Any] = {
        "model": settings.graph_llm_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(container_id, document_id, chunk_id, text)},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://local-latent-containers",
        "X-Title": "Graph Extraction",
    }
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=settings.graph_llm_timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = json.loads(content)
    except Exception as exc:  # pragma: no cover - runtime guard
        LOGGER.warning("graph_llm_call_failed", error=str(exc))
        return [], []
    entities: list[dict] = []
    relations: list[dict] = []
    for ent in parsed.get("entities", []) or []:
        ent_id = ent.get("id") or ent.get("name")
        if not ent_id:
            continue
        entities.append(
            {
                "id": str(ent_id),
                "label": ent.get("name") or str(ent_id),
                "type": _clean_entity_type(ent.get("type") or ""),
                "summary": ent.get("description") or ent.get("name"),
                "source_chunk_ids": ent.get("source_chunk_ids") or [chunk_id],
                "properties": {"source": "llm"},
            }
        )
    for rel in parsed.get("relations", []) or []:
        src = rel.get("source_id")
        tgt = rel.get("target_id")
        if not src or not tgt:
            continue
        relations.append(
            {
                "source": src,
                "target": tgt,
                "type": _clean_relation_type(rel.get("type") or ""),
                "properties": {
                    "source": "llm",
                    "description": rel.get("description") or "",
                },
                "source_chunk_ids": rel.get("source_chunk_ids") or [chunk_id],
            }
        )
    return entities, relations
