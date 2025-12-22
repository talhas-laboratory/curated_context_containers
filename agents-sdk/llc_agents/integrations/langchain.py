"""LangChain integration for Local Latent Containers.

Provides a retriever that can be used with LangChain chains and agents.
"""

from typing import Any, List, Optional

try:
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
except ImportError:
    raise ImportError(
        "LangChain is not installed. Install with: pip install llc-agents[langchain]"
    )

from llc_agents import ContainerClient, AgentSession
from llc_agents.models import SearchMode


class LocalLatentRetriever(BaseRetriever):
    """LangChain retriever for Local Latent Containers.

    Example:
        from llc_agents.integrations.langchain import LocalLatentRetriever
        from langchain.chains import RetrievalQA
        from langchain.llms import OpenAI

        retriever = LocalLatentRetriever(
            agent_id="langchain-bot",
            containers=["expressionist-art"],
            base_url="http://localhost:7801",
            token="your-token"
        )

        qa = RetrievalQA.from_chain_type(
            llm=OpenAI(),
            retriever=retriever
        )

        result = qa({"query": "How did expressionists use color?"})
    """

    agent_id: str
    """Unique agent identifier."""

    containers: Optional[List[str]] = None
    """List of container IDs/slugs to search (searches all if None)."""

    base_url: str = "http://localhost:7801"
    """LLC API base URL."""

    token: Optional[str] = None
    """Bearer token for authentication."""

    search_mode: str = "hybrid"
    """Search mode: semantic, hybrid, or bm25."""

    k: int = 10
    """Number of results to retrieve."""

    rerank: bool = False
    """Enable reranking for improved relevance."""

    filters: Optional[dict] = None
    """Optional filters (modality, metadata)."""

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        """Initialize retriever."""
        super().__init__(**kwargs)
        
        # Create session and client
        self._session = AgentSession(
            agent_id=self.agent_id,
            base_url=self.base_url,
            token=self.token,
        )
        self._client = ContainerClient(self._session)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve documents synchronously (wrapper for async)."""
        import asyncio
        
        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._aget_relevant_documents(query))

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve documents asynchronously."""
        # Map search mode string to enum
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

        # Convert to LangChain documents
        documents = []
        for result in response.results:
            # Build metadata
            metadata = {
                "source": result.uri or result.container_name,
                "container_id": result.container_id,
                "container_name": result.container_name,
                "chunk_id": result.chunk_id,
                "doc_id": result.doc_id,
                "title": result.title,
                "score": result.score,
            }

            # Add stage scores if available
            if result.stage_scores:
                metadata["stage_scores"] = result.stage_scores

            # Add provenance if available
            if result.provenance:
                metadata.update(result.provenance)

            # Add custom metadata
            if result.meta:
                metadata["custom_meta"] = result.meta

            # Create document
            doc = Document(
                page_content=result.snippet,
                metadata=metadata,
            )
            documents.append(doc)

        return documents

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









