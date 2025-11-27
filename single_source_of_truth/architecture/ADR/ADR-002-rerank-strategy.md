# ADR-002: Rerank Strategy for Phase 2

**Date:** 2025-11-21  
**Status:** Proposed  
**Deciders:** Silent Architect, IKB Designer, Orchestrator  
**Tags:** retrieval, latency, ranking, observability

---

## Context
- Phase 1 hybrid retrieval (BM25 + vector) meets baseline relevance without rerank, but we need a plan for Phase 2.
- Latency budget for search is 900 ms P95; rerank must not blow budget.
- Embedding provider is external (Nomic) with possible rate limits; rerank provider may be similar.
- Diagnostics already capture stage timings/issue codes; rerank slot is stubbed in `app/services/search.py`.

## Decision
Adopt a **pluggable rerank stage** with default no-op and optional external provider:
- Keep rerank disabled by default; enable per-request or via manifest (`retrieval.rerank.enabled=true`).
- Use HTTP provider interface (e.g., Cohere / custom model) behind an adapter with timeout + retries and budget guard.
- Hard cap rerank to top-N (e.g., 50) and short timeout (≤200 ms) so total request respects latency budget.
- Surface rerank diagnostics (`rerank_applied`, provider, timing) and issue codes (`RERANK_TIMEOUT`, `RERANK_DOWN`).

## Rationale
- Maintains current deterministic behavior while allowing opt-in quality boosts.
- Avoids coupling to a single provider; adapter can swap or be disabled.
- Explicit budget guard keeps P95 under SLO and prevents golden queries from regressing.
- Diagnostics-first approach simplifies rollout and rollback.

## Alternatives Considered

### Always-on external rerank
Pros: Best potential quality.  
Cons: High latency risk, external dependency, higher cost.  
Reason rejected: Violates local-first and latency goals for baseline.

### Local rerank (cross-encoder) only
Pros: Fully offline.  
Cons: Heavy model load on laptop; likely exceeds latency/CPU budget.  
Reason rejected: M2 target not ideal; complexity high for Phase 2 start.

## Consequences
**Positive**
- Clear extension point with guardrails.
- Easy to experiment with providers without code churn.

**Negative**
- Added complexity in configuration and testing matrix.
- If left disabled, users may assume rerank exists; docs must clarify defaults.

**Neutral**
- Slight increase in response payload (diagnostics metadata).

## Implementation Notes
1) Add rerank adapter (HTTP) with timeout/retries and feature flag.  
2) Wire manifest + request flag to control rerank; cap top-N; stop if budget exceeded.  
3) Extend diagnostics/metrics and add tests (timeout, down provider, quality smoke).  
4) Gate CI golden queries to record rerank diagnostics but not fail if disabled.

## Success Metrics
- P95 search latency with rerank enabled stays ≤900 ms on golden set.
- No increase in issue rate; rerank issue codes visible when provider fails.
- nDCG@10 improves vs. baseline when rerank is enabled in experiments.

## References
- `app/services/search.py` rerank stub
- `single_source_of_truth/work/BUILDPLAN_EXECUTION.md` Step 8 readiness

## Revision History
| Date | Change | Author |
|------|--------|--------|
| 2025-11-21 | Initial draft | Codex |
