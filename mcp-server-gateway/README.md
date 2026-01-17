# Local Latent Containers — MCP Gateway

MCP (Model Context Protocol) server that exposes Local Latent Containers API as tools for AI agents.

## What This Does

This gateway allows AI agents (Claude Desktop, Cursor, custom agents) to:
- **Discover containers** via `containers_list`
- **Get container details** via `containers_describe`
- **Search semantically** across containers via `containers_search`
- **Add new sources** dynamically via `containers_add`
- **Monitor ingestion jobs** via `jobs_status`

## Installation

### Prerequisites

- Python 3.11+
- LLC backend running at `http://localhost:7801` (local) or `http://llc.<tailnet>/api` (Tailscale)
- `LLC_MCP_TOKEN` set in your environment (same token configured on the server)

### Setup

```bash
# Install the gateway
cd mcp-server-gateway
pip install -e .

# Set environment variables
export LLC_BASE_URL="http://localhost:7801"
export LLC_MCP_TOKEN="your-token-here"

# Test the server
python -m llc_mcp_gateway.server
```

## Claude Desktop Integration

### Step 1: Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "local-latent-containers": {
      "command": "python",
      "args": [
        "-m",
        "llc_mcp_gateway.server"
      ],
      "env": {
        "LLC_BASE_URL": "http://localhost:7801",
        "LLC_MCP_TOKEN": "your-token-here"
      }
    }
  }
}
```

### Step 2: Get Your Token

Use the same token configured on the server (for home server deployments this
is stored in `docker/.env.home` on the server or your secrets manager). Set it
in Claude Desktop and restart the app.

### Step 3: Restart Claude Desktop

Quit and restart Claude Desktop. The MCP server will start automatically when Claude launches.

### Step 4: Verify

In Claude Desktop, you should now see LLC tools available. Try:

> "List all available containers"

> "Search the expressionist-art container for information about color theory"

## Cursor Integration

Add to your Cursor settings (`.cursor/config.json` or settings UI):

```json
{
  "mcp": {
    "servers": {
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
}
```

### Remote (Tailscale) Example

If the server is only reachable via Tailscale, point the gateway at the
reverse proxy path:

```bash
export LLC_BASE_URL="http://llc.<tailnet>/api"
export LLC_MCP_TOKEN="your-token-here"
python -m llc_mcp_gateway.server
```

## Available Tools

### `containers_list`

List available containers with filtering and pagination.

**Example:**
```
List all active containers with statistics
```

### `containers_describe`

Get detailed metadata for a specific container.

**Example:**
```
Describe the expressionist-art container
```

### `containers_search`

Execute semantic/hybrid search across containers.

**Example:**
```
Search for "expressionist use of color" in hybrid mode with k=10 results
```

### `containers_add`

Add new sources to a container.

**Example:**
```
Add https://example.com/essay.pdf to the expressionist-art container
```

### `jobs_status`

Check status of ingestion jobs.

**Example:**
```
Check status of job abc-123-def
```

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLC_BASE_URL` | `http://localhost:7801` | LLC backend API URL |
| `LLC_MCP_TOKEN` | (required) | Bearer token for authentication |

## Architecture

```
┌─────────────────┐
│  Claude Desktop │ (or Cursor, custom agent)
└────────┬────────┘
         │ MCP Protocol (stdio)
         ▼
┌─────────────────┐
│  MCP Gateway    │ (this package)
│  - Tool defs    │
│  - Validation   │
│  - Mapping      │
└────────┬────────┘
         │ HTTP/JSON + Bearer token
         ▼
┌─────────────────┐
│  LLC Backend    │ (FastAPI on :7801)
│  - Search       │
│  - Ingest       │
│  - Retrieval    │
└─────────────────┘
```

The gateway acts as a thin translation layer:
1. Exposes LLC API as MCP tool descriptors
2. Validates tool calls against schemas
3. Proxies requests to LLC backend with authentication
4. Translates responses back to MCP format

## Troubleshooting

### "Connection refused" errors

Ensure LLC backend is running:
```bash
cd ..
make up
```

### "Authentication failed" errors

Verify the token in your environment matches the server configuration, then
update the Claude Desktop/Cursor config and restart.

### "Tool not found" errors

Restart Claude Desktop to reload the MCP server configuration.

### Debug mode

Run the server directly to see logs:
```bash
python -m llc_mcp_gateway.server
```

## Development

### Run tests
```bash
pytest
```

### Format code
```bash
black src/
ruff check src/
```

## Next Steps

- **Python SDK**: Use `../agents-sdk` for programmatic agent development
- **Examples**: See `../examples/agents/` for sample agent implementations
- **Documentation**: Read `../docs/AGENT_QUICKSTART.md` for patterns and best practices






















