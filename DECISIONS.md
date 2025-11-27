# Key Decisions Log — Institutional Memory

**Last Updated:** 2025-11-09T00:30:00Z

---

## Purpose

This document provides a chronological log of key project decisions that shape the product, architecture, and design. For detailed architecture decisions, see `architecture/ADR/`.

---

## Decision Log

### 2025-11-09: Adopt Single Source of Truth Folder Structure
**Context:** Need persistent memory across agent sessions to prevent state fragmentation.

**Decision:** Create `single_source_of_truth/` folder as mandatory environment for all agents. All agents must read from and write back to this folder at the start and end of each session.

**Rationale:**
- Prevents state desynchronization across sessions
- Enables true multi-agent coordination
- Provides audit trail of all decisions and progress
- Makes project state queryable and navigable

**Impact:**
- Agents must follow explicit session initialization/closure protocols
- Documentation discipline required (read-before-write, write-back-always)
- Folder structure becomes the "operating system" for the project

**Owner:** Orchestrator

---

### 2025-11-09: Three-Agent System (Orchestrator, Silent Architect, IKB Designer)
**Context:** Need clear separation of concerns for coordination, backend, and frontend work.

**Decision:** Adopt three-agent architecture:
- **Orchestrator:** Coordination, context synchronization, progress tracking
- **Silent Architect:** Backend systems, architecture, deterministic logic
- **IKB Designer:** Frontend UI/UX, components, perceptual design

**Rationale:**
- Clear ownership reduces coordination overhead
- Personas encode domain expertise (technical vs perceptual)
- Orchestrator ensures single source of truth maintenance

**Impact:**
- Each agent has clear domain folder (architecture/ vs design/)
- Cross-references required (e.g., IKB Designer reads API_CONTRACTS.md)
- Orchestrator mediates conflicts via CONTEXT.md

**Owner:** Orchestrator

---

### 2025-11-09: Append-Only Diary Folder
**Context:** Need temporal log of all sessions without losing history.

**Decision:** Use `diary/` folder with YYYY-MM-DD.md files, append-only.

**Rationale:**
- Immutable history provides audit trail
- Easy to trace decisions over time
- No risk of overwriting past reflections
- Temporal navigation (git blame of documentation not sufficient)

**Impact:**
- Folder grows over time (acceptable trade-off)
- Each session must log summary with timestamp
- Reflection quality depends on agent discipline

**Owner:** Orchestrator

---

### 2025-11-09: Four-Tier Documentation Structure
**Context:** Need organized, navigable documentation for different purposes.

**Decision:**
- **Tier 1:** Core state (INDEX.md, CONTEXT.md, PROGRESS.md, VISION.md)
- **Tier 2:** Domain folders (architecture/, design/)
- **Tier 3:** Work tracking (work/)
- **Tier 4:** Knowledge base (knowledge/)

**Rationale:**
- Separation of concerns: state vs domain vs tracking vs learning
- Clear ownership per tier
- Reduces cognitive load (agents know where to look)
- Scales as project grows

**Impact:**
- Requires discipline to maintain folder hygiene
- INDEX.md critical for new agent orientation
- Cross-references between tiers needed

**Owner:** Orchestrator

---

### 2025-11-09: Baseline System Architecture (FastAPI + Postgres + Qdrant + MinIO)
**Context:** Need a deterministic, local-first stack for MCP v1 that can run on a single MacBook Air while remaining extensible for future phases.

**Decision:** Adopt the following baseline architecture for Phase 1:
- FastAPI MCP server exposing list/describe/add/search endpoints with diagnostics and bearer auth
- PostgreSQL 16 for container registry, BM25 search, job queue, and embedding cache metadata
- Qdrant 1.11 for vector storage (collection per container per modality)
- MinIO for blob storage (originals, thumbnails, PDF renders)
- Lightweight worker pool polling Postgres jobs table (Postgres-native queue) for ingestion tasks

**Rationale:**
- All components run cleanly under Docker Compose on Apple Silicon hardware
- Postgres-backed queue keeps stack minimal while ADR evaluates Celery vs RQ for future phases
- Aligns with build plan assumptions (hybrid retrieval, deterministic observability)
- Clear separation of responsibilities simplifies future ADRs (e.g., rerank provider, queue engine)

**Impact:**
- Architecture/SYSTEM.md, DATA_MODEL.md, and API_CONTRACTS.md now reflect this baseline
- Implementation must follow documented contracts; deviations require ADRs
- Enables IKB Designer and future agents to rely on stable data/API shapes

**Owner:** Silent Architect

---

### 2025-11-09: Task Queue Strategy (ADR-001)
**Context:** Need asynchronous ingestion without bloating the local-first compose stack; options considered included Celery+Redis, RQ+Redis, or leveraging Postgres directly.

**Decision:** Adopt a PostgreSQL-native job queue for Phase 1 using `FOR UPDATE SKIP LOCKED` semantics (see `architecture/ADR/ADR-001-task-queue.md`). Workers poll Postgres directly, store payloads + retries in the same DB, and Redis/Celery remain upgrade paths for later phases.

**Rationale:** Fits MacBook Air resource budget, reuses an existing dependency, keeps job + manifest state transactional, and aligns with determinism mandate. Future migration remains straightforward because job payload contracts stay stable.

**Impact:** Compose stack stays minimal; `workers/` implementation focuses on Postgres dispatcher; orchestration docs + CONTEXT updated; future high-throughput phases will revisit ADR.

**Owner:** Silent Architect

---

## Decision Principles

1. **Context Over Mandate:** Decisions documented with full context (why, not just what)
2. **Reversibility Bias:** Prefer decisions that can be reversed if wrong
3. **Data-Driven:** Use metrics and SLOs to validate decisions
4. **Documented Trade-offs:** Always list alternatives considered
5. **ADR for Architecture:** Technical architecture decisions get full ADR in `architecture/ADR/`

---

## Upcoming Decisions (Pending)

| Decision | Owner | Blocker | Target Date |
|----------|-------|---------|-------------|
| Task queue: Celery vs RQ | Silent Architect | Needs benchmarking | Phase 1 |
| Rerank provider: API vs local model | Silent Architect | Needs latency testing | Phase 1 |
| Frontend state management: Context vs Zustand | IKB Designer | Needs component complexity assessment | Phase 1 |
| Initial container themes for prototype | Product | Needs user research or assumption | Phase 1 |

---

**Update Frequency:** When significant decisions made  
**Owner:** Agent making decision (or Orchestrator for cross-cutting decisions)
