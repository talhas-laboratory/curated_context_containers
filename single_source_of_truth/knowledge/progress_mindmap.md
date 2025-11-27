# Progress Mindmap — Actionable Checklist
Source: `progress_mindmap.txt` (2025-11-21). Update checkboxes as work lands. Architecture decisions (Postgres-native queue ADR-001, pluggable rerank ADR-002, local-first stack FastAPI+Postgres+Qdrant+MinIO) are baked into the steps.

## Phase 1 — MCP v1 Local (deterministic single-container prototype)

### Completed (reference only)
- [x] Foundation & SSoT discipline (personas, INDEX/CONTEXT/PROGRESS/diary protocols).
- [x] Architecture & contracts published (SYSTEM, DATA_MODEL, API_CONTRACTS, ADR-001, ADR-002 draft).
- [x] Backend core (FastAPI MCP endpoints with auth/policies, hybrid search, diagnostics/issue codes, embedding cache).
- [x] Ingestion & retrieval pipelines (text/PDF chunking, dedup hash+semantic, MinIO storage, Qdrant upsert, hybrid search with freshness/dedup, rerank hook stub).
- [x] Metrics/observability (Prom counters/histograms, structured logs, diagnostics rail data surfaced).
- [x] Automation (docker compose stabilized, Makefile targets, bootstrap_db, golden runner with latency budgets, ingest→search integration test, Playwright E2E script).
- [x] CI & runbooks (GitHub Actions migrate→pytest+cov→smoke→golden, E2E optional; runbooks for setup/install, backup/restore, incident response; sample manifests and golden queries).
- [x] Frontend baseline (Next.js App Router, MCP HTTP client + React Query hooks, gallery + search workspace, diagnostics rail, document modal, keyboard shortcuts, reduced-motion variant, Storybook stories).

### Remaining — Actionable Steps
- [x] Performance & rerank (ADR-002 execution)
  - [x] Implement HTTP rerank adapter (opt-in via manifest/request), cap top-N (≤50), timeout ≤200 ms with budget guard to keep P95 <900 ms.
  - [x] Emit rerank diagnostics/issue codes (`rerank_applied`, provider, `RERANK_TIMEOUT`, `RERANK_DOWN`) and ensure deterministic fallback when disabled.
  - [x] Run golden queries with rerank enabled; record nDCG/recall and confirm latency budgets hold. (Baseline + rerank nDCG=1.0, recall=1.0, p95≈379 ms.)
- [x] Testing gaps (TD-001/TD-002)
  - [x] Add frontend unit/RTL coverage with MSW for MCP client hooks and UI states; wire into CI.
  - [x] Harden Playwright E2E (search path) and make CI gate required instead of optional.
  - [x] Add latency/error-path backend tests (timeout/no_hits/rate_limit) and PDF E2E scenario.
- [ ] Frontend quality gates
  - [x] Implement loading/empty/error states across gallery/search/modal; ensure a11y labels and focus traps hold.
  - [ ] Validate keyboard navigation + reduced-motion edge cases with live data; fix diagnostics rail edge cases.
- [x] Documentation alignment
  - [x] Reconcile CONTEXT/PROGRESS/phase1_completion to remove drift (e.g., Celery/RQ mentions, outdated % complete); recompute hash and log in diary.
  - [x] Update DECISIONS/LESSONS with rerank strategy status once implemented.
- [x] Phase 1 close-out
  - [x] Write retrospective diary entry with metrics snapshot (latency, nDCG/recall, queue depth).
  - [x] Archive ADRs as accepted/proposed as appropriate; set Phase 2 starting line after baseline artifacts captured.

## Execution Slices (for sequencing)
- [x] Slice 1 — Doc Sync & Truth Pass: reconcile PROGRESS/CONTEXT/phase1_completion, recompute hash, diary update.
- [x] Slice 2 — Backend Perf & Rerank: implement ADR-002 adapter + diagnostics, run golden (latency + quality).
- [x] Slice 3 — Frontend Reliability: add frontend tests + MSW, harden Playwright, cover loading/error/empty/a11y/keyboard.
- [x] Slice 4 — Search Quality & Latency Validation: add PDF ingest→search E2E, latency/error-path tests, capture baseline artifacts (golden baseline+rERANK with PDF/error cases: p50/p95≈336/428 and 338/448; ndcg≈0.823, recall≈0.8).
- [x] Slice 5 — Phase 1 Close-Out: retrospective, DECISIONS/LESSONS updates, archive ADRs, Phase 2 kickoff doc.

## Phase 2 — Multimodal + Rerank (planned)
- [ ] Image ingestion pipeline and crossmodal search modes (text→image, image→text) with Qdrant payload parity.
- [ ] Rerank provider integration + caching; expose rerank diagnostics in UI.
- [ ] Refresh/export endpoints and UI flows; MinIO snapshot packaging aligned to manifest policy.
- [ ] Multi-container selector and crossmodal UI updates; extend golden queries for multimodal/rerank quality.

## Phase 3 — Multi-Vector + Observability (planned)
- [ ] Multi-vector embeddings/router support; container router cutover tooling.
- [ ] Full observability dashboards and automated eval gates for nDCG regression.
- [ ] Production hardening: rate limiting/backoff, DLQ automation, security audit.
