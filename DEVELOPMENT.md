# Development Guide

## First-Time Setup Decision

**Choose your development environment:**

### 🏠 Local Development (Laptop)

Best for: Testing, feature development, debugging

1. **Setup**:
   ```bash
   cd docker
   cp .env.dev.template .env
   # Edit .env with your API  keys
   docker compose -f compose.dev.yaml up -d
   ```

2. **Cherry Studio setup**:
   - MCP will auto-connect to `localhost:7801`
   - Default config already set in `~/.llc_mcp_config`

3. **Access**:
   - Backend API: `http://localhost:7801`
   - Qdrant UI: `http://localhost:6333/dashboard`
   - MinIO Console: `http://localhost:9001`

---

### 🌐 Remote Server Connection

Best for: Using production data, collaboration

1. **Your config** (`~/.llc_mcp_config`) is already set for remote server

2. **Cherry Studio automatically connects** to:
   ```
   http://talhas-laboratory.tailefe062.ts.net/api/v1
   ```

3. **To switch to local**, edit `~/.llc_mcp_config`:
   ```bash
   # Comment out remote lines
   # export LLC_MCP_BRIDGE_URL="http://talhas-laboratory..."
   
   # Uncomment local lines
   export LLC_MCP_BRIDGE_URL="http://localhost:7801/v1"
   export LLC_MCP_BRIDGE_TOKEN="local-dev-token"
   ```

4. **Restart Cherry Studio** to apply changes

---

## Quick Commands

### Start Local Backend
```bash
docker compose -f docker/compose.dev.yaml up -d
```

### Stop Local Backend
```bash
docker compose -f docker/compose.dev.yaml down
```

### View Logs
```bash
docker compose -f docker/compose.dev.yaml logs -f mcp
```

### Restart a Service
```bash
docker compose -f docker/compose.dev.yaml restart mcp
```

### Cherry Studio Debug Log
```bash
tail -f /tmp/cherry_mcp_debug.log
```

---

## Project Structure

```
curated_context_containers/
├── docker/
│   ├── compose.dev.yaml      ← Local development
│   ├── compose.prod.yaml     ← Server deployment
│   ├── .env.dev.template     ← Copy to .env locally
│   └── .env.prod.template    ← Copy to .env on server
├── frontend/                  ← Next.js UI
├── mcp-server/               ← Backend API
│   ├── mcp_bridge.py         ← Cherry Studio bridge (auto-detects env)
│   └── start_bridge.sh       ← Wrapper script
└── workers/                   ← Background jobs
```

---

## Troubleshooting

### Cherry Studio shows "Connection Closed"
1. Check wrapper script is executable:
   ```bash
   chmod +x mcp-server/start_bridge.sh
   ```

2. Check debug log:
   ```bash
   tail /tmp/cherry_mcp_debug.log
   ```

### "Connection Refused"
- **Local**: Start Docker backend
- **Remote**: Check server is accessible:
  ```bash
  curl http://talhas-laboratory.tailefe062.ts.net/health
  ```

### Data Mismatch
Check which environment you're connected to:
```bash
cat ~/.llc_mcp_config
```

---

## Environment Switching

Your MCP bridge automatically reads from `~/.llc_mcp_config`.

**Current setup**: Remote server  
**To switch**: Edit the config file and uncomment the local lines

No need to edit Python code directly!
