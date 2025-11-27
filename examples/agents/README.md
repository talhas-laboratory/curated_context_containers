# Agent Examples

Example AI agents demonstrating different patterns for interacting with Local Latent Containers.

## Prerequisites

1. **LLC Backend Running**
   ```bash
   cd /path/to/curated_context_containers
   make up
   ```

2. **Python SDK Installed**
   ```bash
   cd agents-sdk
   pip install -e .
   ```

3. **Token Set**
   ```bash
   export LLC_TOKEN=$(cat ../docker/mcp_token.txt)
   ```

## Examples

### 1. Research Agent (`research_agent.py`)

**Purpose:** Autonomous research across multiple containers

**Capabilities:**
- Discovers available containers
- Searches across multiple containers in parallel
- Aggregates and ranks results
- Provides timing and diagnostic information

**Usage:**
```bash
python research_agent.py
```

**Example Output:**
```
📚 Discovering available containers...

✓ Found 3 active containers:

  • expressionist-art
    Theme: German Expressionism
    Documents: 142

🔍 Researching: expressionist use of color
   Mode: Hybrid search with reranking
   Max results: 20

✓ Found 47 total hits, returning 20

⏱  Query timings:
   Vector search: 23ms
   BM25 search: 12ms
   Rerank: 45ms

📄 Research Findings (showing top 5):

1. Kandinsky — Concerning the Spiritual in Art
   Source: expressionist-art
   Score: 0.874
   The expressionists revolutionized the use of color, treating it as an independent element capable of conveying emotion...
```

### 2. Curator Agent (`curator_agent.py`)

**Purpose:** Container management and source curation

**Capabilities:**
- Monitors container health and statistics
- Adds sources to containers
- Tracks ingestion job status
- Batch processing with rate limiting

**Usage:**
```bash
python curator_agent.py
```

**Example Output:**
```
📊 Monitoring container: expressionist-art

Name: expressionist-art
Theme: German Expressionism
State: active
Embedder: google-gemma3-text v1.0.0
Dimensions: 768
Modalities: text, image

Statistics:
  Documents: 142
  Chunks: 1834
  Size: 234.50 MB
  Last ingest: 2025-11-27T20:15:00

✓ Container is healthy

📦 Adding 2 sources to expressionist-art
✓ Submitted 2 ingestion jobs
  • Job abc-123: queued
  • Job def-456: queued

⏳ Waiting for jobs to complete...
✅ All jobs completed!
```

### 3. Collaboration Demo (`collaboration_demo.py`)

**Purpose:** Multi-agent workflow demonstration

**Capabilities:**
- Discovery agent finds relevant containers
- Search agent executes queries
- Analysis agent evaluates results
- Agent-to-agent coordination

**Usage:**
```bash
python collaboration_demo.py
```

**Example Output:**
```
================================================================================
Multi-Agent Collaboration Workflow
================================================================================

Mission: Research color theory in modern art movements
Query: expressionist use of color

--- STEP 1: Container Discovery ---

[Discovery Agent] Discovering containers for mission: Research color theory in modern art movements
[Discovery Agent] Found 2 relevant containers

Top recommendations:
1. expressionist-art (relevance: 1.5)
2. bauhaus-design (relevance: 0.5)

--- STEP 2: Search Execution ---

[Search Agent] Searching: expressionist use of color
[Search Agent] Containers: ['expressionist-art', 'bauhaus-design']
[Search Agent] Found 47 results

Sample results:
1. Color Theory in Expressionism (expressionist-art)
   Score: 0.874
   Expressionists used color to convey emotion...

--- STEP 3: Result Analysis ---

[Analysis Agent] Analyzing results...
[Analysis Agent] Analysis complete: high quality results
[Analysis Agent] Average score: 0.812
[Analysis Agent] Top container: expressionist-art

Insights:
  Quality: high
  Average score: 0.812
  Best container: expressionist-art

================================================================================
✅ Collaborative workflow complete!
================================================================================
```

## Customization

### Create Your Own Agent

Use these as templates:

```python
import asyncio
from llc_agents import ContainerClient, AgentSession

class MyAgent:
    def __init__(self, agent_id: str, token: str):
        self.session = AgentSession(
            agent_id=agent_id,
            agent_name="My Custom Agent",
            token=token
        )
        self.client = ContainerClient(self.session)
    
    async def do_work(self):
        # Your agent logic here
        containers = await self.client.list_containers()
        # ...
    
    async def close(self):
        await self.session.close()

async def main():
    agent = MyAgent("my-agent-001", token="...")
    try:
        await agent.do_work()
    finally:
        await agent.close()

asyncio.run(main())
```

## Advanced Patterns

### Parallel Searches

```python
tasks = [
    client.search(query="color", containers=["art-1"]),
    client.search(query="form", containers=["art-2"]),
]
results = await asyncio.gather(*tasks)
```

### Error Handling

```python
import httpx

try:
    results = await client.search(query="test")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        print("Container not found")
    else:
        print(f"API error: {e.response.status_code}")
```

### Job Monitoring

```python
jobs = await client.add_sources(container, sources)

# Poll manually
while True:
    status = await client.get_job_status([j.job_id for j in jobs])
    if all(s.status in ["completed", "failed"] for s in status):
        break
    await asyncio.sleep(2)

# Or use helper
completed = await client.wait_for_jobs([j.job_id for j in jobs])
```

## Troubleshooting

### "Connection refused"
```bash
# Ensure backend is running
make up
```

### "Authentication failed"
```bash
# Verify token
cat ../docker/mcp_token.txt
export LLC_TOKEN=$(cat ../docker/mcp_token.txt)
```

### "Container not found"
```python
# List available containers
containers = await client.list_containers()
for c in containers:
    print(c.name)
```

## Next Steps

- Read the [Agent Quickstart Guide](../../docs/AGENT_QUICKSTART.md)
- Explore the [Python SDK](../../agents-sdk/README.md)
- Review [API Contracts](../../single_source_of_truth/architecture/API_CONTRACTS.md)

