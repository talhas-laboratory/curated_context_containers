# Next Slice Plan — Hybrid Retrieval + Ingestion Hardening

## Objective
Deliver a functional hybrid search path (vector + BM25 + RRF placeholder) backed by real ingestion pipelines (text + PDF) so each `/containers/add` request results in searchable chunks with provenance and diagnostics. Automate validation via smoke + golden query scripts.

## Workstreams

### 1. Ingestion Hardening
- Text pipeline: chunking, dedup placeholder, provenance, metrics
- PDF pipeline: text extraction stub, modality tagging, provenance
- Embedding adapters (stub hooking) + storage (MinIO placeholder)
- Dedup + caching scaffolding (hash + semantic TODOs)

### 2. Retrieval Stack
- Qdrant adapter scaffolding (collection management, upsert/search stubs)
- BM25 integration (tsvector already in place, add weights)
- RRF fusion placeholder merging vector + BM25
- Diagnostics expansion (stage timings, candidate counts)

### 3. Automation & Tooling
- Compose smoke test: ingest sample, run search, check diagnostics
- Golden queries: integrate script + ENV instructions, add CI hook placeholder
- Docs updates: PROGRESS/CONTEXT/WORK, README, scripts

## Task Breakdown

1. **Text Ingestion**
   - Implement chunker (fixed size + provenance) and update worker pipeline
   - Write dedup stub (hash map) and log duplicates
   - Ensure chunks include tsvector updates (trigger or direct)

2. **PDF Ingestion**
   - Stub text extraction (using PyMuPDF placeholder) and create pdf-specific chunks
   - Tag modalities and store metadata for diagnostics

3. **Embedding/Storage Adapters**
   - Create placeholder embedding adapter (returns zero vector) with TODO markers
   - Scaffold MinIO adapter to store raw payload references (even if no actual upload yet)

4. **Qdrant Adapter**
   - Build client wrapper, collection creation, upsert/search stubs
   - Wire vector search stage to return fake scores while placeholder data exists

5. **Hybrid Fusion**
   - Implement BM25 scoring via `ts_rank_cd`
   - Combine BM25 + vector scores via RRF placeholder
   - Update `/v1/search` to accept `mode` param (semantic|hybrid|bm25) and respond accordingly

6. **Diagnostics & Observability**
   - Extend SearchResponse diagnostics with stage timings, candidate counts
   - Add worker metrics counters (ingest jobs processed) and log ingestion duration

7. **Automation**
   - Update `compose_smoke_test.sh` to verify hybrid search path
   - Hook `run_golden_queries.sh` into Makefile target (`make golden-queries`)
   - Document how to run these in README / scripts README

8. **Documentation & Tracking**
   - Update PROGRESS (mark ingestion design complete, note new tasks)
   - Update CONTEXT + CURRENT_FOCUS with this slice plan
   - Record plan summary in diary after implementation

## Dependencies
- Ensure `psql`, Docker, Alembic, Qdrant/minio containers available (already in compose)
- No external internet access needed thanks to placeholders

## Definition of Done
- `/containers/add` creates rows consumable by `/search` using hybrid pipeline
- Smoke test runs: migrate → ingest sample text/PDF → hybrid search showing stage diagnostics
- Golden query script runs without errors, returning at least stub metrics
- single_source_of_truth updated with new slice status

## Status (2025-11-09)
- [x] Text ingestion chunking/dedup + provenance logged
- [x] PDF ingestion placeholder path (shares chunker, modality tagging)
- [x] Placeholder embedding + Qdrant adapters wired into search
- [x] Hybrid search (semantic/bm25/hybrid modes) with RRF + diagnostics
- [x] Smoke + golden query scripts upgraded and tied into Makefile
- [x] Documentation/state synced (this plan, PROGRESS, CONTEXT, diary)
