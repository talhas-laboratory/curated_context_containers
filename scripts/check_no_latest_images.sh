#!/usr/bin/env bash
set -euo pipefail

FILES=(
  "docker/compose.home.yaml"
  "docker/.env.home.example"
  "docker/compose.prod.yaml"
  "docker/.env.prod.template"
  "docker/compose.observability.yaml"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    if grep -n ":latest" "$file" >/dev/null; then
      echo "Found :latest tag in $file. Pin image tags before deploy."
      grep -n ":latest" "$file" || true
      exit 1
    fi
  fi
done

echo "Image tag check passed (no :latest)."
