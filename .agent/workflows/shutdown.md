---
description: Shut down all local project processes
---

# Shutdown Workflow

This workflow stops all local development processes for the Latent Containers project.

## When to Use

Run this workflow when the user requests:
- "close all current processes for this project"
- "shut down the local stack"
- "stop all Docker services"
- "clean up running processes"

## Steps

// turbo
1. Stop local Docker services:
```bash
cd /Users/talhauddin/software/curated_context_containers
docker compose -f docker/compose.dev.yaml down
```

2. Verify all containers are stopped:
```bash
docker ps --filter "name=docker-" --format "table {{.Names}}\t{{.Status}}"
```

3. (Optional) If user wants to free up disk space, remove volumes:
```bash
docker compose -f docker/compose.dev.yaml down -v
```
**Warning**: This deletes all local data! Only do this if user explicitly requests it.

## Notes

- This workflow only affects **local development** services
- The **remote production server** (`talhas-laboratory.tailefe062.ts.net`) is NOT affected
- Cherry Studio MCP connection will continue working (it connects to remote server)
- To restart local services: `docker compose -f docker/compose.dev.yaml up -d`
