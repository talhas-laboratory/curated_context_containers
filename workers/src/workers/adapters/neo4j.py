"""Neo4j adapter for workers (graph upsert)."""
from __future__ import annotations

import json
import logging
from typing import Any

from neo4j import GraphDatabase, Driver

from workers.config import settings

LOGGER = logging.getLogger(__name__)


class Neo4jAdapter:
    def __init__(self) -> None:
        self._uri = settings.neo4j_uri
        self._user = settings.neo4j_user
        self._password = settings.neo4j_password
        self._driver: Driver | None = None

    def connect(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        return self._driver

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def upsert(self, container_id: str, nodes: list[dict], edges: list[dict]) -> dict[str, int]:
        driver = self.connect()
        inserted_nodes = 0
        inserted_edges = 0
        with driver.session() as session:
            for node in nodes:
                session.run(
                    """
                    MERGE (n:LLCNode {node_id: $node_id, container_id: $container_id})
                ON CREATE SET n.created_at = timestamp()
                SET n.updated_at = timestamp(),
                    n.label = $label,
                    n.type = $type,
                    n.summary = $summary,
                    n.properties_json = $properties_json,
                    n.source_chunk_ids = $source_chunk_ids
                """,
                {
                    "node_id": node.get("id"),
                    "container_id": container_id,
                    "label": node.get("label"),
                    "type": node.get("type"),
                    "summary": node.get("summary"),
                    "properties_json": json.dumps(node.get("properties") or {}),
                    "source_chunk_ids": node.get("source_chunk_ids") or [],
                },
            )
            inserted_nodes += 1
            for edge in edges:
                session.run(
                    """
                    MERGE (s:LLCNode {node_id: $source, container_id: $container_id})
                    MERGE (t:LLCNode {node_id: $target, container_id: $container_id})
                MERGE (s)-[r:LLCEdge {type: $type, container_id: $container_id}]->(t)
                ON CREATE SET r.created_at = timestamp()
                SET r.updated_at = timestamp(),
                    r.properties_json = $properties_json,
                    r.source_chunk_ids = $source_chunk_ids
                """,
                {
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "type": edge.get("type") or "RELATED",
                    "container_id": container_id,
                    "properties_json": json.dumps(edge.get("properties") or {}),
                    "source_chunk_ids": edge.get("source_chunk_ids") or [],
                },
            )
            inserted_edges += 1
        return {"inserted_nodes": inserted_nodes, "inserted_edges": inserted_edges}


neo4j_adapter = Neo4jAdapter()
