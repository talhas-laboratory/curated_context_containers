#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO_ROOT/docker/compose.home.yaml}"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/docker/.env.home}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Create it from docker/.env.home.example and set LLC_MCP_TOKEN + image tags."
  exit 1
fi

echo "Preparing /srv/llc volumes..."
sudo mkdir -p /srv/llc/{postgres,qdrant,minio,neo4j/data,neo4j/logs,caddy,manifests}
sudo chown -R "$USER":"$USER" /srv/llc

echo "Syncing manifests..."
if command -v rsync >/dev/null 2>&1; then
  rsync -a "$REPO_ROOT/manifests/" /srv/llc/manifests/
else
  cp -a "$REPO_ROOT/manifests/." /srv/llc/manifests/
fi

echo "Starting compose stack..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "Done. Verify with: curl http://llc.<tailnet>/api/health"
