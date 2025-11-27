# ADR-003: Image Ingestion and Crossmodal Search

**Date:** 2025-11-27  
**Status:** Proposed  
**Deciders:** Silent Architect (builder), Orchestrator  
**Tags:** ingestion, retrieval, multimodal, crossmodal, storage

---

## Context

- Phase 2 requires adding image ingestion and enabling crossmodal search (text→image and image→text) while keeping local-first constraints on MacBook Air M2.
- Existing stack uses Nomic Embed Multimodal 7B (API) for text/PDF embeddings (1408-dim cosine vectors) and Qdrant per-container collections; MinIO stores blobs; Postgres holds registry/jobs/tsv.
- Latency SLO: search p95 < 900 ms with rerank budget guard; ingestion should remain offline/async via workers.
- Constraints: no new heavy services; keep deterministic pipelines; preserve manifest-driven configuration; maintain provenance and diagnostics; keep payload parity between Postgres/Qdrant/MinIO.

---

## Decision

We will:

1) **Adopt Nomic Embed Multimodal 7B for image embeddings** (same model family as text) at 1408 dims, cosine distance, to ensure crossmodal compatibility without new models.
2) **Implement an image ingestion pipeline** in workers that fetches an image, hashes it, stores original + 2k-edge thumbnail in MinIO, embeds the image, and upserts a single `image` chunk into Postgres/Qdrant with provenance/meta. Semantic dedup uses hash + cosine ≥0.92 reuse when possible.
3) **Create per-container Qdrant image collections** named `c_<container_id>_image` (size=1408, cosine, HNSW M=32/ef=64) with payload parity to text chunks (doc_id, chunk_id, uri, modality, provenance, meta).
4) **Extend search to a crossmodal mode** that, when requested, fans out query embeddings to both text and image collections (based on manifest modalities) and fuses results via existing RRF/dedup/freshness. Text queries can return images; image queries can return text/images if enabled.
5) **Expose manifest knobs** for image ingest (thumbnail_max_edge, compress_quality), dedup thresholds, and crossmodal enable/disable per container; enforce in `/v1/containers/add` and search routing.

---

## Rationale

- Using the same multimodal embedder for text and image keeps crossmodal search simple (one model, cosine) and avoids new dependencies.
- Keeping the ingestion flow in workers preserves async/offline processing and reuses existing job infrastructure and observability.
- Separate image collections per container/modality align with current Qdrant layout and allow selective targeting/fusion.
- Manifest-driven gating ensures containers opt into image modality explicitly and keeps privacy/policy constraints intact.

---

## Alternatives Considered

### Option 1: Local CLIP/OpenCLIP model
**Pros:** No external API latency/cost; offline.
**Cons:** Heavier local footprint; new dependency and tuning; duplicate embedder path vs existing Nomic integration.
**Reason for Rejection:** Increases complexity/footprint during Phase 2; current API embedder already multimodal.

### Option 2: Defer image ingestion to Phase 3
**Pros:** Lower near-term effort; keep scope on rerank.
**Cons:** Blocks crossmodal UI/testing and Phase 2 goals; leaves design incomplete.
**Reason for Rejection:** Phase 2 explicitly targets multimodal search; deferral conflicts with roadmap.

### Option 3: Store images only in MinIO, search via captions
**Pros:** Simpler storage; reuse text pipeline.
**Cons:** Requires reliable captioning (not planned); loses true image retrieval.
**Reason for Rejection:** Adds new model dependency (captioning) and weakens crossmodal fidelity.

---

## Consequences

### Positive
- Enables true image retrieval and crossmodal search within existing model family.
- Minimal architectural churn: reuses workers, manifests, Qdrant layout, diagnostics.
- Keeps provenance and payload parity across modalities.

### Negative
- Adds MinIO storage usage (original + thumbnail) and Qdrant footprint per container.
- Increases reliance on Nomic API for images (latency/cost); needs rate-limit handling.
- Slightly more query latency when crossmodal mode fans out to more collections.

### Neutral
- Freshness/dedup semantics extend to images; dedup may behave differently for visually similar assets.

---

## Implementation Notes

**Steps Required:**
1. Extend manifest schema to allow `image` modality and image ingest settings (thumb edge, quality, max size).
2. Add worker image pipeline: fetch → hash → store original/thumbnail in MinIO → embed → write Postgres document/chunk (modality=image, provenance, meta) → upsert Qdrant collection `c_<id>_image`.
3. Add semantic dedup reuse for identical hash and cosine ≥0.92 against existing image vectors; skip re-embed on cache hit.
4. In search service: when mode `crossmodal` (or manifest allows image in `hybrid`), fan out query embedding to image collection(s); fuse with text/BM25 via existing RRF/dedup/freshness pipeline; return thumbnail URL in payload if available.
5. Update API contracts/tests to reflect image modality in list/describe/search responses and diagnostics; add worker tests and integration test (ingest image → search text/image queries).

**Affected Components:** manifests/, workers/pipelines/image.py (new), workers/jobs, mcp-server adapters/services (Qdrant, search), Postgres schema (ensure modality enum covers image), API_CONTRACTS.

**Migration Strategy:** Create image collections lazily on first ingest per container; manifests opt-in; existing containers remain text/PDF-only unless updated.

**Rollback Plan:** Disable `image` modality in manifest and search routing; stop writing to image collections; data remains in MinIO/Qdrant but unused.

---

## Success Metrics

- Image ingest success rate ≥99% per 100 jobs; retries captured in job metrics.
- Crossmodal search latency p95 remains <900 ms (with rerank budget guard) on local stack.
- Golden crossmodal queries achieve nDCG@10 ≥0.75 after judgments.
- No unbounded storage growth: thumbnails generated once; dedup/caching prevents duplicate vectors for identical images.

---

## References

- Phase 2 goal in `single_source_of_truth/PROGRESS.md`
- Manifest knobs for image ingest in `BUILDPLAN.md` (image thumbnail + compression settings)
- Qdrant layout in `architecture/SYSTEM.md`

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2025-11-27 | Initial draft | Silent Architect |
