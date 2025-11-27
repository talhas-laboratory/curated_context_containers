#!/usr/bin/env python3
"""
Multi-Agent Collaboration Demo

Demonstrates:
- Multiple agents working together
- Container sharing and discovery
- Agent-to-agent coordination
"""

import asyncio
import os
import sys
from pathlib import Path

sdk_path = Path(__file__).parent.parent.parent / "agents-sdk"
sys.path.insert(0, str(sdk_path))

from llc_agents import ContainerClient, AgentSession


class CollaborativeAgent:
    """Base class for collaborative agents."""

    def __init__(self, agent_id: str, agent_name: str, token: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.session = AgentSession(
            agent_id=agent_id,
            agent_name=agent_name,
            token=token,
        )
        self.client = ContainerClient(self.session)

    async def close(self):
        await self.session.close()

    def log(self, message: str):
        """Log message with agent identifier."""
        print(f"[{self.agent_name}] {message}")


class DiscoveryAgent(CollaborativeAgent):
    """Agent that discovers and recommends containers."""

    async def discover_for_mission(self, mission: str) -> list:
        """Discover containers relevant to a mission."""
        self.log(f"Discovering containers for mission: {mission}")

        # List all containers
        containers = await self.client.list_containers(include_stats=True)

        # Filter by relevance (simple substring match for demo)
        relevant = []
        mission_lower = mission.lower()

        for container in containers:
            relevance_score = 0

            # Check theme
            if container.theme and any(
                word in container.theme.lower() for word in mission_lower.split()
            ):
                relevance_score += 1

            # Check name
            if any(word in container.name.lower() for word in mission_lower.split()):
                relevance_score += 0.5

            if relevance_score > 0:
                relevant.append(
                    {
                        "container": container,
                        "relevance": relevance_score,
                    }
                )

        # Sort by relevance
        relevant.sort(key=lambda x: x["relevance"], reverse=True)

        self.log(f"Found {len(relevant)} relevant containers")
        return relevant


class SearchAgent(CollaborativeAgent):
    """Agent that executes searches based on recommendations."""

    async def search_containers(self, query: str, containers: list) -> dict:
        """Search across recommended containers."""
        self.log(f"Searching: {query}")
        self.log(f"Containers: {[c.name for c in containers]}")

        results = await self.client.search(
            query=query,
            containers=[c.name for c in containers],
            k=5,
        )

        self.log(f"Found {results.total_hits} results")

        return {
            "query": query,
            "total_hits": results.total_hits,
            "results": [
                {
                    "title": r.title,
                    "container": r.container_name,
                    "score": r.score,
                    "snippet": r.snippet[:100],
                }
                for r in results.results
            ],
        }


class AnalysisAgent(CollaborativeAgent):
    """Agent that analyzes search results from other agents."""

    def analyze_results(self, search_results: dict) -> dict:
        """Analyze search results and provide insights."""
        self.log("Analyzing results...")

        results = search_results["results"]

        if not results:
            self.log("No results to analyze")
            return {"status": "no_data"}

        # Calculate statistics
        avg_score = sum(r["score"] for r in results) / len(results)
        top_containers = {}

        for result in results:
            container = result["container"]
            top_containers[container] = top_containers.get(container, 0) + 1

        analysis = {
            "total_results": len(results),
            "average_score": avg_score,
            "top_container": max(top_containers.items(), key=lambda x: x[1])[0],
            "containers_searched": list(top_containers.keys()),
            "quality": "high" if avg_score > 0.7 else "medium" if avg_score > 0.5 else "low",
        }

        self.log(f"Analysis complete: {analysis['quality']} quality results")
        self.log(f"Average score: {avg_score:.3f}")
        self.log(f"Top container: {analysis['top_container']}")

        return analysis


async def collaborative_workflow(mission: str, query: str, token: str):
    """Demonstrate multi-agent collaboration workflow."""
    print("=" * 80)
    print("Multi-Agent Collaboration Workflow")
    print("=" * 80 + "\n")

    print(f"Mission: {mission}")
    print(f"Query: {query}\n")

    # Initialize agents
    discovery = DiscoveryAgent("discovery-001", "Discovery Agent", token)
    search = SearchAgent("search-001", "Search Agent", token)
    analysis = AnalysisAgent("analysis-001", "Analysis Agent", token)

    try:
        # Step 1: Discovery agent finds relevant containers
        print("\n--- STEP 1: Container Discovery ---\n")
        relevant = await discovery.discover_for_mission(mission)

        if not relevant:
            print("\n❌ No relevant containers found")
            return

        # Print top 3 recommendations
        print(f"\nTop recommendations:")
        for i, rec in enumerate(relevant[:3], 1):
            print(f"{i}. {rec['container'].name} (relevance: {rec['relevance']})")

        # Step 2: Search agent executes query
        print("\n--- STEP 2: Search Execution ---\n")
        containers_to_search = [r["container"] for r in relevant[:3]]
        search_results = await search.search_containers(query, containers_to_search)

        # Print sample results
        print(f"\nSample results:")
        for i, result in enumerate(search_results["results"][:2], 1):
            print(f"{i}. {result['title']} ({result['container']})")
            print(f"   Score: {result['score']:.3f}")
            print(f"   {result['snippet']}...\n")

        # Step 3: Analysis agent evaluates results
        print("\n--- STEP 3: Result Analysis ---\n")
        insights = analysis.analyze_results(search_results)

        print(f"\nInsights:")
        print(f"  Quality: {insights.get('quality', 'unknown')}")
        print(f"  Average score: {insights.get('average_score', 0):.3f}")
        print(f"  Best container: {insights.get('top_container', 'none')}")

        print("\n" + "=" * 80)
        print("✅ Collaborative workflow complete!")
        print("=" * 80)

    finally:
        # Clean up
        await discovery.close()
        await search.close()
        await analysis.close()


async def main():
    """Run collaboration demo."""
    token = os.getenv("LLC_TOKEN")
    if not token:
        print("❌ Error: LLC_TOKEN not set")
        return 1

    # Example workflow
    await collaborative_workflow(
        mission="Research color theory in modern art movements",
        query="expressionist use of color",
        token=token,
    )

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

