#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-"http://localhost"}
TOKEN=${MCP_TOKEN:-${LLC_MCP_TOKEN:-}}

AUTH_HEADER=()
if [ -n "$TOKEN" ]; then
  AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
fi

curl -sf "$BASE_URL/" > /dev/null
curl -sf "$BASE_URL/api/health" > /dev/null
curl -sf "$BASE_URL/api/ready" > /dev/null

if [ -n "$TOKEN" ]; then
  curl -sf -X POST "$BASE_URL/api/v1/containers/list" \
    -H 'Content-Type: application/json' \
    "${AUTH_HEADER[@]}" \
    -d '{}' > /dev/null
else
  echo "Skipping authenticated MCP check (no token)."
fi

echo "Deploy smoke check passed for $BASE_URL"
