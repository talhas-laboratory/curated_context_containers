# Project State Evaluation — 2025-11-20

## What I inspected
- Read the Single Source of Truth (INDEX/CONTEXT/PROGRESS/VISION + architecture docs) for intended scope.
- Skimmed code in `mcp-server/` (API layer, services, adapters, metrics), `workers/` (pipelines/adapters/job loop), `frontend/`, `scripts/`, `docker/`, and migrations.
- Ran tests: `pytest mcp-server/tests -q` (1 failing in `tests/test_metrics.py`), `pytest workers/tests -q` (all passing).

## Current state (code-level)
- **Backend (FastAPI)**: Auth enforced via bearer token; list/describe/add/search routes backed by AsyncSession and manifest loader. Search supports semantic/bm25/hybrid with basic stage timings and RRF but no freshness boosts, rerank, ACL/policy enforcement, or dedup in the response path. Embedding adapter is synchronous HTTPX with fallback zero vectors and no cache/rate-limit hooks. Qdrant adapter searches from the event loop via `run_in_executor`, lacks collection lifecycle management, filtering, retries, or payload shape validation. Container stats are read from JSON fields but never updated by services.
- **Workers/Ingestion**: Worker loop polls Postgres and dispatches text/pdf to a shared pipeline. Pipeline handles chunking, SHA/semantic dedup, embedding cache table, MinIO write, and Qdrant upsert. PDF/text share the same placeholder text extraction; no page rendering, MIME-specific extraction, job events/heartbeats, or DLQ/retry backoff beyond simple `retries` counter. Container stats and job events are not updated.
- **Frontend**: Next.js App Router scaffold with layout/globals, Tailwind tokens, and three components (`SearchInput`, `ResultItem`, `DiagnosticsRail`) rendered with static sample data. No MCP client, state management, container gallery, document modal, loading/error/empty states, keyboard nav, or accessibility treatments. Storybook scripts exist but no stories beyond component files.
- **Infrastructure/Tooling**: Docker Compose stack defined for postgres/qdrant/minio/mcp/workers; Make targets call shell scripts, with `scripts/bootstrap_db.sh` seeding a sample container. Smoke/golden scripts exist but depend on docker and live stack; no CI wiring observed. Alembic migration wraps raw SQL schema. No runbooks or operational docs yet.
- **Tests/Quality**: Worker unit tests pass. MCP server tests mostly green except `test_observe_search_records_counters` (metrics label shape mismatch after adding `container`/`status` labels). No integration/e2e or frontend tests present.

## Gaps and remaining work (prioritized)
1. **Stabilize observability contract**
   - Fix `observe_search`/Prometheus label expectations and update `mcp-server/tests/test_metrics.py` to pass; align metric labels with BUILDPLAN (container/mode/status).
   - Add structured logging around search/ingest stages to match diagnostics spec.
2. **Search correctness and policy gaps**
   - Implement manifest-driven knobs (latency budgets per container, ACL/policy enforcement, modality filters, freshness boosts, rerank hook) in `mcp-server/app/services/search.py`.
   - Add dedup/freshness/snippet rendering logic and normalize issue codes per `architecture/API_CONTRACTS.md`.
   - Harden Qdrant adapter (collection lifecycle, filters, retries/backoff) and embedding adapter (async client, rate limiting, cache usage).
3. **Ingestion reliability**
   - Add real PDF extraction and page render handling; extend pipelines for images/web when Phase 2 starts.
   - Emit job events/heartbeats, visibility timeouts, DLQ semantics, and update container stats after ingest.
   - Validate manifests before enqueueing jobs; surface job IDs/status in API responses/CLI.
4. **Frontend integration**
   - Build MCP HTTP client + React Query hooks; wire search/list/describe endpoints into UI.
   - Implement container gallery, result list from live data, diagnostics toggle, and document detail modal with provenance.
   - Add loading/error/empty states, keyboard navigation, reduced motion, and accessibility audit per design docs.
5. **Testing & automation**
   - Get `make smoke` running against compose stack (including migrations/bootstrap) and ensure dedup/cache assertions hold.
   - Add contract tests that hit real schemas (not only monkeypatched), ingestion→search integration tests, and start golden query runner in CI.
   - Add frontend component/story tests and minimal E2E (ingest → search → view) once API is live.
6. **Documentation & ops**
   - Update `single_source_of_truth/CONTEXT.md` and `PROGRESS.md` to reflect current code state (beyond 2025-11-09 snapshot).
   - Write runbooks (setup, smoke/golden, backup/restore, incident response) and CLI usage docs; document MCP token handling and env vars.
   - Record ADR for rerank provider strategy before Phase 2.
