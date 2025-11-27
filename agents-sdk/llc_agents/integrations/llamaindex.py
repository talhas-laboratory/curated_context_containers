"""LlamaIndex integration for Local Latent Containers.

Provides a retriever that can be used with LlamaIndex query engines.
"""

from typing import List, Optional

try:
    from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
    from llama_index.core.retrievers import BaseRetriever
except ImportError:
    raise ImportError(
        "LlamaIndex is not installed. Install with: pip install llc-agents[llamaindex]"
    )

from llc_agents import ContainerClient, AgentSession
from llc_agents.models import SearchMode


class LocalLatentRetriever(BaseRetriever):
    """LlamaIndex retriever for Local Latent Containers.

    Example:
        from llc_agents.integrations.llamaindex import LocalLatentRetriever

        retriever = LocalLatentRetriever(
            agent_id="llamaindex-bot",
            containers=["expressionist-art"],
            base_url="http://localhost:7801",
            token="your-token"
        )

        # Use as retriever
        nodes = await retriever.aretrieve("expressionist color theory")

        # Or as query engine
        query_engine = retriever.as_query_engine()
        response = await query_engine.aquery("expressionist color theory")
    """

    def __init__(
        self,
        agent_id: str,
        containers: Optional[List[str]] = None,
        base_url: str = "http://localhost:7801",
        token: Optional[str] = None,
        search_mode: str = "hybrid",
        k: int = 10,
        rerank: bool = False,
        filters: Optional[dict] = None,
        **kwargs
    ):
        """Initialize retriever.

        Args:
            agent_id: Unique agent identifier
            containers: List of container IDs/slugs
            base_url: LLC API base URL
            token: Bearer token
            search_mode: Search mode (semantic/hybrid/bm25)
            k: Number of results
            rerank: Enable reranking
            filters: Optional filters
            **kwargs: Additional BaseRetriever parameters
        """
        super().__init__(**kwargs)
        
        self.agent_id = agent_id
        self.containers = containers
        self.search_mode = search_mode
        self.k = k
        self.rerank = rerank
        self.filters = filters

        # Create session and client
        self._session = AgentSession(
            agent_id=agent_id,
            base_url=base_url,
            token=token,
        )
        self._client = ContainerClient(self._session)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes synchronously (wrapper for async)."""
        import asyncio
        
        # Run async method
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._aretrieve(query_bundle))

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes asynchronously."""
        query = query_bundle.query_str

        # Map search mode
        mode_map = {
            "semantic": SearchMode.SEMANTIC,
            "hybrid": SearchMode.HYBRID,
            "bm25": SearchMode.BM25,
        }
        mode = mode_map.get(self.search_mode.lower(), SearchMode.HYBRID)

        # Execute search
        response = await self._client.search(
            query=query,
            containers=self.containers,
            mode=mode,
            rerank=self.rerank,
            k=self.k,
            filters=self.filters,
            diagnostics=True,
        )

        # Convert to LlamaIndex nodes
        nodes = []
        for result in response.results:
            # Build metadata
            metadata = {
                "source": result.uri or result.container_name,
                "container_id": result.container_id,
                "container_name": result.container_name,
                "chunk_id": result.chunk_id,
                "doc_id": result.doc_id,
                "title": result.title,
            }

            # Add stage scores
            if result.stage_scores:
                metadata["stage_scores"] = result.stage_scores

            # Add provenance
            if result.provenance:
                metadata.update(result.provenance)

            # Add custom metadata
            if result.meta:
                for key, value in result.meta.items():
                    metadata[f"custom_{key}"] = value

            # Create text node
            node = TextNode(
                text=result.snippet,
                id_=result.chunk_id,
                metadata=metadata,
            )

            # Wrap in NodeWithScore
            node_with_score = NodeWithScore(
                node=node,
                score=result.score,
            )
            nodes.append(node_with_score)

        return nodes

    async def cleanup(self):
        """Clean up session resources."""
        await self._session.close()


def create_retriever(
    agent_id: str,
    containers: Optional[List[str]] = None,
    base_url: str = "http://localhost:7801",
    token: Optional[str] = None,
    search_mode: str = "hybrid",
    k: int = 10,
    **kwargs
) -> LocalLatentRetriever:
    """Create a LocalLatentRetriever with simplified parameters.

    Args:
        agent_id: Unique agent identifier
        containers: List of container IDs/slugs
        base_url: LLC API base URL
        token: Bearer token
        search_mode: Search mode (semantic/hybrid/bm25)
        k: Number of results
        **kwargs: Additional retriever parameters

    Returns:
        Configured LocalLatentRetriever instance
    """
    return LocalLatentRetriever(
        agent_id=agent_id,
        containers=containers,
        base_url=base_url,
        token=token,
        search_mode=search_mode,
        k=k,
        **kwargs
    )

