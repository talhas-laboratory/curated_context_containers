# ADR-004: Rerank Provider Integration and Caching

**Date:** 2025-11-27  
**Status:** Proposed  
**Deciders:** Silent Architect (builder), Orchestrator  
**Tags:** rerank, latency, caching, retrieval, diagnostics

---

## Context

- Phase 1 implemented an optional rerank adapter with budget guard and diagnostics but no external provider wiring or caching; rerank can be disabled per request/manifest.
- Phase 2 requires a real rerank provider (API or local) plus caching to preserve latency budgets (p95 < 900 ms end-to-end) and reduce provider cost/latency.
- Constraints: local-first stack on MacBook Air; minimal new services; deterministic fallback when provider absent/down; observability for rerank timings/issue codes; top-k in limited to keep budget.

---

## Decision

We will:

1) **Define a provider interface** with an HTTP API implementation (configurable `RERANK_PROVIDER`, `RERANK_API_URL`, `RERANK_API_KEY`) supporting text queries over text/image candidates.
2) **Clamp rerank budgets**: `rerank_timeout_ms = min(request_budget_remaining - safety, provider_timeout_cap)` (default cap 200 ms; safety window 100 ms) with top_k_in=50 → top_k_out=10 unless overridden by manifest/request.
3) **Add rerank result caching** keyed by `(query_hash, candidate_ids_in_order, provider, model_version)` stored in Postgres table `rerank_cache` with TTL (default 24h) and size guard; cache hit bypasses provider call.
4) **Degrade deterministically**: on timeout/error/down, return fused ranking with `issues=[RERANK_TIMEOUT|RERANK_DOWN]`, diagnostics noting applied=false; no retries in critical path.
5) **Expose observability**: metrics for rerank latency, cache hit/miss, provider errors; diagnostics include provider, applied flag, timeout_ms, cache_status.

---

## Rationale

- Budget clamping and small top_k bound keep rerank from violating the 900 ms SLO.
- Cache reduces repeated provider calls for identical query+candidate sets, lowering cost/latency while keeping determinism.
- Explicit issue codes and diagnostics preserve transparency when rerank is skipped or partial.
- Provider interface keeps room for a local model later without API surface changes.

---

## Alternatives Considered

### Option 1: Local cross-encoder only
**Pros:** No external dependency/cost; fully offline.
**Cons:** Larger local footprint; potential latency > budget on M2 without tuning.
**Reason for Rejection:** Higher effort/risk for Phase 2; API option faster to integrate while leaving local path open.

### Option 2: No caching
**Pros:** Simpler implementation.
**Cons:** Higher cost/latency; repeated calls for same query set; risks budget breaches.
**Reason for Rejection:** Cache materially improves latency/cost; overhead is small.

### Option 3: Increase top_k_in beyond 50
**Pros:** Potential quality lift.
**Cons:** Higher latency/cost; risks budget; marginal lift unproven.
**Reason for Rejection:** Budget priority; can revisit after measurements.

---

## Consequences

### Positive
- Provides real rerank quality path with controlled latency and deterministic fallback.
- Cache improves performance and reduces provider spend.
- Diagnostics clarify when rerank influenced results.

### Negative
- Adds dependency on external provider availability when enabled.
- New Postgres table for cache introduces maintenance (TTL eviction).
- Slight code complexity in search pipeline (budget math, cache layer).

### Neutral
- If provider disabled, behavior matches Phase 1 (fused ranking) with minimal overhead.

---

## Implementation Notes

**Steps Required:**
1. Add settings/env + manifest fields for rerank provider (`provider`, `model`, `timeout_ms`, `top_k_in`, `top_k_out`, `cache_ttl_s`, `enabled`).
2. Create Postgres table `rerank_cache` (query_hash text, candidate_fingerprint text, provider text, model text, ttl_ts, scores jsonb) with indexes on ttl/provider.
3. Implement provider client (HTTP) and interface; clamp timeout to budget; serialize candidates as text for fingerprint.
4. Wire cache lookup/store in rerank stage; include cache hit/miss in diagnostics; enforce size guard (e.g., top_k_in ≤ 50).
5. Update tests: rerank stage unit tests (timeout/down/cache hit/miss), integration/golden path with rerank enabled; ensure issue codes surface.
6. Update API_CONTRACTS diagnostics fields to include rerank provider/applied/cache_status; document in architecture notes.

**Affected Components:** mcp-server services/search.py, rerank adapter, settings; Postgres migrations; tests; manifests; API_CONTRACTS; golden runner.

**Migration Strategy:** Add table/migration; default provider `none` leaves behavior unchanged; manifests opt-in; cache table prunable via TTL cleanup job.

**Rollback Plan:** Set provider to `none` in config/manifest; disable cache use; drop table if fully reverting.

---

## Success Metrics

- Rerank stage latency p95 ≤ 200 ms when enabled; overall search p95 < 900 ms.
- Cache hit rate target ≥30% on repeated queries; no stale hits beyond TTL.
- Golden rerank runs show nDCG/recall lift vs baseline within budget.
- Zero provider-induced failures surfaced to clients beyond typed issue codes.

---

## References

- ADR-002 (rerank strategy baseline)
- Phase 2 goals in `single_source_of_truth/PROGRESS.md`
- Golden metrics expectations in `CONTEXT.md`

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2025-11-27 | Initial draft | Silent Architect |
