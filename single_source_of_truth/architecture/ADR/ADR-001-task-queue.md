# ADR-001: Task Queue Strategy for Phase 1

**Date:** 2025-11-09  
**Status:** Accepted  
**Deciders:** Silent Architect  
**Tags:** architecture, infrastructure, workers

---

## Context

Phase 1 requires asynchronous ingestion (text/PDF/web/image) plus future refresh/export jobs. The system must:
- Run entirely on a single MacBook Air M2 via Docker Compose
- Minimize moving parts while contracts are drafted
- Guarantee deterministic persistence/auditability for jobs
- Operate mostly offline (no managed services) and keep resource usage low (<1 CPU per worker container when idle)

We already depend on PostgreSQL 16 for container registry + BM25. Qdrant and MinIO are also required. We want background jobs now so that ingestion pipelines can start immediately, but we do **not** yet need horizontal scaling or complex routing. BuildPlan sketches an eventual worker pool, and DATA_MODEL.md already includes `jobs` tables suitable for a database-backed queue. We must decide whether to introduce an external broker (Redis/RabbitMQ) with Celery/RQ now or postpone until Phase 2/3 when throughput requires it.

---

## Decision

Adopt a **PostgreSQL-native job queue** for Phase 1 using the existing `jobs` table with `FOR UPDATE SKIP LOCKED` locking semantics. Workers poll Postgres directly, update job status heartbeats, and push DLQ metadata into the same database. Celery/RQ remain future upgrade paths once multi-node scaling or SLA-driven retries demand a dedicated broker.

---

## Rationale

- **Fewer services:** Postgres already runs for metadata; piggybacking avoids introducing Redis/RabbitMQ just for queueing.
- **Transactional integrity:** Job creation, payload storage, and manifest updates stay in a single transaction, simplifying rollback and audit requirements.
- **Local-first footprint:** Each added container taxes the limited CPU/RAM budget on an M2 Air. Avoiding Redis keeps Compose lightweight and easier for contributors to run.
- **Deterministic behavior:** Postgres row-level locks with explicit status columns let us reason about retries and DLQ handling without framework magic.
- **Ease of future migration:** Designing job payloads + worker interfaces around an abstract dispatcher lets us swap in Celery/RQ later without rewriting pipelines.

---

## Alternatives Considered

### Option 1: Celery + Redis
**Description:** Standard Celery workers with Redis broker/backing store.

**Pros:**
- Battle-tested, lots of features (eta, chaining, chords).
- Built-in retry policies, monitoring, and instrumentation.

**Cons:**
- Adds Redis container (RAM + operational overhead) before we need it.
- Celery configuration complexity for a single-node deployment.
- Requires extra transports (kombu) and more dependencies in worker images.

**Reason for Rejection:** Overkill for Phase 1 and violates minimal surface principle; we only need simple FIFO queue semantics right now.

### Option 2: RQ + Redis
**Description:** Lightweight Redis Queue with worker processes per queue.

**Pros:**
- Simpler API than Celery; smaller feature surface.
- Mature ecosystem, good for Python-only stacks.

**Cons:**
- Still introduces Redis + connection management.
- Less flexible scheduling without extra libraries.
- No transactional coupling with Postgres (job + metadata updates split across stores).

**Reason for Rejection:** Adds Redis dependency without solving any urgent problem; still duplicates persistence compared to Postgres.

### Option 3: Postgres-native queue (Chosen)
**Description:** Use `jobs` table + advisory locking (`FOR UPDATE SKIP LOCKED`) for claiming work.

**Pros:**
- Zero new infrastructure, leverages existing DB.
- Strong consistency; job lifecycle and payload resident together.
- Easy to introspect via SQL for debugging/metrics.

**Cons:**
- Less throughput than Redis/Celery under very high load.
- Requires manual implementation of retry/backoff + scheduling utilities.
- Tight coupling to Postgres; scaling to multiple worker nodes needs tuning (partitioning, vacuuming).

**Reason for Acceptance:** Meets Phase 1 requirements with the smallest surface area and keeps migration path open.

---

## Consequences

### Positive
- Compose stack remains limited to Postgres, Qdrant, MinIO, MCP server, and workers.
- Job metadata, payloads, retries, and DLQ auditing live in one database for provenance.
- Easier onboarding: contributors only need Postgres knowledge to inspect jobs.

### Negative
- Custom worker loop + retry logic must be maintained.
- Throughput ceiling tied to Postgres performance; may need partitioning if volume spikes.
- Scheduling features (ETA, periodic tasks) require bespoke implementation.

### Neutral
- Migration to Celery/RQ later will require adapter layer but worker payload contracts already typed, so change is bounded.

---

## Implementation Notes

**Steps Required:**
1. Implement `workers/jobs/dispatcher.py` handling job claim/heartbeat/reset using Postgres transactions.
2. Build `workers/jobs/worker.py` main loop (poll interval, exponential backoff, DLQ handling) using the dispatcher.
3. Expose admin endpoints/CLI to inspect `jobs` + `job_events` tables for troubleshooting.

**Affected Components:**
- PostgreSQL schema (jobs/job_events triggers already defined in DATA_MODEL)
- Worker container images (`workers/` package)
- MCP server IngestService (job creation + status reporting)

**Migration Strategy:**
- None (net-new). If we later adopt Celery/RQ, we can implement compatibility layer reading from Postgres and publishing to Redis while draining outstanding rows.

**Rollback Plan:**
- If Postgres queue proves insufficient, disable dispatcher, deploy Redis + Celery/RQ, and add migration script that publishes outstanding jobs from Postgres into the new broker before dropping dispatcher usage.

---

## Success Metrics

**Metrics to Track:**
- `ingest_queue_depth` (should stay < 20 jobs under normal load)
- `job_lag_seconds` (time from queued → running should remain < 10s)
- Job failure rate (< 5% retries per day)

**Gates:**
- If queue depth exceeds 100 jobs for >10 minutes or lag exceeds 60s, escalate to evaluate Redis-based broker earlier than Phase 2.
- Retry rate >10% for 24h signals need for better retry/backoff instrumentation.

---

## References

- `single_source_of_truth/architecture/SYSTEM.md`
- `single_source_of_truth/architecture/DATA_MODEL.md`
- BuildPlan section "Worker Architecture (Postgres-based Queue)"

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2025-11-09 | Initial decision (Accepted) | Silent Architect |

