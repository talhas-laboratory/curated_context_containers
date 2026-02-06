# Deployment Guide for Curated Context Containers

This guide details the deployment process for the `curated_context_containers` project on the home server (`192.168.0.102`).

## Architecture Overview

The system runs as a Docker Compose stack with the following services:

- **Frontend**: Next.js application (Port 3000, exposed via Caddy on Port 80)
- **MCP Server**: Python backend (Port 7801)
- **Workers**: Background job processors
- **Databases/Storage**:
  - **PostgreSQL**: Relational data (Port 5432)
  - **Qdrant**: Vector database (Port 6333)
  - **Neo4j**: Graph database (Port 7474/7687)
  - **MinIO**: S3-compatible object storage (Port 9000/9001)
- **Reverse Proxy**: Caddy (Port 80)

## Prerequisites

### Access
- **SSH Access**: `ssh talha@192.168.0.102`
- **Auth**: Use SSH keys (recommended) or whatever access method your host requires.
- **Permissions**: User `talha` must have `docker` group privileges or use `sudo`.

### Secrets & Configuration
Configuration is managed via `.env` files.
- **Template**: `docker/.env.prod.template` (Recommended source)
- **Live Config**: `docker/.env` (on the server)

Ensure the following secrets are set in the live `.env`:
- **LLC_MCP_TOKEN** (Must match your client configuration)
- Database passwords (`POSTGRES_PASSWORD`, `MINIO_SECRET_KEY`, `NEO4J_PASSWORD`)
- External API keys (`LLC_OPENROUTER_API_KEY`, `LLC_GOOGLE_API_KEY`, etc.)
- Pinned image tags (`LLC_FRONTEND_IMAGE`, `LLC_MCP_IMAGE`, `LLC_WORKERS_IMAGE`, `MINIO_IMAGE`)

## Deployment Workflow

The project uses a **Hybrid Deployment** model:
1. **CI (GitHub Actions)**: Builds and pushes Docker images to GitHub Container Registry (`ghcr.io`) whenever `main` is updated.
2. **CD (Manual/Scripted)**: Pulls the new images on the server and restarts the stack.

### 1. Build & Publish (Automated)
Every push to `main` triggers the GitHub Actions workflows to build:
- `ghcr.io/talhas-laboratory/curated_context_containers-frontend:<tag>`
- `ghcr.io/talhas-laboratory/curated_context_containers-mcp:<tag>`
- `ghcr.io/talhas-laboratory/curated_context_containers-workers:<tag>`

**Wait for these actions to complete on GitHub before deploying.**

### 2. server Deployment

You can deploy using the helper script (Recommended) or manually.

#### Option A: Scripted Deployment (Fastest)

There is a `deploy_home_server.sh` script that handles directory setup, manifest syncing, and compose restart.

1. **SSH into the server**:
   ```bash
   ssh talha@192.168.0.102
   ```

2. **Navigate to project**:
   ```bash
   cd ~/software/curated_context_containers
   ```

3. **Update Code**:
   ```bash
   git pull origin main
   ```

4. **Run Deployment Script**:
   *Note: We override variables to point to the production config files.*
   ```bash
   # Pins the Docker images to the current git SHA tag (sha-<shortsha>) published by CI.
   # This prevents "mystery rollbacks" when tags drift.
   PIN_IMAGES_TO_GIT_SHA=1 \
   COMPOSE_FILE=docker/compose.prod.yaml \
   ENV_FILE=docker/.env \
   ./scripts/deploy_home_server.sh
   ```

#### Option B: Manual Deployment

If the script fails or you need granular control:

1. **SSH and Navigate** (as above).

2. **Update Code**: `git pull origin main`

3. **Ensure Data Directories Exist**:
   ```bash
   sudo mkdir -p /srv/llc/{postgres,qdrant,minio,neo4j/data,neo4j/logs,caddy,manifests}
   sudo chown -R talha:docker /srv/llc
   ```

4. **Sync Manifests**:
   ```bash
   rsync -a manifests/ /srv/llc/manifests/
   ```

5. **Pull Latest Images**:
   ```bash
   docker compose -f docker/compose.prod.yaml pull
   ```

6. **Restart Stack**:
   ```bash
   docker compose -f docker/compose.prod.yaml up -d
   ```
   The `migrations` service will apply Alembic migrations automatically before MCP and workers start.

7. **Cleanup**:
   ```bash
   docker image prune -f
   ```

8. **Deploy Smoke Check**:
   ```bash
   BASE_URL=http://talhas-laboratory.tailefe062.ts.net \
   LLC_MCP_TOKEN=... \
   ./scripts/deploy_smoke.sh
   ```

## Configuration Management

### First-Time Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/talhas-laboratory/curated_context_containers.git ~/software/curated_context_containers
   cd ~/software/curated_context_containers
   ```

2. **Create Environment File**:
   ```bash
   cd docker
   cp .env.prod.template .env
   nano .env
   # Fill in values, especially LLC_MCP_TOKEN
   ```

3. **Create Volumes**: See step 3 in manual deployment.

## Updating Image Versions

1. Update `docker/.env` with new pinned tags or digests for `LLC_*_IMAGE` and `MINIO_IMAGE`.
2. Deploy with `docker compose -f docker/compose.prod.yaml up -d`.
3. Run `./scripts/deploy_smoke.sh` against the base URL.
4. Monitor logs and Grafana (if enabled) for errors.

Example digest pinning:
```
LLC_MCP_IMAGE=ghcr.io/OWNER/REPO-mcp@sha256:REPLACE_WITH_DIGEST
```

## Troubleshooting

- **Server Connection Issues**:
  - `curl http://192.168.0.102:7801/health` -> Should return 200 OK.
  - `docker compose -f docker/compose.prod.yaml ps` -> Check if containers are restarting.
  
- **"No such file or directory: /srv/llc/..."**:
  - Run the `sudo mkdir` commands to ensure volumes exist on the host.

- **Missing Environment Variables**:
  - Double check `docker/.env`. Ensure you are loading the correct file (default compose looks for `.env` in the same dir).

## Backups

See `docs/backup_restore.md` for backup and restore scripts and usage.
The example cron entry is in `docs/backup_schedule.cron`.

## Observability

Optional stack: `docs/observability.md` (Prometheus + Grafana + Loki).

## Migrations & Rollback

The `migrations` service applies Alembic migrations automatically on deploy.

To roll back the last migration (use with caution):
```bash
docker compose -f docker/compose.prod.yaml run --rm migrations alembic downgrade -1
```

## Rollback

To roll back to a stable state:

1. **Revert Git Code**: `git checkout <previous-hash>`
2. **Revert Images**: Unless you tagged specific versions in `.env`, `latest` will be the broken on. You might need to rely on the local docker cache (if you haven't pruned) or modify `.env` to point to a specific older SHA tag from GHCR.
3. **Restart**: `docker compose -f docker/compose.prod.yaml up -d`
