# Claude Desktop MCP Setup - Ready to Use! 🚀

Your MCP gateway is **installed and ready**. Follow these steps to connect Claude Desktop to your expressionist-art container.

## Step 1: Ensure LLC Backend is Running

```bash
cd /Users/talhauddin/software/curated_context_containers
make up
```

Verify services are running:
```bash
docker compose -f docker/compose.local.yaml ps
```

You should see:
- `mcp` (FastAPI server on :7801)
- `postgres`
- `qdrant`
- `minio`

All should be in "running" state.

## Step 2: Add MCP Configuration to Claude Desktop

### Option A: Copy the Ready-Made Config

1. Open Terminal and run:
```bash
# Backup existing config (if any)
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json.backup 2>/dev/null || true

# Copy the ready-made config
cp /Users/talhauddin/software/curated_context_containers/mcp-server-gateway/claude_desktop_config_READY.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Option B: Manual Configuration

1. Open this file in a text editor:
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. Add this configuration:
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

**Note:** If you already have other MCP servers configured, merge this into your existing `mcpServers` object.

## Step 3: Restart Claude Desktop

1. **Quit** Claude Desktop completely (Cmd+Q)
2. **Reopen** Claude Desktop
3. The MCP server will start automatically

## Step 4: Verify Connection

In Claude Desktop, you should see MCP tools available. Try asking:

> "What MCP tools are available?"

You should see:
- `containers_list`
- `containers_describe`
- `containers_search`
- `containers_add`
- `jobs_status`

## Step 5: Search the Expressionist Art Container!

Now try these queries:

### List Available Containers
> "List all available containers"

You should see `expressionist-art` and any other containers you have.

### Search for Context
> "Search the expressionist-art container for information about the use of color in expressionist paintings"

> "Using the expressionist-art container, find examples of how expressionists used color to convey emotion"

> "What does the expressionist-art container say about color theory?"

### Describe the Container
> "Describe the expressionist-art container"

This will show you:
- Theme
- Number of documents
- Embedder being used
- Statistics

### Add New Sources (if needed)
> "Add this URL to the expressionist-art container: https://example.com/essay.pdf"

## Troubleshooting

### "Connection refused" or "Cannot connect"

**Issue:** LLC backend not running

**Fix:**
```bash
cd /Users/talhauddin/software/curated_context_containers
make up
# Wait 30 seconds for services to start
```

### "MCP server not found" or tools don't appear

**Issue:** Claude Desktop config path wrong or Python not in PATH

**Fix 1 - Verify Python:**
```bash
which python3
# Use full path in config if needed
```

**Fix 2 - Use full path in config:**
```json
{
  "mcpServers": {
    "local-latent-containers": {
      "command": "/usr/bin/python3",  // or output of 'which python3'
      "args": ["-m", "llc_mcp_gateway.server"],
      "env": { ... }
    }
  }
}
```

### "Container not found"

**Issue:** expressionist-art container doesn't exist yet

**Fix:** Create the container first:
```bash
cd /Users/talhauddin/software/curated_context_containers
# Check existing containers
curl -X POST http://localhost:7801/v1/containers/list \
  -H "Authorization: Bearer $LLC_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": "active"}'
```

### "Authentication failed"

**Issue:** Token mismatch

**Fix:** Verify token:
```bash
echo "$LLC_MCP_TOKEN"
```

### Check MCP Server Logs

If Claude Desktop shows errors, check the logs:

**macOS:**
```bash
# View Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

Or test the MCP server directly:
```bash
cd /Users/talhauddin/software/curated_context_containers/mcp-server-gateway
LLC_BASE_URL="http://localhost:7801" \
LLC_MCP_TOKEN="your-token-here" \
python -m llc_mcp_gateway.server
# Should start without errors
# Press Ctrl+C to stop
```

## Example Conversation

Once working, you can have conversations like:

**You:** "Search the expressionist-art container for information about color theory"

**Claude (using MCP):**
*[Uses containers_search tool]*

"Based on the expressionist-art container, I found several relevant passages about color theory:

1. **Kandinsky — Concerning the Spiritual in Art** (Score: 0.87)
   'The expressionists revolutionized the use of color, treating it as an independent element capable of conveying emotion...'

2. **Color and Expression in German Expressionism** (Score: 0.82)
   'Unlike the impressionists who focused on capturing light, expressionists used color symbolically...'

[Claude can now discuss these findings with you]"

---

**You:** "Can you find more sources about expressionist color techniques?"

**Claude:** 
*[Uses containers_search with different query]*

"Here are additional sources focusing specifically on techniques..."

## Advanced Usage

### Search Multiple Containers
> "Search both expressionist-art and bauhaus-design containers for information about color"

### Check Job Status
> "What's the status of job abc-123-def-456?"

### Get Container Statistics
> "Show me detailed statistics for the expressionist-art container"

## What's Next?

Once this works, you can:

1. **Add More Sources:** Ask Claude to add URLs to containers
2. **Create New Containers:** Use the lifecycle API (see Python SDK examples)
3. **Build Custom Agents:** Use the Python SDK (`agents-sdk/`) for programmatic access
4. **Multi-Agent Workflows:** See `examples/agents/` for inspiration

## Quick Reference

**Config Location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**MCP Gateway Location:**
```
/Users/talhauddin/software/curated_context_containers/mcp-server-gateway/
```

**Token:**
```
your-token-here
```

**API Endpoint:**
```
http://localhost:7801
```

---

🎉 **You're all set!** Restart Claude Desktop and start searching your containers!



