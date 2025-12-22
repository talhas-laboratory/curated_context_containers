"""High-level client for container operations."""

import asyncio
from typing import Any, Optional
from uuid import uuid4

from llc_agents.session import AgentSession
from llc_agents.models import (
    Container,
    ContainerState,
    SearchResult,
    SearchResponse,
    SearchMode,
    Job,
    Source,
)


class ContainerClient:
    """High-level client for interacting with Local Latent Containers.

    Provides async methods for:
    - Listing and describing containers
    - Searching across containers
    - Adding sources and monitoring jobs
    - Creating and managing containers (when lifecycle API is available)

    Example:
        session = AgentSession(agent_id="bot-001", token="...")
        client = ContainerClient(session)

        # Search
        results = await client.search(
            query="expressionist color theory",
            containers=["expressionist-art"],
            k=10
        )

        # List containers
        containers = await client.list_containers(state="active")

        # Add sources
        jobs = await client.add_sources(
            container="expressionist-art",
            sources=[Source(uri="https://example.com/doc.pdf")]
        )
    """

    def __init__(self, session: AgentSession):
        """Initialize client with an agent session.

        Args:
            session: AgentSession with authentication and agent identity
        """
        self.session = session

    async def list_containers(
        self,
        state: ContainerState = ContainerState.ACTIVE,
        limit: int = 25,
        offset: int = 0,
        search: Optional[str] = None,
        include_stats: bool = True,
    ) -> list[Container]:
        """List containers with filtering.

        Args:
            state: Filter by container state
            limit: Number of containers to return (max 100)
            offset: Pagination offset
            search: Optional substring to filter names
            include_stats: Include document/chunk counts

        Returns:
            List of Container objects
        """
        response = await self.session.post(
            "/v1/containers/list",
            json={
                "state": state.value,
                "limit": limit,
                "offset": offset,
                "search": search,
                "include_stats": include_stats,
            },
        )

        data = response.json()
        containers_data = data.get("containers", [])

        return [Container(**c) for c in containers_data]

    async def describe_container(self, container: str) -> Container:
        """Get detailed metadata for a container.

        Args:
            container: Container UUID or slug name

        Returns:
            Container object with full details

        Raises:
            httpx.HTTPStatusError: If container not found (404)
        """
        response = await self.session.post(
            "/v1/containers/describe",
            json={"container": container},
        )

        data = response.json()
        container_data = data.get("container", {})

        return Container(**container_data)

    async def search(
        self,
        query: str,
        containers: Optional[list[str]] = None,
        mode: SearchMode = SearchMode.HYBRID,
        rerank: bool = False,
        k: int = 10,
        diagnostics: bool = True,
        filters: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        graph: Optional[dict[str, Any]] = None,
    ) -> SearchResponse:
        """Execute semantic/hybrid search across containers.

        Args:
            query: Search query text
            containers: List of container IDs/slugs (searches all if None)
            mode: Search mode (semantic, hybrid, bm25)
            rerank: Apply reranking for improved relevance (adds latency)
            k: Number of results to return (1-50)
            diagnostics: Include timing and scoring diagnostics
            filters: Optional filters (modality, metadata)
            request_id: Optional request ID for tracing

        Returns:
            SearchResponse with results and diagnostics

        Example:
            results = await client.search(
                query="expressionist use of color",
                containers=["expressionist-art"],
                mode=SearchMode.HYBRID,
                k=10,
                filters={"modality": ["text"]}
            )

            for result in results.results:
                print(f"{result.title}: {result.snippet}")
                print(f"Score: {result.score}")
        """
        payload = {
            "query": query,
            "mode": mode.value,
            "rerank": rerank,
            "k": k,
            "diagnostics": diagnostics,
        }

        if containers:
            payload["container_ids"] = containers

        if filters:
            payload["filters"] = filters
        if graph:
            payload["graph"] = graph

        response = await self.session.post(
            "/v1/search",
            json=payload,
            request_id=request_id,
        )

        data = response.json()
        return SearchResponse(**data)

    async def graph_search(
        self,
        container: str,
        query: str,
        mode: str = "nl",
        max_hops: int = 2,
        k: int = 20,
        diagnostics: bool = True,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Run graph/NL→Cypher search for a graph-enabled container."""
        payload = {
            "container": container,
            "query": query,
            "mode": mode,
            "max_hops": max_hops,
            "k": k,
            "diagnostics": diagnostics,
        }
        response = await self.session.post(
            "/v1/containers/graph_search",
            json=payload,
            request_id=request_id,
        )
        return response.json()

    async def graph_schema(self, container: str) -> dict[str, Any]:
        """Retrieve graph schema (labels/relationship types) for a container."""
        response = await self.session.get(
            "/v1/containers/graph_schema",
            params={"container": container},
        )
        return response.json()

    async def add_sources(
        self,
        container: str,
        sources: list[Source],
        mode: str = "async",
        timeout_ms: int = 5000,
    ) -> list[Job]:
        """Add sources to a container.

        Args:
            container: Container UUID or slug
            sources: List of Source objects to ingest
            mode: "async" (returns immediately) or "blocking" (waits for completion)
            timeout_ms: Timeout for blocking mode

        Returns:
            List of Job objects with job IDs and status

        Example:
            jobs = await client.add_sources(
                container="expressionist-art",
                sources=[
                    Source(
                        uri="https://example.com/essay.pdf",
                        title="Color Theory Essay",
                        modality="pdf"
                    )
                ]
            )

            # Poll for completion
            await client.wait_for_jobs([j.job_id for j in jobs])
        """
        payload = {
            "container": container,
            "sources": [s.model_dump(exclude_none=True) for s in sources],
            "mode": mode,
            "timeout_ms": timeout_ms,
        }

        response = await self.session.post("/v1/containers/add", json=payload)

        data = response.json()
        jobs_data = data.get("jobs", [])

        return [Job(**j) for j in jobs_data]

    async def get_job_status(self, job_ids: list[str]) -> list[Job]:
        """Get status of ingestion jobs.

        Args:
            job_ids: List of job UUIDs

        Returns:
            List of Job objects with current status
        """
        response = await self.session.post(
            "/v1/jobs/status",
            json={"job_ids": job_ids},
        )

        data = response.json()
        jobs_data = data.get("jobs", [])

        return [Job(**j) for j in jobs_data]

    async def wait_for_jobs(
        self,
        job_ids: list[str],
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> list[Job]:
        """Poll jobs until completion or timeout.

        Args:
            job_ids: List of job UUIDs to wait for
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            List of completed Job objects

        Raises:
            TimeoutError: If jobs don't complete within timeout
            RuntimeError: If any job fails
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            jobs = await self.get_job_status(job_ids)

            # Check if all completed or failed
            all_done = all(j.status in ["completed", "failed"] for j in jobs)

            if all_done:
                # Check for failures
                failed = [j for j in jobs if j.status == "failed"]
                if failed:
                    errors = [f"{j.job_id}: {j.error}" for j in failed]
                    raise RuntimeError(f"Jobs failed: {', '.join(errors)}")

                return jobs

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Jobs did not complete within {timeout}s")

            # Wait before next poll
            await asyncio.sleep(poll_interval)


class SearchBuilder:
    """Fluent builder for complex search queries.

    Example:
        results = await (
            SearchBuilder(client)
            .query("expressionist color theory")
            .in_containers(["expressionist-art", "bauhaus-design"])
            .with_mode(SearchMode.HYBRID)
            .with_rerank()
            .limit(20)
            .filter_modality(["text"])
            .execute()
        )
    """

    def __init__(self, client: ContainerClient):
        self.client = client
        self._query: Optional[str] = None
        self._containers: Optional[list[str]] = None
        self._mode: SearchMode = SearchMode.HYBRID
        self._rerank: bool = False
        self._k: int = 10
        self._diagnostics: bool = True
        self._filters: dict[str, Any] = {}

    def query(self, text: str) -> "SearchBuilder":
        """Set search query text."""
        self._query = text
        return self

    def in_containers(self, containers: list[str]) -> "SearchBuilder":
        """Set target containers."""
        self._containers = containers
        return self

    def with_mode(self, mode: SearchMode) -> "SearchBuilder":
        """Set search mode."""
        self._mode = mode
        return self

    def with_rerank(self, enabled: bool = True) -> "SearchBuilder":
        """Enable/disable reranking."""
        self._rerank = enabled
        return self

    def limit(self, k: int) -> "SearchBuilder":
        """Set result limit."""
        self._k = k
        return self

    def with_diagnostics(self, enabled: bool = True) -> "SearchBuilder":
        """Enable/disable diagnostics."""
        self._diagnostics = enabled
        return self

    def filter_modality(self, modalities: list[str]) -> "SearchBuilder":
        """Filter by modality."""
        self._filters["modality"] = modalities
        return self

    def filter_metadata(self, metadata: dict[str, Any]) -> "SearchBuilder":
        """Filter by metadata."""
        self._filters["metadata"] = metadata
        return self

    async def execute(self) -> SearchResponse:
        """Execute the search query."""
        if not self._query:
            raise ValueError("Query text is required")

        return await self.client.search(
            query=self._query,
            containers=self._containers,
            mode=self._mode,
            rerank=self._rerank,
            k=self._k,
            diagnostics=self._diagnostics,
            filters=self._filters if self._filters else None,
        )







