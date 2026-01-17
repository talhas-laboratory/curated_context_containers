#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/compose.local.yaml"
export LLC_POSTGRES_DSN=${LLC_POSTGRES_DSN:-"postgresql://local:localpw@localhost:5433/registry"}
POSTGRES_DSN="$LLC_POSTGRES_DSN"
MCP_TOKEN="${MCP_TOKEN:-${LLC_MCP_TOKEN:-}}"

if [[ -z "${MCP_TOKEN:-}" && -n "${MCP_TOKEN_PATH:-}" && -f "$MCP_TOKEN_PATH" ]]; then
  MCP_TOKEN=$(cat "$MCP_TOKEN_PATH")
fi
MCP_TOKEN="${MCP_TOKEN:-}"

AUTH_HEADER=()
if [[ -n "${MCP_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $MCP_TOKEN")
fi

pushd "$ROOT_DIR" > /dev/null

trap 'echo "Stopping compose stack"; docker compose -f "$COMPOSE_FILE" logs mcp workers; docker compose -f "$COMPOSE_FILE" down' EXIT

docker compose -f "$COMPOSE_FILE" up -d --build

echo "Waiting for Postgres to be ready..."
RETRIES=30
until psql "$POSTGRES_DSN" -c "SELECT 1" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
  echo "Waiting for Postgres... $((RETRIES--))"
  sleep 2
done
if [ $RETRIES -eq 0 ]; then
  echo "Timeout waiting for Postgres"
  docker compose -f "$COMPOSE_FILE" logs postgres
  exit 1
fi

./scripts/bootstrap_db.sh

# Give MCP a moment to boot
sleep 5

curl -sf "${AUTH_HEADER[@]}" http://localhost:7801/health
curl -sf -X POST http://localhost:7801/v1/containers/list -H 'Content-Type: application/json' "${AUTH_HEADER[@]}" -d '{}'
curl -sf -X POST http://localhost:7801/v1/search -H 'Content-Type: application/json' "${AUTH_HEADER[@]}" -d '{"query":"smoke", "container_ids":["00000000-0000-0000-0000-000000000001"]}'

curl -sf -X POST http://localhost:7801/v1/containers/add \
  -H 'Content-Type: application/json' \
  "${AUTH_HEADER[@]}" \
  -d '{"container":"expressionist-art","sources":[{"uri":"https://example.com/smoke","mime":"text/plain","meta":{"text":"smoke test text"}}]}'

curl -sf -X POST http://localhost:7801/v1/containers/add \
  -H 'Content-Type: application/json' \
  "${AUTH_HEADER[@]}" \
  -d '{"container":"expressionist-art","sources":[{"uri":"https://example.com/smoke","mime":"text/plain","meta":{"text":"smoke test text"}}]}'

sleep 8

MCP_TOKEN="$MCP_TOKEN" python3 - <<'PY'
import json
import sys
import urllib.request
import os

payload = json.dumps({
    "query": "smoke",
    "container_ids": ["00000000-0000-0000-0000-000000000001"],
    "mode": "hybrid",
    "diagnostics": True,
}).encode()
headers = {"Content-Type": "application/json"}
token = os.environ.get("MCP_TOKEN")
if token:
    headers["Authorization"] = f"Bearer {token}"
req = urllib.request.Request(
    "http://localhost:7801/v1/search",
    data=payload,
    headers=headers,
)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read())

diagnostics = data.get("diagnostics", {})
timings = data.get("timings_ms", {})
assert data.get("returned", 0) >= 1, "hybrid search returned no results"
assert diagnostics.get("mode") == "hybrid", diagnostics
assert "bm25_hits" in diagnostics and "vector_hits" in diagnostics, diagnostics
assert "bm25_ms" in timings and "vector_ms" in timings and "total_ms" in timings, timings
print("Smoke diagnostics", json.dumps({"diagnostics": diagnostics, "timings": timings}))
PY

DOC_COUNT=$(psql "$POSTGRES_DSN" -At -c "SELECT COUNT(*) FROM documents WHERE container_id = '00000000-0000-0000-0000-000000000001';")
if [ "$DOC_COUNT" != "1" ]; then
  echo "Document deduplication failed (expected 1 doc, found $DOC_COUNT)"
  exit 1
fi

CHUNK_COUNT=$(psql "$POSTGRES_DSN" -At -c "SELECT COUNT(*) FROM chunks WHERE container_id = '00000000-0000-0000-0000-000000000001';")
if [ "$CHUNK_COUNT" -eq 0 ]; then
  echo "Chunk ingestion failed (no chunks for expressionist-art)"
  exit 1
fi

# Verify embedding cache
CACHE_COUNT=$(psql "$POSTGRES_DSN" -At -c "SELECT COUNT(*) FROM embedding_cache WHERE created_at > NOW() - INTERVAL '5 minutes';")
if [ "$CACHE_COUNT" -eq 0 ]; then
  echo "Warning: No embedding cache entries found (expected some after ingestion)"
fi

# Verify dedup assignments
DEDUP_COUNT=$(psql "$POSTGRES_DSN" -At -c "SELECT COUNT(*) FROM chunks WHERE container_id = '00000000-0000-0000-0000-000000000001' AND dedup_of IS NOT NULL;")
echo "Found $DEDUP_COUNT semantic-deduped chunks"

echo "Smoke test passed"
