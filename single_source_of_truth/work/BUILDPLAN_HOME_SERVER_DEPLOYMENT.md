# Build Plan — Home Server Deployment (Docker + 24/7 MCP)

## Goal
Package the full Local Latent Containers stack so it can run 24/7 on an Ubuntu 24.04.3 home server, expose the frontend via browser, and allow remote agents to connect via MCP with a stable, authenticated endpoint.

## Requirements (mapped to the vision)
1. **Always-on services**: MCP API, workers, frontend, and data stores must survive reboots and keep running.
2. **Browser access**: A stable VPN URL serves the frontend UI via reverse proxy.
3. **MCP access for agents**: Agents can connect to the MCP gateway or API 24/7 with a consistent base URL and token.
4. **Single deployment package**: One command (or one compose file) can bring the stack up with persistent storage.
5. **Security**: Token-based auth, restricted internal ports, and VPN-only access (Tailscale).
6. **Portability**: Works on Ubuntu x86_64; supports Mac M2 dev workflows via multi-arch builds.
7. **Operational hygiene**: Backup/restore path and upgrade cadence documented.

## Deployment Decisions (locked)
- **Access model**: VPN-only (Tailscale); no public domain exposure.
- **Build strategy**: buildx multi-arch images pushed to GHCR; home server pulls images.
- **MCP gateway**: run locally per agent; gateway connects to remote MCP API over Tailscale.

## Current State Evaluation (against requirements)
### What already exists
- **Dockerfiles** for backend services: `mcp-server/Dockerfile`, `workers/Dockerfile`.
- **Local compose** stack: `docker/compose.local.yaml` with Postgres, Qdrant, MinIO, Neo4j, MCP server, workers.
- **MCP gateway** implementation: `mcp-server-gateway` (stdio-based MCP server).
- **Runbooks** for setup and backups: `single_source_of_truth/runbooks/SETUP_AND_INSTALL.md`, `BACKUP_AND_RESTORE.md`.

### Gaps to close
- **Frontend is not containerized** (no Dockerfile, no production compose service).
- **No production compose** file; local compose exposes internal services and uses dev defaults.
- **No VPN-first access plan** (Tailscale setup, firewall rules, stable tailnet hostnames).
- **No multi-arch build plan** (Mac M2 builds are arm64; Ubuntu home server is amd64).
- **No documented remote MCP access** path for agent-local gateway configuration.
- **Secrets handling** is dev-oriented (plain text token in repo) and needs hardening for long-lived deployment.
- **CORS is dev-biased** (wide allowlist/regex) and should be locked to the frontend origin in prod.

## Build Plan (bridge the gaps)

### Phase 1 - Containerize the Frontend
- [x] Add `frontend/Dockerfile` (multi-stage build; `next build` + `next start`).
- [x] Set `NEXT_PUBLIC_MCP_BASE_URL` at build time to the proxy path (`/api`).
- [x] Keep `NEXT_PUBLIC_MCP_TOKEN` empty by default; rely on localStorage token or a proxy to avoid hardcoding secrets.
- [x] Add buildx GHCR workflow for the frontend image (linux/amd64, linux/arm64).
- [x] Update `frontend/README.md` with production build/run instructions.

### Phase 2 - Production Compose Stack
- [x] Create `docker/compose.home.yaml` (or `compose.prod.yaml`) with services:
  - `postgres`, `qdrant`, `minio`, `neo4j`
  - `mcp` (FastAPI)
  - `workers`
  - `frontend`
  - `reverse-proxy` (required) for single-host routing inside tailnet
- [x] Use `image:` references (GHCR) instead of `build:` for app services.
- [x] Restrict ports: expose frontend/MCP to host for Tailscale only; keep DB/Qdrant/MinIO/Neo4j internal.
- [x] Add `restart: unless-stopped` for all services.
- [x] Add healthchecks and `depends_on` conditions for service readiness.
- [x] Move volumes to explicit host paths under `/srv/llc` for easy backup.
- [x] Add `.env` on server for secrets (`LLC_MCP_TOKEN`, API keys); remove reliance on repo `docker/mcp_token.txt`.
- [x] Provide `docker/.env.home.example` template for server configuration.
- [x] Add GHCR buildx workflows for `mcp` and `workers` images (linux/amd64, linux/arm64).

### Phase 3 - Tailscale Access + Reverse Proxy
- [ ] Install Tailscale on the Ubuntu server; enable MagicDNS or note the tailnet IP.
- [ ] Add firewall rules to allow ports only on `tailscale0` (ufw recommended).
- [x] Add `docker/Caddyfile` or `docker/nginx.conf` to route:
  - `/` -> `frontend:3000`
  - `/api` (or `/mcp`) -> `mcp:7801`
- [x] Use a single URL: `http://llc.<tailnet>` for the frontend and `http://llc.<tailnet>/api` for MCP.
- [x] Set `MCP_CORS_ORIGINS` to the frontend origin; remove permissive wildcard in production.
- [x] Document Tailscale + firewall steps in `docs/DEPLOY_HOME_SERVER.md`.

### Phase 4 - MCP Access Strategy (24/7)
- [x] Document agent-local gateway setup using tailnet base URL:
  - `LLC_BASE_URL=http://<tailnet-hostname>:7801` (or `/api` if proxy)
  - `LLC_MCP_TOKEN=<token>`
- [x] Update `mcp-server-gateway/README.md` with tailnet examples and VPN-only assumption.

### Phase 5 - Secrets + Security
- [x] Move `LLC_MCP_TOKEN` out of repo and into `.env` or Docker secrets on server.
- [x] Document GHCR auth: PAT with `packages:read` and `docker login ghcr.io` on server.
- [x] Add a short security section to `docker/README.md` covering VPN-only access and firewall defaults.

### Phase 6 - Ops + Persistence
- [x] Add a `scripts/deploy_home_server.sh` (or docs) to bootstrap:
  - create directories
  - `docker login ghcr.io` (once)
  - pull images
  - `docker compose -f docker/compose.home.yaml up -d`
- [x] Document upgrade workflow (pull new images, restart, smoke test).
- [x] Link existing backup/restore runbook in the deployment doc.

## Acceptance Checks (Definition of Done)
- [ ] `http://llc.<tailnet>` loads the frontend.
- [ ] Frontend can list/search containers via MCP API endpoint.
- [ ] `curl http://llc.<tailnet>/api/health` returns `{status: "ok"}`.
- [ ] Agents can connect via MCP gateway using `LLC_BASE_URL` and token.
- [ ] Containers and data persist after host reboot (volumes survive).
- [ ] Internal services are not exposed outside the tailnet.

## Artifacts to Produce
- `frontend/Dockerfile`
- `docker/compose.home.yaml` (or `compose.prod.yaml`)
- `docker/Caddyfile` (or `docker/nginx.conf`)
- `scripts/deploy_home_server.sh` (optional helper)
- `docs/DEPLOY_HOME_SERVER.md` (deployment instructions)

## Open Questions
- None (deployment decisions locked).
