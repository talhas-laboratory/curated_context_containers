# Docker Configuration Guide

This directory contains Docker Compose configurations for running Latent Containers.

## Quick Reference

| File | Purpose | Use When |
|------|---------|----------|
| `compose.dev.yaml` | Local development | Developing on your laptop |
| `compose.prod.yaml` | Production server | Deploying to remote server |
| `compose.observability.yaml` | Observability stack | Prometheus/Grafana/Loki |
| `.env.dev.template` | Dev environment vars | Setting up local env |
| `.env.prod.template` | Prod environment vars | Setting up server env |

---

## Local Development

### First-Time Setup

1. **Copy the template**:
   ```bash
   cp .env.dev.template .env
   ```

2. **Edit `.env`** and add your API keys:
   ```env
   LLC_NOMIC_API_KEY=your-actual-key
   LLC_OPENROUTER_API_KEY=your-actual-key
   ```

3. **Start services**:
   ```bash
   docker compose -f compose.dev.yaml up -d
   ```

4. **Verify**:
   ```bash
   curl http://localhost:7801/health
   ```

### Stopping Services

```bash
docker compose -f compose.dev.yaml down
```

---

## Production Server

### Server Setup

1. **SSH to server**:
   ```bash
   ssh talha@talhas-laboratory.tailefe062.ts.net
   ```

2. **Copy template**:
   ```bash
   cd ~/curated_context_containers/docker
   cp .env.prod.template .env
   ```

3. **Edit `.env`** with production values

4. **Start services**:
   ```bash
   docker compose -f compose.prod.yaml up -d
   ```

### Updating Server

```bash
docker compose -f compose.prod.yaml pull
docker compose -f compose.prod.yaml up -d
```

### Observability (Optional)

```bash
docker compose -f compose.prod.yaml -f compose.observability.yaml up -d
```

---

## Environment Variables

### Required for Both

- `LLC_MCP_TOKEN` - Authentication token for API
- `LLC_NOMIC_API_KEY` or `LLC_GOOGLE_API_KEY` - For embeddings

### Optional

- `LLC_OPENROUTER_API_KEY` - For graph LLM features
- `LLC_EMBEDDER_PROVIDER` - Choose `nomic` or `google` (default: nomic)

---

## Troubleshooting

### "No such file or directory: /srv/llc"

You're trying to use `compose.prod.yaml` locally. Use `compose.dev.yaml` instead.

### "Connection refused" from MCP bridge

Backend isn't running. Start it:
```bash
docker compose -f compose.dev.yaml up -d
```

### Check service status

```bash
docker compose -f compose.dev.yaml ps
```

### View logs

```bash
docker compose -f compose.dev.yaml logs mcp
```
