#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE=${COMPOSE_FILE:-"$ROOT_DIR/docker/compose.prod.yaml"}
BACKUP_DIR=${1:-${BACKUP_DIR:-""}}
STOP_SERVICES=${STOP_SERVICES:-1}
RESET_DB=${RESET_DB:-1}

if [ -z "$BACKUP_DIR" ]; then
  echo "Usage: $0 /path/to/backup_dir"
  echo "Or set BACKUP_DIR env var."
  exit 1
fi

if [ "${RESTORE_FORCE:-}" != "1" ]; then
  echo "Refusing to restore without RESTORE_FORCE=1"
  exit 1
fi

if [ ! -f "$BACKUP_DIR/postgres.sql" ]; then
  echo "Missing $BACKUP_DIR/postgres.sql"
  exit 1
fi
if [ ! -f "$BACKUP_DIR/qdrant.tgz" ] || [ ! -f "$BACKUP_DIR/minio.tgz" ] || [ ! -f "$BACKUP_DIR/neo4j.tgz" ]; then
  echo "Missing one or more volume archives in $BACKUP_DIR"
  exit 1
fi

if [ "$STOP_SERVICES" = "1" ]; then
  echo "Stopping stack for restore..."
  docker compose -f "$COMPOSE_FILE" stop || true
fi

echo "Restoring Postgres..."
if [ "$RESET_DB" = "1" ]; then
  docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U local -d registry -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
fi

docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U local -d registry < "$BACKUP_DIR/postgres.sql"

echo "Restoring Qdrant volume..."
rm -rf /srv/llc/qdrant
mkdir -p /srv/llc
tar -C /srv/llc -xzf "$BACKUP_DIR/qdrant.tgz"

echo "Restoring MinIO volume..."
rm -rf /srv/llc/minio
mkdir -p /srv/llc
tar -C /srv/llc -xzf "$BACKUP_DIR/minio.tgz"

echo "Restoring Neo4j volume..."
rm -rf /srv/llc/neo4j
mkdir -p /srv/llc
tar -C /srv/llc -xzf "$BACKUP_DIR/neo4j.tgz"

if [ "$STOP_SERVICES" = "1" ]; then
  echo "Starting stack after restore..."
  docker compose -f "$COMPOSE_FILE" up -d
fi

echo "Restore complete from: $BACKUP_DIR"
