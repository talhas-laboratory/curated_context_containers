"""Local Latent Containers - Python SDK for AI Agents.

This SDK provides a high-level Python interface for AI agents to interact
with Local Latent Containers, enabling autonomous search, ingestion, and
container management.

Example usage:
    from llc_agents import ContainerClient, AgentSession

    session = AgentSession(
        agent_id="research-bot-001",
        base_url="http://localhost:7801",
        token="your-token"
    )

    client = ContainerClient(session)

    # Search across containers
    results = await client.search(
        query="expressionist use of color",
        containers=["expressionist-art"],
        mode="hybrid"
    )

    # List containers
    containers = await client.list_containers(include_stats=True)

    # Add sources
    jobs = await client.add_sources(
        container="expressionist-art",
        sources=[{"uri": "https://example.com/doc.pdf"}]
    )
"""

from llc_agents.client import ContainerClient
from llc_agents.session import AgentSession
from llc_agents.models import (
    Container,
    SearchResult,
    Job,
    SearchMode,
    ContainerLifecycleResponse,
)

__version__ = "0.1.0"

__all__ = [
    "ContainerClient",
    "AgentSession",
    "Container",
    "SearchResult",
    "Job",
    "SearchMode",
    "ContainerLifecycleResponse",
]





















