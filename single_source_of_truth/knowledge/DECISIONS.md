# Decisions Log — Key Project Choices

**Last Updated:** 2025-11-23T15:15:00Z  
**Owner:** Orchestrator (contributions welcome)

This file records notable decisions, their rationale, and status to keep agents aligned. Use ADRs in `architecture/ADR/` for deeper architectural analysis.

---

## Active/Accepted Decisions

### 2025-11-23 — Rerank Execution Strategy (ADR-002)
- **Decision:** Keep rerank opt-in and budget-guarded; clamp rerank timeout to latency budget; proceed with deterministic fallback when provider absent.
- **Rationale:** Preserves p95 latency <900 ms locally while allowing quality lift when provider is available; avoids failures when rerank is disabled.
- **Evidence:** Golden baseline + rerank with PDF/error cases p95≈428/448 ms; ndcg_avg≈0.823; recall_avg≈0.8.
- **Status:** Accepted (Phase 1)

### 2025-11-23 — Golden Evaluation Expansion
- **Decision:** Golden suite includes PDF content plus latency/no-hit cases; judgments mapped to ingested doc_ids; budgets enforced at 900 ms (p95).
- **Rationale:** Ensures retrieval quality and latency are validated on realistic modalities and error paths before Phase 2.
- **Evidence:** `.artifacts/golden_summary.baseline.json` and `.artifacts/golden_summary.rerank.json` with all queries returning hits under budget.
- **Status:** Accepted (Phase 1)

### 2025-11-23 — PDF Modality Enablement for expressionist-art
- **Decision:** Allow `pdf` modality in manifest/bootstrap for the seed container; ingest PDFs via text extraction path until renderer lands.
- **Rationale:** Needed for PDF integration/E2E coverage and golden PDF query.
- **Evidence:** `test_pdf_ingest_and_search_against_real_stack` passing; PDF golden query returns expected doc.
- **Status:** Accepted (Phase 1)

---

## Deferred/Planned

- **Rate Limiting:** Rate-limit path remains stubbed in tests; implement and cover in Phase 2/3 hardening.
- **Rerank Provider Integration:** External/local provider wiring deferred to Phase 2 (Multimodal + Rerank).

---

## How to Add

Use the template below for new entries:

```
### YYYY-MM-DD — Title
- **Decision:** ...
- **Rationale:** ...
- **Evidence:** ...
- **Status:** Proposed/Accepted/Rejected/Deferred
```
