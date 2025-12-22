# Runbook — Refresh and Export

**Owner:** Silent Architect  
**Last Updated:** 2025-12-01  
**Status:** 🟡 In Progress — API in place, worker handler pending

---

## Purpose

Operational steps for container re-embedding (refresh) and export jobs triggered via `/v1/admin/refresh` and `/v1/admin/export`.

---

## Refresh

**API:** `POST /v1/admin/refresh`

**Request:** `{ "container": "uuid|slug", "strategy": "in_place|shadow", "embedder_version": "1.x.x" }`

**Behavior:** Enqueues a `refresh` job in Postgres with payload (container_id, name, strategy, embedder_version). Worker handler TBD; current stub avoids worker crashes.

**How to run:**
1. `curl -X POST http://localhost:7801/v1/admin/refresh -H "Content-Type: application/json" -d '{"container":"expressionist-art","strategy":"in_place","embedder_version":"1.1.0"}'`
2. Observe job in DB: `SELECT id, status, payload FROM jobs WHERE kind='refresh' ORDER BY created_at DESC LIMIT 5;`
3. Tail worker logs (once handler lands) for progress; expect `running → done`.

**Success criteria:** job transitions to `done`; chunks/embeddings updated to target embedder_version; Qdrant collections recreated if needed; stats updated.

**Failure modes:**
- `CONTAINER_NOT_FOUND` → confirm slug/UUID.
- `timeout/retries exceeded` → job status `failed`; inspect `jobs.error`; retry after fixing cause.

**Notes:** worker implementation still required for re-embed and swap; add reconciliation before cutover.

---

## Export

**API:** `POST /v1/admin/export`

**Request:** `{ "container": "uuid|slug", "format": "tar|zip", "include_vectors": true, "include_blobs": true }`

**Behavior:** Enqueues an `export` job in Postgres with payload (container_id, name, format, include_vectors, include_blobs). Worker handler TBD; current stub avoids worker crashes.

**How to run:**
1. `curl -X POST http://localhost:7801/v1/admin/export -H "Content-Type: application/json" -d '{"container":"expressionist-art","format":"tar","include_vectors":true,"include_blobs":true}'`
2. Verify job enqueued: `SELECT id, status, payload FROM jobs WHERE kind='export' ORDER BY created_at DESC LIMIT 5;`
3. Worker (future): stream tarball to MinIO path `exports/{container_id}/{job_id}.tar` with manifest.json + vectors + blobs; return signed URL.

**Success criteria:** job `done`; export artifact stored; signed URL returned (future).

**Failure modes:** same as refresh; MinIO/FS errors once implemented.

**Notes:** add checksum + manifest versioning; consider encrypting exports if policy requires.

---

## Monitoring & Metrics

- Track job counts by kind/status: `jobs` table; expose Prometheus counters (future) `llc_jobs_total{kind,status}`.
- Alert on jobs stuck `running` > visibility_timeout or `failed` spikes.

---

## Rollback

- Refresh: revert to previous embedder_version snapshot; restore Qdrant collection from last snapshot.
- Export: N/A (read-only); delete failed artifacts from MinIO if partial.

---

## References

- `single_source_of_truth/architecture/API_CONTRACTS.md` (admin.refresh/export)
- `single_source_of_truth/architecture/DATA_MODEL.md` (jobs schema)
- `single_source_of_truth/work/PHASE2_BUILDPLAN.md` (Phase 2 tasks)
