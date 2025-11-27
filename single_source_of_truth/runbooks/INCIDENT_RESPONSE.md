# Runbook — Incident Response

Purpose: Quick responses to the most likely production-ish incidents for the local MCP stack.

---

## Nomic embedding rate limits / outages
- **Symptoms:** Search vector stage slow/failing; `VECTOR_DOWN` in issues; logs show HTTP 429/5xx to Nomic.
- **Immediate actions:**
  - Set `NOMIC_API_KEY` to a valid key or rotate if suspected exhausted.
  - Temporarily switch to fallback by unsetting `NOMIC_API_KEY` (workers/server already fallback to zero vectors to stay online; expect degraded relevance).
  - Reduce load: lower `k`, prefer `bm25` mode in UI, or disable vector stage by setting `mode=bm25`.
- **Stabilization:**
  - Increase `embedding_rate_limit_delay` (settings) if throttling persists.
  - Clear or warm embedding cache only if incorrect embeddings suspected; otherwise leave cache intact.

## Search latency spikes / budget breaches
- **Symptoms:** `LATENCY_BUDGET_EXCEEDED` issues; golden queries failing budget; high `total_ms` in diagnostics.
- **Immediate actions:**
  - Check metrics `/metrics` for `llc_search_requests_total` and stage durations.
  - Inspect Qdrant health: `curl http://localhost:6333/healthz`.
  - Verify Postgres query plan: run `EXPLAIN` on `chunks_search_view` if BM25 slow.
  - Use smaller `k` (≤10) and limit containers to active ones.
- **Stabilization:**
  - Lower manifest latency budget only if necessary; prefer fixing slowness.
  - Ensure Qdrant collections exist; recreate via ingestion if missing.
  - Re-run `make smoke` to validate after adjustments.

## Ingestion failures / stuck jobs
- **Symptoms:** Jobs stuck in `queued`/`running`, no chunks/documents appearing; worker logs show repeated errors.
- **Immediate actions:**
  - Query jobs: `psql "$LLC_POSTGRES_DSN" -c "SELECT id, status, retries, error FROM jobs ORDER BY created_at DESC LIMIT 10;"`.
  - Check worker logs: `docker compose -f docker/compose.local.yaml logs workers`.
  - Reap stale jobs: worker loop already requeues; restart workers if heartbeats stale.
- **Common fixes:**
  - Manifest modality violations → ensure source MIME/URI matches allowed modalities; adjust manifest if intentional.
  - MinIO errors → confirm `LLC_MINIO_*` credentials and bucket; restart MinIO if needed.
  - Qdrant connection errors → confirm service up, recreate collection by re-running ingestion after Qdrant is healthy.
- **Validation:** After remediation, rerun `./scripts/bootstrap_db.sh` (if wiping) then `make smoke` and a targeted ingest followed by search.

## Escalation & Logging
- All services expose logs via docker-compose: `docker compose -f docker/compose.local.yaml logs mcp workers`.
- Collect artifacts: `.artifacts/golden_summary.json`, smoke logs, and `/metrics` snapshot before teardown.
- If persistent, file in `work/BLOCKERS.md` with repro steps and affected components.
