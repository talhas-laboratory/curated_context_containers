# Debugging Log — Fixed Errors

This log tracks significant bugs, their root causes, and how they were resolved.

---

## [2026-02-08] Qdrant Crashing with "Too Many Open Files"

- **Status:** ✅ Fixed
- **Symptom:** `docker-qdrant-1` container would crash or become unresponsive; UI would show `VECTOR_DOWN`; logs contained `RocksDB: Too many open files`.
- **Root Cause:** The `docker/compose.prod.yaml` was missing `ulimits` for the Qdrant service. As collections and segments grew, Qdrant exceeded the default OS limit for file descriptors.
- **Resolution:** Added `ulimits` configuration to the Qdrant service in `compose.prod.yaml` and `compose.local.yaml`.
  ```yaml
  ulimits:
    nofile:
      soft: 1048576
      hard: 1048576
  ```
- **Verification:** `docker exec docker-qdrant-1 ulimit -n` now returns `1048576`.

---

## [2026-02-08] Nomic Embedding API 404 (Outdated Endpoints)

- **Status:** ✅ Fixed
- **Symptom:** Semantic search failed with `VECTOR_DOWN`; internal logs showed `httpx.HTTPStatusError: Client error '404 Not Found' for url 'https://api-atlas.nomic.ai/v1/embedding'`.
- **Root Cause:** Nomic updated their API to require specific endpoints for text and image embeddings. The old generic endpoint `/v1/embedding` now returns 404.
- **Resolution:** Updated `config.py` and `embedder.py` to use:
  - Text: `https://api-atlas.nomic.ai/v1/embedding/text`
  - Image: `https://api-atlas.nomic.ai/v1/embedding/image`
- **Verification:** Direct API call via `embedding_client.embed_text` inside the container now returns successful 768-dimension vectors.

---

## [2026-01-18] MCP Authentication 401 Unauthorized

- **Status:** ✅ Fixed
- **Symptom:** Cherry Studio could not connect to MCP; received 401 errors.
- **Root Cause:** Environment variables for tokens were not correctly passed through `uv run` in certain environments.
- **Resolution:** Reverted to a stable token configuration and ensured correct environment variable propagation.
- **Verification:** Successfully authorized and connected from external clients.
