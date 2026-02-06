#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE=${COMPOSE_FILE:-"$ROOT_DIR/docker/compose.prod.yaml"}
BACKUP_ROOT=${BACKUP_ROOT:-"/srv/llc/backups"}
STOP_SERVICES=${STOP_SERVICES:-0}
RETENTION_DAYS=${RETENTION_DAYS:-14}
RETENTION_COUNT=${RETENTION_COUNT:-}
VERIFY=${VERIFY:-1}
METRICS_DIR=${METRICS_DIR:-"/srv/llc/metrics"}

TS=$(date +"%Y%m%d_%H%M%S")
OUT_DIR="$BACKUP_ROOT/$TS"
mkdir -p "$OUT_DIR"

if [ "$STOP_SERVICES" = "1" ]; then
  echo "Stopping data services for consistent backup..."
  docker compose -f "$COMPOSE_FILE" stop qdrant minio neo4j || true
fi

echo "Backing up Postgres..."
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U local -d registry > "$OUT_DIR/postgres.sql"

echo "Backing up Qdrant volume..."
tar -C /srv/llc -czf "$OUT_DIR/qdrant.tgz" qdrant

echo "Backing up MinIO volume..."
tar -C /srv/llc -czf "$OUT_DIR/minio.tgz" minio

echo "Backing up Neo4j volume..."
tar -C /srv/llc -czf "$OUT_DIR/neo4j.tgz" neo4j

if [ "$STOP_SERVICES" = "1" ]; then
  echo "Restarting data services..."
  docker compose -f "$COMPOSE_FILE" up -d qdrant minio neo4j
fi

if [ "$VERIFY" = "1" ]; then
  echo "Verifying backup artifacts..."
  test -s "$OUT_DIR/postgres.sql"
  tar -tzf "$OUT_DIR/qdrant.tgz" >/dev/null
  tar -tzf "$OUT_DIR/minio.tgz" >/dev/null
  tar -tzf "$OUT_DIR/neo4j.tgz" >/dev/null
fi

mkdir -p "$METRICS_DIR"
cat <<METRICS > "$METRICS_DIR/llc_backup.prom"
# HELP llc_backup_last_success_timestamp Unix timestamp of last successful backup
# TYPE llc_backup_last_success_timestamp gauge
llc_backup_last_success_timestamp $(date +%s)
METRICS

if [ -n "$RETENTION_DAYS" ]; then
  echo "Pruning backups older than $RETENTION_DAYS days..."
  find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -print0 | xargs -0 rm -rf -- || true
fi

if [ -n "$RETENTION_COUNT" ]; then
  echo "Keeping newest $RETENTION_COUNT backups..."
  ls -1dt "$BACKUP_ROOT"/* 2>/dev/null | tail -n +"$((RETENTION_COUNT + 1))" | xargs rm -rf -- || true
fi

echo "Backup complete: $OUT_DIR"
