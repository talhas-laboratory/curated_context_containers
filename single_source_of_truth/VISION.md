# Product Vision — North Star

**Version:** 1.0  
**Status:** Stable  
**Phase Scope:** 1–3 (MCP v1 through multi-vector)

---

## Core Idea

**Local Latent Containers** are theme-scoped vector collections that make personal knowledge retrieval feel calm, deterministic, and inevitable — like memory, not search.

---

## Product Principles

1. **Invisible Intelligence**  
   The system should feel instantaneous and obvious, not impressive or algorithmic.

2. **Themed Coherence**  
   Collections organize by meaning (expressionist-art, stoic-philosophy, product-specs) not by type.

3. **Provenance as Truth**  
   Every result carries its origin story: where it came from, when, why it matters.

4. **Deterministic Retrieval**  
   Hybrid search (vector + BM25) fused with optional rerank. No generative uncertainty.

5. **Local-First, Private Always**  
   All embeddings, all data, all inference runs on your machine. Zero telemetry by default.

6. **Calm Interface**  
   Monochrome chrome, IKB blue reserved for data orbs. Motion is breath, not spectacle.

---

## User Archetypes

### Primary: The Researcher
- **Need:** Search across PDFs, notes, images within themed contexts
- **Pain:** Generic search doesn't understand domain nuance; too much noise
- **Outcome:** Find relevant chunks in <1s with provenance and diagnostics

### Secondary: The Curator
- **Need:** Build personal knowledge collections with multimodal sources
- **Pain:** Existing tools either too technical (vector DBs) or too simple (folders)
- **Outcome:** Add documents/images, define themes, trust the system to surface connections

### Tertiary: The Developer
- **Need:** MCP-accessible vector collections for agent workflows
- **Pain:** Commercial APIs are expensive, opaque, and leak data
- **Outcome:** Self-hosted, deterministic, inspectable retrieval via MCP

---

## Core User Flows

### Flow 1: Create Container
1. Name container (e.g., "expressionist-art")
2. Describe theme (optional; used for context)
3. Choose modalities (text, pdf, image)
4. Set privacy policy (local-only, no export)

### Flow 2: Add Content
1. Select container
2. Drag-drop files or paste URL
3. System ingests: extract → chunk → embed → index
4. Show progress + diagnostics (optional)

### Flow 3: Search Container
1. Enter query (natural language or keywords)
2. Select search mode (semantic, hybrid, crossmodal)
3. System retrieves: embed → vector search → BM25 → fuse → rerank (optional)
4. Display results: snippet + provenance + score + diagnostics toggle

### Flow 4: Inspect Result
1. Click result to open detail modal
2. View: full context, metadata, provenance, related chunks
3. Actions: export, flag, re-ingest, view in original

---

## Success Metrics

### Latency
- **P95 search:** <900ms (local M2 MacBook Air)
- **P50 search:** <400ms
- **Ingestion:** Background; no blocking UX

### Quality
- **nDCG@10:** ≥0.75 on golden query set per container
- **Regression tolerance:** <2% drop on index cutover

### User Experience
- **Time-to-glance:** <1s to identify primary action
- **Squint test:** UI legible at 25% zoom
- **WCAG AA:** All text meets contrast requirements

### Reliability
- **Error rate:** <1% per 1000 requests
- **Index drift:** Postgres ↔ Qdrant <5s lag
- **Data durability:** Zero data loss on graceful shutdown

---

## Non-Goals (This Phase)

- ❌ Generative answers (RAG): only retrieval + rerank
- ❌ Cloud sync: fully local, no multi-device
- ❌ Collaborative containers: single-user only
- ❌ Real-time ingestion: batch processing acceptable
- ❌ Mobile clients: desktop web only

---

## Phase Roadmap

### Phase 1: MCP v1 Local (Current)
- **Scope:** Text + PDF ingestion, hybrid search, MCP endpoints
- **Outcome:** Functional single-container prototype with diagnostics

### Phase 2: Multimodal + Rerank
- **Scope:** Image ingestion, crossmodal search, rerank provider
- **Outcome:** Multi-container system with export/refresh endpoints

### Phase 3: Multi-Vector + Observability
- **Scope:** Multi-vector embeddings, full diagnostics dashboards, eval automation
- **Outcome:** Production-ready system with cutover tooling

---

## Design Philosophy

### Perceptual (IKB Designer)
- **Calm over impressive:** space and type carry hierarchy, not color
- **Invisible until needed:** diagnostics hidden by default, revealed on toggle
- **Motion as breath:** 120–320ms transitions; one animated region max
- **Truth through provenance:** every result shows its origin

### Structural (Silent Architect)
- **Contract-first:** schemas before code, types before data
- **Versioned reality:** never overwrite; cutovers gated by metrics
- **Observability as language:** logs and metrics narrate how answers arise
- **Minimal surface:** expose only MCP; all services private

---

## Brand Essence

**Three Adjectives:**
1. Calm
2. Deterministic
3. Inevitable

**Analogies:**
- Memory, not search
- Garden, not factory
- Light switch, not dashboard

---

## Ultimate Goal

Create a system where knowledge retrieval feels **inevitable** — where finding the right information is as natural and effortless as remembering your own thoughts.

