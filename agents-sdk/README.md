# LLC Agents SDK

Python SDK for AI agents to interact with Local Latent Containers.

## Installation

```bash
# Basic installation
pip install -e .

# With LangChain integration
pip install -e ".[langchain]"

# With LlamaIndex integration
pip install -e ".[llamaindex]"

# All integrations
pip install -e ".[all]"
```

## Quick Start

```python
from llc_agents import ContainerClient, AgentSession

# Create session with agent identity
session = AgentSession(
    agent_id="research-bot-001",
    agent_name="Research Assistant",
    base_url="http://localhost:7801",
    token="your-token-here"
)

# Create client
client = ContainerClient(session)

# List containers
containers = await client.list_containers(include_stats=True)
for container in containers:
    print(f"{container.name}: {container.theme}")

# Search across containers
results = await client.search(
    query="expressionist use of color",
    containers=["expressionist-art"],
    mode="hybrid",
    k=10
)

for result in results.results:
    print(f"{result.title}: {result.snippet}")
    print(f"Score: {result.score}\n")

# Add new sources
from llc_agents.models import Source

jobs = await client.add_sources(
    container="expressionist-art",
    sources=[
        Source(
            uri="https://example.com/essay.pdf",
            title="Color Theory in Expressionism",
            modality="pdf"
        )
    ]
)

# Wait for ingestion to complete
completed_jobs = await client.wait_for_jobs([j.job_id for j in jobs])
```

## Core Concepts

### AgentSession

Manages authentication and HTTP session for an agent:

```python
session = AgentSession(
    agent_id="unique-agent-id",      # Required: tracked in logs
    agent_name="Human Readable Name", # Optional
    base_url="http://localhost:7801", # Optional (default shown)
    token="bearer-token",             # Optional (from LLC_TOKEN env)
    timeout=30.0                      # Optional (seconds)
)

# Use as context manager for automatic cleanup
async with session:
    response = await session.post("/v1/search", {...})
```

### ContainerClient

High-level interface for container operations:

```python
client = ContainerClient(session)

# List containers
containers = await client.list_containers(
    state="active",        # active, paused, archived, all
    limit=25,
    include_stats=True
)

# Get container details
container = await client.describe_container("expressionist-art")
print(container.embedder)  # "nomic-embed-multimodal-7b"
print(container.stats.document_count)

# Search
results = await client.search(
    query="color theory",
    containers=["expressionist-art"],
    mode="hybrid",  # semantic, hybrid, bm25
    k=10,
    rerank=True  # Optional quality boost
)

# Add sources
jobs = await client.add_sources(
    container="expressionist-art",
    sources=[Source(uri="https://...")],
    mode="async"  # or "blocking"
)

# Monitor jobs
status = await client.get_job_status([job.job_id])
completed = await client.wait_for_jobs([job.job_id], timeout=300)
```

### SearchBuilder

Fluent interface for complex queries:

```python
from llc_agents import SearchBuilder, SearchMode

results = await (
    SearchBuilder(client)
    .query("expressionist color theory")
    .in_containers(["expressionist-art", "bauhaus-design"])
    .with_mode(SearchMode.HYBRID)
    .with_rerank()
    .limit(20)
    .filter_modality(["text"])
    .filter_metadata({"period": "modernism"})
    .execute()
)
```

## Framework Integrations

### LangChain

```python
from llc_agents.integrations.langchain import LocalLatentRetriever
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

retriever = LocalLatentRetriever(
    agent_id="langchain-bot",
    containers=["expressionist-art"],
    base_url="http://localhost:7801",
    token="your-token",
    search_mode="hybrid",
    k=10
)

qa = RetrievalQA.from_chain_type(
    llm=OpenAI(),
    retriever=retriever,
    return_source_documents=True
)

result = qa({"query": "How did expressionists use color?"})
print(result["result"])
```

### LlamaIndex

```python
from llc_agents.integrations.llamaindex import LocalLatentRetriever
from llama_index.core import VectorStoreIndex

retriever = LocalLatentRetriever(
    agent_id="llamaindex-bot",
    containers=["expressionist-art"],
    base_url="http://localhost:7801",
    token="your-token"
)

# Use in query engine
query_engine = retriever.as_query_engine()
response = query_engine.query("expressionist color theory")
print(response)
```

## Configuration

### Environment Variables

```bash
# API endpoint
export LLC_BASE_URL="http://localhost:7801"

# Authentication token
export LLC_TOKEN="your-token-here"

# Get token from docker setup
cat ../docker/mcp_token.txt
```

### Token Management

```python
# Explicit token
session = AgentSession(agent_id="bot", token="explicit-token")

# From environment
session = AgentSession(agent_id="bot")  # Uses LLC_TOKEN

# From file
with open("../docker/mcp_token.txt") as f:
    token = f.read().strip()
session = AgentSession(agent_id="bot", token=token)
```

## Advanced Usage

### Parallel Searches

```python
import asyncio

# Search multiple containers in parallel
searches = [
    client.search(query="color theory", containers=["expressionist-art"]),
    client.search(query="geometric forms", containers=["bauhaus-design"]),
    client.search(query="light and shadow", containers=["renaissance-art"])
]

results = await asyncio.gather(*searches)
```

### Custom Request IDs

```python
from uuid import uuid4

request_id = str(uuid4())
results = await client.search(
    query="color theory",
    request_id=request_id  # Track in logs
)
```

### Error Handling

```python
import httpx

try:
    results = await client.search(query="test")
except httpx.HTTPStatusError as e:
    print(f"API error: {e.response.status_code}")
    print(e.response.json())
except httpx.ConnectError:
    print("Cannot connect to LLC backend")
except httpx.TimeoutException:
    print("Request timed out")
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=llc_agents --cov-report=html

# Run specific test
pytest tests/test_client.py::test_search
```

## Examples

See `../examples/agents/` for complete examples:
- `research_agent.py` - Autonomous research bot
- `curator_agent.py` - Container management
- `multi_agent_demo.py` - Collaboration patterns

## API Reference

### Models

All request/response models are Pydantic v2 models:

- `Container` - Container metadata
- `SearchResult` - Individual search result
- `SearchResponse` - Complete search response
- `Job` - Ingestion job status
- `Source` - Source to ingest

### Enums

- `SearchMode` - SEMANTIC, HYBRID, BM25
- `ContainerState` - ACTIVE, PAUSED, ARCHIVED, ALL
- `JobStatus` - QUEUED, RUNNING, COMPLETED, FAILED

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black llc_agents/
ruff check llc_agents/

# Type checking
mypy llc_agents/

# Run tests
pytest
```

## License

MIT

