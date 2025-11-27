#!/usr/bin/env python3
"""
Research Agent - Autonomous research assistant that searches across containers.

This agent demonstrates:
- Discovering containers
- Parallel searching across multiple containers
- Result aggregation and ranking
- Dynamic source discovery
"""

import asyncio
import os
import sys
from typing import List, Dict, Any
from pathlib import Path

# Add agents-sdk to path
sdk_path = Path(__file__).parent.parent.parent / "agents-sdk"
sys.path.insert(0, str(sdk_path))

from llc_agents import ContainerClient, AgentSession, SearchMode


class ResearchAgent:
    """Autonomous research agent that explores and synthesizes information."""

    def __init__(self, agent_id: str = "research-bot-001", token: str = None):
        """Initialize research agent.

        Args:
            agent_id: Unique agent identifier
            token: Bearer token (defaults to LLC_TOKEN env var)
        """
        self.agent_id = agent_id
        self.token = token or os.getenv("LLC_TOKEN")
        self.session = None
        self.client = None

    async def __aenter__(self):
        """Context manager entry."""
        self.session = AgentSession(
            agent_id=self.agent_id,
            agent_name="Research Assistant",
            token=self.token,
        )
        self.client = ContainerClient(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()

    async def discover_containers(self) -> List[Dict[str, Any]]:
        """Discover all available containers.

        Returns:
            List of container metadata dictionaries
        """
        print("📚 Discovering available containers...")

        containers = await self.client.list_containers(
            state="active",
            include_stats=True,
        )

        print(f"\n✓ Found {len(containers)} active containers:\n")
        for c in containers:
            stats = c.stats
            doc_count = stats.document_count if stats else 0
            print(f"  • {c.name}")
            print(f"    Theme: {c.theme}")
            print(f"    Documents: {doc_count}")
            print()

        return [
            {
                "id": c.id,
                "name": c.name,
                "theme": c.theme,
                "modalities": c.modalities,
            }
            for c in containers
        ]

    async def research_topic(
        self,
        topic: str,
        containers: List[str] = None,
        max_results: int = 20,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """Research a topic across containers.

        Args:
            topic: Research query
            containers: List of container names to search (searches all if None)
            max_results: Maximum number of results to return
            use_rerank: Whether to use reranking for improved relevance

        Returns:
            List of research findings with scores and sources
        """
        print(f"🔍 Researching: {topic}")
        print(f"   Mode: Hybrid search {'with reranking' if use_rerank else ''}")
        print(f"   Max results: {max_results}\n")

        response = await self.client.search(
            query=topic,
            containers=containers,
            mode=SearchMode.HYBRID,
            k=max_results,
            rerank=use_rerank,
            diagnostics=True,
        )

        print(f"✓ Found {response.total_hits} total hits, returning {response.returned}\n")

        if response.diagnostics:
            timings = response.diagnostics
            print(f"⏱  Query timings:")
            print(f"   Vector search: {timings.get('vector_ms', 0)}ms")
            print(f"   BM25 search: {timings.get('bm25_ms', 0)}ms")
            if use_rerank:
                print(f"   Rerank: {timings.get('rerank_ms', 0)}ms")
            print()

        findings = []
        for result in response.results:
            findings.append(
                {
                    "container": result.container_name,
                    "title": result.title,
                    "snippet": result.snippet,
                    "score": result.score,
                    "uri": result.uri,
                    "stage_scores": result.stage_scores,
                }
            )

        return findings

    async def deep_dive(self, topic: str, container: str, depth: int = 3) -> Dict[str, Any]:
        """Perform a deep dive on a specific topic within a container.

        Args:
            topic: Research topic
            container: Container name to search
            depth: Number of follow-up queries to perform

        Returns:
            Dictionary with initial findings and related topics
        """
        print(f"🔬 Deep dive: {topic} in {container}")
        print(f"   Depth: {depth} levels\n")

        # Initial search
        initial_findings = await self.research_topic(
            topic,
            containers=[container],
            max_results=10,
        )

        print(f"\n📊 Deep dive complete!")
        print(f"   Initial findings: {len(initial_findings)}")

        return {
            "topic": topic,
            "container": container,
            "initial_findings": initial_findings,
        }

    async def parallel_research(
        self, topics: List[str], container: str = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Research multiple topics in parallel.

        Args:
            topics: List of research topics
            container: Optional container to focus on

        Returns:
            Dictionary mapping topics to findings
        """
        print(f"🚀 Parallel research: {len(topics)} topics")
        if container:
            print(f"   Focused on: {container}")
        print()

        # Create search tasks
        tasks = [
            self.research_topic(
                topic,
                containers=[container] if container else None,
                max_results=10,
                use_rerank=False,  # Faster for parallel
            )
            for topic in topics
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks)

        # Map results to topics
        findings_by_topic = {topic: findings for topic, findings in zip(topics, results)}

        print(f"\n✓ Parallel research complete!")
        for topic, findings in findings_by_topic.items():
            print(f"   {topic}: {len(findings)} findings")

        return findings_by_topic

    def print_findings(self, findings: List[Dict[str, Any]], max_display: int = 5):
        """Pretty-print research findings.

        Args:
            findings: List of finding dictionaries
            max_display: Maximum number of findings to display
        """
        print(f"\n📄 Research Findings (showing top {max_display}):\n")

        for i, finding in enumerate(findings[:max_display], 1):
            print(f"{i}. {finding['title']}")
            print(f"   Source: {finding['container']}")
            print(f"   Score: {finding['score']:.3f}")
            print(f"   {finding['snippet'][:150]}...")
            if finding.get("uri"):
                print(f"   URI: {finding['uri']}")
            print()


async def main():
    """Example usage of ResearchAgent."""
    # Get token from environment
    token = os.getenv("LLC_TOKEN")
    if not token:
        print("❌ Error: LLC_TOKEN environment variable not set")
        print("   Set it with: export LLC_TOKEN=$(cat docker/mcp_token.txt)")
        return 1

    async with ResearchAgent(token=token) as agent:
        # Example 1: Discover containers
        print("=" * 80)
        print("Example 1: Container Discovery")
        print("=" * 80 + "\n")

        containers = await agent.discover_containers()

        if not containers:
            print("❌ No containers found. Please create some containers first.")
            return 1

        # Example 2: Single topic research
        print("\n" + "=" * 80)
        print("Example 2: Single Topic Research")
        print("=" * 80 + "\n")

        findings = await agent.research_topic(
            "expressionist use of color",
            max_results=10,
            use_rerank=True,
        )

        agent.print_findings(findings)

        # Example 3: Parallel research
        print("\n" + "=" * 80)
        print("Example 3: Parallel Multi-Topic Research")
        print("=" * 80 + "\n")

        topics = [
            "color theory",
            "geometric forms",
            "light and shadow",
        ]

        parallel_findings = await agent.parallel_research(topics)

        for topic, findings in parallel_findings.items():
            print(f"\n{topic.upper()}:")
            agent.print_findings(findings, max_display=2)

        print("\n✅ Research complete!")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

