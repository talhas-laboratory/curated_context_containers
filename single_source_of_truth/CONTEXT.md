# Project Context — Live State Snapshot

**Last Updated:** 2026-01-16T14:49:24Z  
**Hash:** 4a17b86c5b95c3207ade429528a7000e475267f1d57016ba861320b4a0a90979  
**Phase:** 2 — Multimodal + Rerank (Complete; Phase 3 planning next)

---

## Project Identity

**Name:** Local Latent Containers  
**Codename:** Curated Context Containers  
**Mission:** Theme-scoped vector collections with calm, deterministic retrieval via MCP

---

## Current State Summary

### Frontend (IKB Designer)
- **Status:** 🟢 Phase 2 complete  
- **State:** Next.js App Router with MCP HTTP client + React Query hooks; gallery/search workspace; document modal; diagnostics rail; keyboard/reduced-motion. Multi-container selector, crossmodal query input/preview, graph/hybrid graph modes with tabular context + diagnostics (Graph Playwright E2E passing), maintenance (refresh/export) UI with job status + focus traps, MSW/RTL coverage; Playwright search flows hardened.  
- **Next:** Plan Phase 3 UI (observability dashboards, deeper diagnostics), add Playwright coverage for maintenance flows, Storybook notes for Phase 3 components.

### Backend (Silent Architect)
- **Status:** 🟢 Phase 2 complete  
- **State:** Auth enforced; manifests drive policy/latency; hybrid/crossmodal/graph search with diagnostics/issue codes; rerank provider + cache; integration + contract tests green; golden runner supports text/image and rerank budgets. Image ingest (MinIO originals+thumbs, modality collections), crossmodal search, rerank provider/cache, refresh/export endpoints, admin fastpath for UI testing, graph endpoints (upsert/search/schema) backed by Neo4j + Qdrant node embeddings.  
- **Next:** Plan Phase 3 (multi-vector/observability), link ADR-003/ADR-004 into DATA_MODEL/API_CONTRACTS, add refresh/export worker handlers + runbooks, define Phase 3 ADRs.

### Integration & Automation
- **Status:** 🟢 Baseline gates wired  
- **State:** `make smoke` + golden budgeted; integration test hits real Postgres/Qdrant/MinIO/Neo4j; PDF ingest→search integration test passing; CI workflow runs migrate → pytest (cov) → smoke → golden (Playwright required; skip via `CI_E2E=0`); runbooks published (setup, backup/restore, incident response). Golden runner supports image queries/container arrays + graded relevance via titles/URIs; graph contracts/integration + Playwright graph spec now green locally.  
- **Next:** Home server deployment packaging (frontend container + production compose + reverse proxy), then Phase 3 eval design (multi-vector/observability).

---

## Active Work Streams

| Stream | Owner | Status | Current Task |
|--------|-------|--------|--------------|
| Architecture | Silent Architect | 🟢 | Phase 2 complete; drafting Phase 3 scope (multi-vector/observability) |
| Design System | IKB Designer | 🟢 | Phase 2 complete; planning Phase 3 UI/observability surfaces |
| MCP Protocol | Silent Architect | 🟢 | Phase 2 endpoints stable (refresh/export/admin fastpath) |
| Documentation | Orchestrator | 🟢 | Phase 2 closed; prepping Phase 3 kickoff notes |

---

## Technology Stack

### Backend
- **Language:** Python 3.11
- **Framework:** FastAPI
- **Database:** PostgreSQL (registry + BM25 + job queue + embedding cache)
- **Vector Store:** Qdrant
- **Object Storage:** MinIO
- **Task Queue:** Postgres-native queue (ADR-001)
- **Embeddings:** google-gemma3-text (API; ready for multimodal expansion)

### Frontend
- **Framework:** Next.js / React
- **Styling:** Tailwind CSS
- **Animation:** Framer Motion
- **State:** React Context / Zustand (TBD)

### Infrastructure
- **Container:** Docker Compose
- **Target:** MacBook Air M2 (local single-node)
- **Volumes:** Named volumes for persistence

---

## Key Constraints

1. **Monochrome Chrome:** All UI chrome is grayscale; IKB blue reserved for data/orbs only
2. **Local-First:** Must run entirely on M2 MacBook Air
3. **Deterministic:** No LLM generation in critical path; vector retrieval + rerank only
4. **Privacy:** All data stays local; no telemetry except opt-in observability
5. **Latency:** P95 search < 900ms local (hybrid retrieval + optional rerank)

---

## Open Questions

1. Frontend state management: Context or Zustand? (IKB Designer to decide)
2. Rerank provider: API or local model? (Silent Architect to decide — Phase 2)
3. Initial container themes for Phase 2 multimodal? (Product decision needed)

---

## Recent Decisions

| Date | Decision | Rationale | Owner |
|------|----------|-----------|-------|
| 2025-11-09 | Adopt `single_source_of_truth/` folder structure | Persistent memory across agent sessions | Orchestrator |
| 2025-11-09 | Three-agent system: Orchestrator, Silent Architect, IKB Designer | Separation of coordination, backend, frontend concerns | Orchestrator |
| 2025-11-23 | Rerank execution per ADR-002 (budget-guarded, opt-in; fallback deterministic) | Preserve p95 <900 ms with optional quality lift | Silent Architect |
| 2025-11-23 | Golden eval expansion (PDF + latency/no-hit cases) with budgets enforced | Broaden coverage before Phase 2 | Orchestrator |
| 2026-01-16 | Home server deployment choices: Tailscale VPN-only, buildx+GHCR, agent-local MCP gateway | Private access with reproducible builds | Orchestrator |
| 2026-01-16 | Home server routing and persistence: reverse proxy with `http://llc.<tailnet>` and volumes under `/srv/llc` | Single URL on tailnet + predictable backups | Orchestrator |

---

## Blockers

*(See work/BLOCKERS.md for detailed impediments)*

**Current:** None — project initialization phase

---

## Next Session Priorities

1. **Orchestrator:** Execute home server deployment plan (production compose + reverse proxy + secrets); update runbooks/docs after wiring.
2. **Silent Architect:** Align MCP server env/CORS and compose topology for production; add optional gateway container if needed.
3. **IKB Designer:** Containerize frontend and verify MCP base URL/token handling for production builds.

---

## Context Hash

**Algorithm:** SHA-256 of CONTEXT.md + PROGRESS.md + VISION.md  
**Current Hash:** 9ac54c91b3d10cad876e89b8b47d731c371e0b2b2702c3feb10572f53dccbd94  
**Purpose:** Verify agents start session with synchronized state
