"""Neo4j adapter stub for graph RAG."""
from __future__ import annotations

import logging
from typing import Any

from neo4j import GraphDatabase, Driver

from app.core.config import get_settings

LOGGER = logging.getLogger(__name__)


class Neo4jAdapter:
    def __init__(self) -> None:
        settings = get_settings()
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

    def run_query(self, query: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute Cypher query and return list of records as dicts."""
        driver = self.connect()
        with driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def healthcheck(self) -> bool:
        try:
            self.run_query("RETURN 1 AS ok")
            return True
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("neo4j_health_failed", exc_info=exc)
            return False


neo4j_adapter = Neo4jAdapter()
