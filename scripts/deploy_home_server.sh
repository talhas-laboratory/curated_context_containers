#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO_ROOT/docker/compose.home.yaml}"
DEFAULT_OVERRIDE="$REPO_ROOT/docker/compose.home.override.yaml"
COMPOSE_OVERRIDE_FILE="${COMPOSE_OVERRIDE_FILE:-}"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/docker/.env.home}"

if [ -z "$COMPOSE_OVERRIDE_FILE" ] && [ -f "$DEFAULT_OVERRIDE" ]; then
  COMPOSE_OVERRIDE_FILE="$DEFAULT_OVERRIDE"
fi

COMPOSE_ARGS=(-f "$COMPOSE_FILE")
if [ -n "$COMPOSE_OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$COMPOSE_OVERRIDE_FILE")
fi

if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ "${ALLOW_DIRTY:-0}" != "1" ]; then
    if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
      echo "Refusing to deploy from a dirty git worktree."
      echo "Commit/stash changes first, or override with: ALLOW_DIRTY=1 $0"
      git -C "$REPO_ROOT" status --porcelain
      exit 1
    fi
  fi
  echo "Deploying git SHA: $(git -C "$REPO_ROOT" rev-parse --short=12 HEAD)"

  if [ "${PIN_IMAGES_TO_GIT_SHA:-0}" = "1" ]; then
    origin_url="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
    owner_repo="${GITHUB_REPOSITORY:-}"
    if [ -z "$owner_repo" ]; then
      # Supports both:
      # - https://github.com/OWNER/REPO.git
      # - git@github.com:OWNER/REPO.git
      if [[ "$origin_url" =~ github\.com[/:]+([^/]+)/([^/.]+)(\.git)?$ ]]; then
        owner_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
      fi
    fi

    if [ -z "$owner_repo" ]; then
      echo "PIN_IMAGES_TO_GIT_SHA=1 requested, but couldn't determine GitHub repo slug."
      echo "Set GITHUB_REPOSITORY=OWNER/REPO and retry."
      exit 1
    fi

    sha_tag="sha-$(git -C "$REPO_ROOT" rev-parse --short=7 HEAD)"
    export LLC_FRONTEND_IMAGE="ghcr.io/${owner_repo}-frontend:${sha_tag}"
    export LLC_MCP_IMAGE="ghcr.io/${owner_repo}-mcp:${sha_tag}"
    export LLC_WORKERS_IMAGE="ghcr.io/${owner_repo}-workers:${sha_tag}"
    echo "Pinned images to ${sha_tag}"
    echo "  LLC_FRONTEND_IMAGE=${LLC_FRONTEND_IMAGE}"
    echo "  LLC_MCP_IMAGE=${LLC_MCP_IMAGE}"
    echo "  LLC_WORKERS_IMAGE=${LLC_WORKERS_IMAGE}"
  fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
echo "Missing env file: $ENV_FILE"
echo "Create it from docker/.env.home.example and set LLC_MCP_TOKEN + image tags."
exit 1
fi

echo "Compose files:"
echo "  - $COMPOSE_FILE"
if [ -n "$COMPOSE_OVERRIDE_FILE" ]; then
  echo "  - $COMPOSE_OVERRIDE_FILE"
fi

echo "Preparing /srv/llc volumes..."
if [ "$(id -u)" -eq 0 ]; then
  mkdir -p /srv/llc/{postgres,qdrant,minio,neo4j/data,neo4j/logs,caddy,manifests}
  chown -R "$USER":"$USER" /srv/llc || true
elif [ -w /srv ] || [ -w /srv/llc ]; then
  mkdir -p /srv/llc/{postgres,qdrant,minio,neo4j/data,neo4j/logs,caddy,manifests}
  chown -R "$USER":"$USER" /srv/llc || true
elif sudo -n true 2>/dev/null; then
  sudo mkdir -p /srv/llc/{postgres,qdrant,minio,neo4j/data,neo4j/logs,caddy,manifests}
  sudo chown -R "$USER":"$USER" /srv/llc
else
  echo "Warning: no permission to create /srv/llc and sudo requires a password."
  echo "Ensure /srv/llc exists and is writable, then re-run."
fi

echo "Syncing manifests..."
if command -v rsync >/dev/null 2>&1; then
  rsync -a "$REPO_ROOT/manifests/" /srv/llc/manifests/
else
  cp -a "$REPO_ROOT/manifests/." /srv/llc/manifests/
fi

echo "Starting compose stack..."
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" pull
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" up -d

echo "Done. Verify with: curl http://llc.<tailnet>/api/health"
