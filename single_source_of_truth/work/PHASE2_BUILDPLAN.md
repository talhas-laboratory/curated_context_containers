# Phase 2 Build Plan — Multimodal + Rerank

**Last Updated:** 2025-11-23

This is the tickable action list for Phase 2. Each checkbox is sized to fit one agent session. **Agents MUST** (a) read `INDEX.md`, `CONTEXT.md`, `PROGRESS.md`, and `CURRENT_FOCUS.md` before starting, (b) update this file + `CONTEXT.md` + `PROGRESS.md` + diary entry after finishing a checkbox, and (c) leave a one-line comment at each step when checking it off (date/result/metrics).

## Slices (execute top-to-bottom)

- [x] **P2.1 — Kickoff & Hash Sync** (Orchestrator): Set Phase 2 start line in `CONTEXT.md`/`PROGRESS.md`; note priorities in `CURRENT_FOCUS.md`; recompute context hash; diary entry logged. *(2025-11-27 — Phase 2 marked in progress; hash refreshed; diary added.)*
- [x] **P2.2 — ADRs: Image Ingest + Rerank Provider/Cache** (Silent Architect): Draft/accept ADRs for image pipeline + rerank provider/caching; document constraints/SLAs; link to DATA_MODEL/API_CONTRACTS. *(2025-11-27 — ADR-003/ADR-004 drafted; awaiting acceptance; follow-up to link DATA_MODEL/API_CONTRACTS.)*
- [ ] **P2.3 — Backend: Image Ingestion Pipeline** (Silent Architect): Implement workers for image ingest (thumbs, hash, cache reuse), MinIO paths, Qdrant image collections; unit tests + worker tests; manifest knobs honored.
- [ ] **P2.4 — Backend: Crossmodal Search Path** (Silent Architect): Add query/image dual-mode search, payload parity, diagnostics for modality hits; contract tests + integration hitting real stack.
- [ ] **P2.5 — Backend: Rerank Provider Integration** (Silent Architect): Wire provider client (API/local), clamp budgets, add caching, enrich diagnostics (applied/timeout/down); golden run with rerank enabled under p95<900ms.
- [ ] **P2.6 — Backend: Refresh Endpoint** (Silent Architect): Implement `/v1/admin/refresh` end-to-end (jobs, worker handler, status surfacing); tests + runbook entry.
- [ ] **P2.7 — Backend: Export Endpoint** (Silent Architect): Implement `/v1/containers/export` tarball with manifest+metadata+blobs; MinIO pathing + access guard; tests + runbook entry.
- [ ] **P2.8 — Frontend: Multi-Container Selector** (IKB Designer): Add container selector/state, adjust hooks for multi-target searches, UI wiring + a11y; RTL/Playwright updates.
- [ ] **P2.9 — Frontend: Crossmodal UI & Diagnostics** (IKB Designer): Add image query input/preview, mode toggles (semantic/hybrid/crossmodal/rerank), diagnostics rail surfacing rerank/provider status; tests + Storybook.
- [ ] **P2.10 — Frontend: Refresh/Export Flows** (IKB Designer): UI for refresh/export triggers + progress, error/empty states, focus traps; RTL/Playwright coverage.
- [ ] **P2.11 — Golden Expansion & Benchmarks** (Silent Architect): Extend golden queries/judgments for image + crossmodal cases; run baseline + rerank; record latency/nDCG/recall in artifacts; gate budgets.
- [ ] **P2.12 — Documentation & Runbooks Sync** (Orchestrator): Update `CONTEXT.md`, `PROGRESS.md`, `CURRENT_FOCUS.md`, `BLOCKERS.md` (if any), `TECHNICAL_DEBT.md` (new debt), `knowledge/DECISIONS.md`, `knowledge/LESSONS.md`, and relevant runbooks; diary entry; recompute context hash.

**Reminder:** Do not proceed to the next checkbox until the current one is checked with a comment and the SSoT files are updated.
