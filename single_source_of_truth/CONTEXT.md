# Project Context — Live State Snapshot

**Last Updated:** 2025-11-27T21:30:00Z  
**Hash:** c7581707d169d5de65fb80c3469a79fb052cd0bb0424140fd41b09b864612414  
**Phase:** 2 — Multimodal + Rerank (Planning; Phase 1 complete; frontend polish ongoing)

---

## Project Identity

**Name:** Local Latent Containers  
**Codename:** Curated Context Containers  
**Mission:** Theme-scoped vector collections with calm, deterministic retrieval via MCP

---

## Current State Summary

### Frontend (IKB Designer)
- **Status:** 🟢 Phase 1 complete + "Ethereal Glass" redesign applied  
- **State:** Next.js App Router with MCP HTTP client + React Query hooks; gallery + search workspace + modal wired; keyboard/reduced-motion implemented; Storybook coverage exists; Vitest+RTL+MSW coverage for containers/search components; Playwright search E2E hardened. **New (Nov 27):** Document manager panel in container search sidebar lists embedded files (chunk counts, timestamps) with delete controls wired to MCP `/v1/documents/*` endpoints plus optimistic refresh + MSW/Vitest coverage.  
- **Next:** Phase 2 UX planning — multi-container selector, crossmodal UI, diagnostics rail polish, a11y/keyboard/reduced-motion validation on live data.

### Backend (Silent Architect)
- **Status:** 🟢 Phase 1 complete; rerank adapter executed per ADR-002; job status endpoint added  
- **State:** Auth enforced; manifests drive policy/latency; hybrid search with diagnostics/issue codes; integration test (ingest→search) added; golden runner budgets enforced; rerank adapter opt-in + budget-guarded. Golden baseline+rERANK (with PDF/error cases) p50/p95≈336/428 and 338/448; ndcg_avg≈0.823; recall_avg≈0.8. **New (Nov 27):** File management slice shipped — `/v1/documents/list` + `/v1/documents/delete` APIs with Postgres joins, Qdrant + MinIO cleanup adapters, and FastAPI router/service layer wired + contract tests.  
- **Next:** Phase 2 execution — image ingestion + crossmodal search ADRs/implementation, rerank provider/caching design and wiring.

### Integration & Automation
- **Status:** 🟢 Baseline gates wired  
- **State:** `make smoke` + golden budgeted; integration test hits real Postgres/Qdrant/MinIO; PDF ingest→search integration test passing; CI workflow runs migrate → pytest (cov) → smoke → golden (Playwright required; skip via `CI_E2E=0`); runbooks published (setup, backup/restore, incident response).  
- **Next:** Fold Phase 2 evals (multimodal/crossmodal) into golden suite; automate nDCG/recall calc in runner for multimodal cases.

---

## Active Work Streams

| Stream | Owner | Status | Current Task |
|--------|-------|--------|--------------|
| Architecture | Silent Architect | 🟡 | Phase 2 ADRs/implementation planning (image ingestion, rerank provider/caching, crossmodal search) |
| Design System | IKB Designer | 🟡 | Planning crossmodal UI + multi-container selector + diagnostics rail polish |
| MCP Protocol | Silent Architect | 🟢 | MCP v1 request/response specs complete; Phase 2 endpoints (refresh/export) pending implementation |
| Documentation | Orchestrator | 🟡 | Phase 2 kickoff started; hashes to refresh per updates |

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

---

## Blockers

*(See work/BLOCKERS.md for detailed impediments)*

**Current:** None — project initialization phase

---

## Next Session Priorities

1. **Orchestrator:** Phase 2 kickoff logged; keep CONTEXT/PROGRESS hashes current as slices complete.
2. **Silent Architect:** Author Phase 2 ADRs (image ingestion, rerank provider/caching) and start image pipeline + crossmodal search design.
3. **IKB Designer:** Plan multi-container selector and crossmodal UI; refine diagnostics rail/a11y for new modes.

---

## Context Hash

**Algorithm:** SHA-256 of CONTEXT.md + PROGRESS.md + VISION.md  
**Current Hash:** c7581707d169d5de65fb80c3469a79fb052cd0bb0424140fd41b09b864612414  
**Purpose:** Verify agents start session with synchronized state
