# Agent Quickstart Guide

Complete guide for building AI agents that interact with Local Latent Containers.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Agent Access Patterns](#agent-access-patterns)
4. [Building Your First Agent](#building-your-first-agent)
5. [Multi-Agent Collaboration](#multi-agent-collaboration)
6. [Best Practices](#best-practices)

## Overview

Local Latent Containers provides three ways for agents to access your curated context:

1. **MCP Gateway** - For Claude Desktop, Cursor, and MCP-compatible tools
2. **Python SDK** - For programmatic agent development
3. **Framework Integrations** - LangChain and LlamaIndex support

### When to Use Each

| Access Pattern | Use Case | Pros | Cons |
|---------------|----------|------|------|
| **MCP Gateway** | Interactive agents (Claude Desktop) | Zero code, immediate use | Limited programmatic control |
| **Python SDK** | Custom agents, automation | Full control, async support | Requires coding |
| **LangChain/LlamaIndex** | RAG pipelines, chains | Framework integration | Framework dependency |

## Getting Started

### Prerequisites

1. LLC backend running at `http://localhost:7801`
2. MCP token set in your environment (`LLC_MCP_TOKEN` for gateway or `LLC_TOKEN` for SDK usage)
3. Python 3.11+ (for SDK/integrations)

### Quick Setup

```bash
# 1. Start LLC backend
cd /path/to/curated_context_containers
make up

# 2. Set environment
export LLC_BASE_URL="http://localhost:7801"
export LLC_MCP_TOKEN="your-token-here"
export LLC_TOKEN="your-token-here"
```

## Agent Access Patterns

### Pattern 1: MCP Gateway (Claude Desktop)

**Best for:** Interactive exploration, quick queries, human-in-the-loop workflows

**Setup:**
```bash
cd mcp-server-gateway
pip install -e .
```

**Configure Claude Desktop:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "local-latent-containers": {
      "command": "python",
      "args": ["-m", "llc_mcp_gateway.server"],
      "env": {
        "LLC_BASE_URL": "http://localhost:7801",
        "LLC_MCP_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Usage:**

In Claude Desktop:

> "List all available containers"

> "Search the expressionist-art container for information about color theory"

> "Add this PDF to the expressionist-art container: https://example.com/essay.pdf"

### Pattern 2: Python SDK

**Best for:** Autonomous agents, batch processing, scheduled tasks

**Setup:**
```bash
cd agents-sdk
pip install -e .
```

**Example:**

```python
import asyncio
from llc_agents import ContainerClient, AgentSession

async def main():
    # Create session with agent identity
    session = AgentSession(
        agent_id="research-bot-001",
        agent_name="Research Assistant",
        token="your-token"
    )
    
    async with session:
        client = ContainerClient(session)
        
        # Search
        results = await client.search(
            query="expressionist use of color",
            containers=["expressionist-art"],
            k=10
        )
        
        for result in results.results:
            print(f"{result.title}: {result.snippet}")

asyncio.run(main())
```

### Pattern 3: LangChain Integration

**Best for:** RAG pipelines, question answering, chains

**Setup:**
```bash
pip install -e "agents-sdk[langchain]"
```

**Example:**

```python
from llc_agents.integrations.langchain import LocalLatentRetriever
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

retriever = LocalLatentRetriever(
    agent_id="langchain-qa",
    containers=["expressionist-art"],
    token="your-token"
)

qa = RetrievalQA.from_chain_type(
    llm=OpenAI(),
    retriever=retriever
)

result = qa({"query": "How did expressionists use color?"})
print(result["result"])
```

## Building Your First Agent

### Example: Research Assistant

This agent autonomously researches a topic by:
1. Discovering relevant containers
2. Searching across them
3. Synthesizing findings
4. Adding new sources it discovers

**File:** `examples/agents/research_agent.py`

```python
import asyncio
from typing import List
from llc_agents import ContainerClient, AgentSession, SearchMode

class ResearchAgent:
    """Autonomous research agent."""
    
    def __init__(self, agent_id: str, token: str):
        self.session = AgentSession(agent_id=agent_id, token=token)
        self.client = ContainerClient(self.session)
    
    async def research(self, topic: str, max_sources: int = 20):
        """Research a topic across all containers."""
        print(f"🔍 Researching: {topic}")
        
        # 1. Discover containers
        containers = await self.client.list_containers(state="active")
        print(f"📚 Found {len(containers)} containers")
        
        # 2. Search across all containers
        results = await self.client.search(
            query=topic,
            containers=[c.name for c in containers],
            mode=SearchMode.HYBRID,
            k=max_sources,
            rerank=True
        )
        
        # 3. Analyze results
        findings = []
        for result in results.results:
            findings.append({
                "source": result.container_name,
                "title": result.title,
                "snippet": result.snippet,
                "score": result.score,
                "uri": result.uri
            })
        
        return findings
    
    async def close(self):
        await self.session.close()

# Usage
async def main():
    agent = ResearchAgent(
        agent_id="research-bot-001",
        token="your-token"
    )
    
    findings = await agent.research("expressionist color theory")
    
    print("\n📊 Research Findings:")
    for f in findings[:5]:
        print(f"\n{f['title']} ({f['source']})")
        print(f"  {f['snippet'][:100]}...")
        print(f"  Score: {f['score']:.3f}")
    
    await agent.close()

asyncio.run(main())
```

### Example: Container Curator

This agent manages container lifecycles:

```python
from llc_agents import ContainerClient, AgentSession
from llc_agents.models import Source

class CuratorAgent:
    """Agent that creates and manages containers."""
    
    def __init__(self, agent_id: str, token: str):
        self.session = AgentSession(agent_id=agent_id, token=token)
        self.client = ContainerClient(self.session)
    
    async def curate_topic(self, topic: str, sources: List[str]):
        """Create a container and populate it with sources."""
        
        # Create container (requires lifecycle API)
        print(f"📦 Creating container for: {topic}")
        
        # Note: This uses the new lifecycle API
        # For now, containers are created via manifests
        
        # Add sources
        source_objects = [Source(uri=uri) for uri in sources]
        jobs = await self.client.add_sources(
            container=topic.lower().replace(" ", "-"),
            sources=source_objects
        )
        
        print(f"⏳ Submitted {len(jobs)} ingestion jobs")
        
        # Wait for completion
        await self.client.wait_for_jobs([j.job_id for j in jobs])
        
        print(f"✅ Container ready!")
```

## Multi-Agent Collaboration

### Pattern: Shared Containers

Multiple agents can collaborate by sharing containers:

```python
# Agent 1: Creates container and adds initial sources
agent1 = ResearchAgent("researcher-001", token)
await agent1.setup_container("modern-art")

# Agent 2: Discovers and adds to existing container
agent2 = CuratorAgent("curator-001", token)
containers = await agent2.client.list_containers(
    state="active",
    search="modern-art"
)

if containers:
    await agent2.add_sources(
        containers[0].name,
        ["https://new-source.com/doc.pdf"]
    )
```

### Pattern: Container Links

Agents can link related containers:

```python
# Link containers to show relationships
from httpx import AsyncClient

async with AsyncClient() as client:
    response = await client.post(
        "http://localhost:7801/v1/collaboration/link",
        json={
            "source_container": "expressionist-art",
            "target_container": "bauhaus-design",
            "relationship": "influenced_by"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
```

### Pattern: Subscriptions

Agents can subscribe to container updates:

```python
# Subscribe to notifications
response = await client.post(
    "http://localhost:7801/v1/collaboration/subscribe",
    json={
        "container": "expressionist-art",
        "events": ["source_added", "source_removed"],
        "webhook_url": "https://my-agent.com/webhook"
    },
    headers={
        "Authorization": f"Bearer {token}",
        "X-Agent-ID": "monitor-bot-001"
    }
)
```

## Best Practices

### 1. Agent Identity

Always provide meaningful agent IDs and names:

```python
# ✅ Good
session = AgentSession(
    agent_id="research-bot-001",
    agent_name="Art History Research Assistant"
)

# ❌ Bad
session = AgentSession(agent_id="agent1")
```

### 2. Error Handling

Handle API errors gracefully:

```python
import httpx

try:
    results = await client.search(query="test")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        print("Container not found")
    elif e.response.status_code == 401:
        print("Authentication failed")
    else:
        print(f"API error: {e.response.status_code}")
```

### 3. Resource Cleanup

Always close sessions:

```python
# Use context manager
async with AgentSession(agent_id="bot") as session:
    client = ContainerClient(session)
    # ... do work ...
# Session automatically closed

# Or manual cleanup
session = AgentSession(agent_id="bot")
try:
    # ... do work ...
finally:
    await session.close()
```

### 4. Respect Latency Budgets

Use diagnostics to monitor performance:

```python
results = await client.search(
    query="test",
    diagnostics=True
)

print(f"Total time: {results.timings_ms.get('total', 0)}ms")
if results.timings_ms.get('total', 0) > 900:
    print("⚠️  Query exceeded latency budget")
```

### 5. Batch Operations

Process multiple operations in parallel:

```python
import asyncio

# Search multiple containers in parallel
searches = [
    client.search(query="color", containers=["art-1"]),
    client.search(query="form", containers=["art-2"]),
    client.search(query="light", containers=["art-3"])
]

results = await asyncio.gather(*searches)
```

### 6. Mission Context

When creating containers, provide mission context:

```python
# This helps other agents discover relevant containers
await create_container(
    name="renaissance-perspective",
    theme="Renaissance perspective techniques",
    mission_context="Research mathematical foundations of perspective in Renaissance art for educational visualization project"
)
```

## Advanced Topics

### Custom Agents with LangChain

```python
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.llms import OpenAI

retriever = LocalLatentRetriever(
    agent_id="langchain-agent",
    containers=["expressionist-art"]
)

tools = [
    Tool(
        name="Search Art History",
        func=lambda q: retriever.get_relevant_documents(q),
        description="Search art history knowledge base"
    )
]

agent = create_react_agent(OpenAI(), tools)
executor = AgentExecutor(agent=agent, tools=tools)

result = executor.invoke({"input": "Compare color use in Expressionism vs Impressionism"})
```

### Autonomous Container Management

```python
class AutonomousAgent:
    """Agent that manages its own containers based on missions."""
    
    async def execute_mission(self, mission: str):
        # 1. Check if relevant container exists
        containers = await self.recommend_containers(mission)
        
        if not containers:
            # 2. Create new container
            container = await self.create_container_for_mission(mission)
        else:
            container = containers[0]
        
        # 3. Search for information
        results = await self.search(mission, container)
        
        # 4. If gaps exist, add new sources
        if self.has_knowledge_gaps(results):
            await self.expand_container(container, mission)
        
        return results
```

## Next Steps

- **Examples**: See `examples/agents/` for complete implementations
- **API Reference**: Read `agents-sdk/README.md` for full API docs
- **Architecture**: Review `single_source_of_truth/architecture/ADR/005_agent_access.md`

## Troubleshooting

### "Connection refused"

Ensure LLC backend is running:
```bash
cd /path/to/curated_context_containers
make up
```

### "Authentication failed"

Verify token:
```bash
export LLC_TOKEN="your-token-here"
```

### "Container not found"

List available containers:
```python
containers = await client.list_containers()
for c in containers:
    print(c.name)
```

## Support

For issues and questions:
- **Documentation**: `single_source_of_truth/`
- **Examples**: `examples/agents/`
- **API Contracts**: `single_source_of_truth/architecture/API_CONTRACTS.md`






















