#!/usr/bin/env python3
"""
Curator Agent - Container management and source ingestion.

This agent demonstrates:
- Adding sources to containers
- Monitoring ingestion jobs
- Batch source processing
- Container health monitoring
"""

import asyncio
import os
import sys
from typing import List
from pathlib import Path

sdk_path = Path(__file__).parent.parent.parent / "agents-sdk"
sys.path.insert(0, str(sdk_path))

from llc_agents import ContainerClient, AgentSession
from llc_agents.models import Source


class CuratorAgent:
    """Agent that manages containers and curates sources."""

    def __init__(self, agent_id: str = "curator-bot-001", token: str = None):
        self.agent_id = agent_id
        self.token = token or os.getenv("LLC_TOKEN")
        self.session = None
        self.client = None

    async def __aenter__(self):
        self.session = AgentSession(
            agent_id=self.agent_id,
            agent_name="Curator Agent",
            token=self.token,
        )
        self.client = ContainerClient(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def add_sources(
        self,
        container: str,
        sources: List[str],
        wait_for_completion: bool = True,
    ) -> List[dict]:
        """Add sources to a container.

        Args:
            container: Container name or UUID
            sources: List of source URIs
            wait_for_completion: Whether to wait for ingestion to complete

        Returns:
            List of job results
        """
        print(f"📦 Adding {len(sources)} sources to {container}")

        # Convert URIs to Source objects
        source_objects = [Source(uri=uri) for uri in sources]

        # Submit jobs
        jobs = await self.client.add_sources(
            container=container,
            sources=source_objects,
            mode="async",
        )

        print(f"✓ Submitted {len(jobs)} ingestion jobs")
        for job in jobs:
            print(f"  • Job {job.job_id}: {job.status}")

        if wait_for_completion:
            print(f"\n⏳ Waiting for jobs to complete...")
            try:
                completed = await self.client.wait_for_jobs(
                    [j.job_id for j in jobs],
                    timeout=300.0,
                )

                print(f"\n✅ All jobs completed!")
                return [
                    {
                        "job_id": j.job_id,
                        "status": j.status,
                        "source": j.source_uri,
                    }
                    for j in completed
                ]
            except TimeoutError:
                print(f"\n⚠️  Timeout waiting for jobs")
                return []
            except RuntimeError as e:
                print(f"\n❌ Error: {e}")
                return []

        return [{"job_id": j.job_id, "status": j.status} for j in jobs]

    async def monitor_container(self, container: str):
        """Monitor container health and statistics.

        Args:
            container: Container name or UUID
        """
        print(f"📊 Monitoring container: {container}\n")

        details = await self.client.describe_container(container)

        print(f"Name: {details.name}")
        print(f"Theme: {details.theme}")
        print(f"State: {details.state}")
        print(f"Embedder: {details.embedder} v{details.embedder_version}")
        print(f"Dimensions: {details.dims}")
        print(f"Modalities: {', '.join(details.modalities)}")

        if details.stats:
            print(f"\nStatistics:")
            print(f"  Documents: {details.stats.document_count}")
            print(f"  Chunks: {details.stats.chunk_count}")
            if details.stats.text_chunks:
                print(f"  Text chunks: {details.stats.text_chunks}")
            if details.stats.image_chunks:
                print(f"  Image chunks: {details.stats.image_chunks}")
            print(f"  Size: {details.stats.size_mb:.2f} MB")
            if details.stats.last_ingest:
                print(f"  Last ingest: {details.stats.last_ingest}")

        return details

    async def batch_ingest(
        self,
        container: str,
        source_batches: List[List[str]],
        batch_delay: float = 5.0,
    ):
        """Ingest sources in batches with delays.

        Args:
            container: Container name
            source_batches: List of source URI batches
            batch_delay: Seconds to wait between batches
        """
        print(f"🔄 Batch ingestion: {len(source_batches)} batches")
        print(f"   Delay between batches: {batch_delay}s\n")

        all_jobs = []

        for i, batch in enumerate(source_batches, 1):
            print(f"Batch {i}/{len(source_batches)}: {len(batch)} sources")

            jobs = await self.add_sources(
                container,
                batch,
                wait_for_completion=False,
            )

            all_jobs.extend(jobs)

            if i < len(source_batches):
                print(f"⏸  Waiting {batch_delay}s before next batch...\n")
                await asyncio.sleep(batch_delay)

        print(f"\n✅ All batches submitted: {len(all_jobs)} total jobs")
        return all_jobs


async def main():
    """Example usage of CuratorAgent."""
    token = os.getenv("LLC_TOKEN")
    if not token:
        print("❌ Error: LLC_TOKEN not set")
        return 1

    async with CuratorAgent(token=token) as agent:
        # Example 1: Monitor a container
        print("=" * 80)
        print("Example 1: Monitor Container")
        print("=" * 80 + "\n")

        try:
            details = await agent.monitor_container("expressionist-art")
            print("\n✓ Container is healthy")
        except Exception as e:
            print(f"\n❌ Error monitoring container: {e}")
            return 1

        # Example 2: Add sources
        print("\n" + "=" * 80)
        print("Example 2: Add Sources")
        print("=" * 80 + "\n")

        # Example sources (these would be real URLs in production)
        test_sources = [
            "https://example.com/doc1.pdf",
            "https://example.com/doc2.pdf",
        ]

        print("⚠️  Note: Using example URLs that may not exist")
        print("    In production, use real URLs to documents\n")

        try:
            # Note: This will likely fail with example URLs
            # Uncomment to test with real URLs
            # results = await agent.add_sources(
            #     "expressionist-art",
            #     test_sources,
            #     wait_for_completion=True
            # )
            print("✓ Source addition demonstrated (skipped with example URLs)")
        except Exception as e:
            print(f"⚠️  Expected error with example URLs: {e}")

        print("\n✅ Curator agent demonstration complete!")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)






















