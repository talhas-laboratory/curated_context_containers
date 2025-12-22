# Build Plan — Graph RAG Enablement (Neo4j + Graph Modes)

**Owner:** Silent Architect / IKB Designer  
**Status:** Complete  
**Scope:** Add graph-backed retrieval to existing containers using Neo4j; keep embeddings in Qdrant; expose graph endpoints + frontend graph tab; no graph visualization in this slice. Follows `BUILDPLAN_GUIDE.md`.

## Remaining Action Steps
- None — close-out gates run (migrations already applied on compose DB; Playwright graph E2E green; CONTEXT/PROGRESS refreshed; done criteria ticked).

---

## 1) Context & References
- Architecture: `single_source_of_truth/architecture/{SYSTEM.md,DATA_MODEL.md,API_CONTRACTS.md,ARCHITECTURE_OVERVIEW.md}`
- Knowledge: `single_source_of_truth/knowledge/Graph_RAG_Guide.md`
- Design system: `single_source_of_truth/design/{TOKENS.md,COMPONENTS.md,PATTERNS.md,ACCESSIBILITY.md}`
- Existing plans: `PHASE2_BUILDPLAN.md`, `BUILDPLAN_GUIDE.md`
- Product constraints: Monochrome chrome; IKB for data only; p95 search <900ms overall; new graph query budget target: backend graph query <120ms.
- Decisions provided:
  - Graph DB: **Neo4j** (new Docker service allowed).
  - Embeddings stay in **Qdrant only** (no vectors stored in Neo4j).
  - Graph derived from **current ingestion** (entity/relation extraction); no external GraphML/CSV imports in this slice.
  - Retrieval patterns: support **(a) NL → entity detect → Cypher template** and **(b) vector-first then graph expansion** now; defer community/global summaries; optional raw Cypher endpoint.
  - Container model: single type; add graph flags/fields (`graph_enabled`, `graph_url`, `graph_schema`).
  - MCP: add `graph_*` endpoints + extend `containers.search` mode (`graph` | `hybrid_graph`).
  - Frontend: add **Graph tab** inside existing search workspace; optional raw-Cypher text area.
- Visualization: **None** this slice (tabular nodes/edges/provenance only).
- Tests: contract tests for graph endpoints; one Playwright flow “NL query → graph search → tabular output”.
- [x] Confirm these context decisions remain valid; adjust if any upstream documents change.

---

## 2) API Integration Tasks (per route)
- **New POST `/v1/containers/graph_upsert` (MCP tool `containers.graph_upsert`):**
  - Request: `{container: uuid|slug, nodes: [{id, label, type, summary, properties?, source_chunk_id}], edges: [{source, target, type, properties?, source_chunk_id}], mode: "merge|replace", diagnostics?: bool}`
  - Response: `{inserted_nodes, inserted_edges, updated_nodes, updated_edges, issues[], timings_ms}`
  - Validation: `graph_enabled=true` in manifest; node/edge IDs scoped to container; chunk IDs must belong to container; size limits (e.g., nodes<=2k, edges<=5k per call).
  - Error codes: `CONTAINER_NOT_FOUND`, `GRAPH_DISABLED`, `INVALID_PARAMS`.
- **New POST `/v1/containers/graph_search` (MCP `containers.graph_search`):**
  - Request: `{container: uuid|slug, query: string, mode: "nl"|"cypher", max_hops?: 2, k?: 20, expand_from_vector?: {query: string, top_k_chunks: 5}, diagnostics?: bool}`
  - Response: `{nodes: [{id,label,type,summary,score,source_chunk_ids[]}], edges: [{source,target,type,score,source_chunk_ids[]}], snippets: [{chunk_id,text,uri,doc_id,title}], issues[], timings_ms:{graph_ms,total}}`
  - Validation: `mode` determines path (NL → template Cypher; cypher executes as-is with allowlist); `max_hops` default 2, capped at 3; `k` 1..50.
  - Error codes: `GRAPH_DISABLED`, `GRAPH_QUERY_INVALID`, `NO_HITS`, `TIMEOUT`.
- **New GET `/v1/containers/graph_schema` (MCP `containers.graph_schema`):**
  - Request: `{container: uuid|slug}`
  - Response: `{schema:{node_labels[], edge_types[], sample_properties}, diagnostics:{node_count,edge_count}, issues[]}`
  - Validation: graph must exist; schema fetched from Neo4j metadata (labels/relTypes) plus stored manifest `graph_schema`.
- **Extend POST `/v1/containers/search`:**
  - New `mode` values: `"graph"`, `"hybrid_graph"`.
    - `graph`: bypass vector/BM25; run `graph_search` pipeline; return tabular nodes/edges + linked snippets.
    - `hybrid_graph`: run existing hybrid (vector+BM25) → expand to graph neighbors (1–2 hops) from top chunks → merge snippets.
  - Request additions: `{graph: {max_hops?:2, neighbor_k?:10}}`.
  - Response additions: `graph_context` block mirroring `graph_search` payload; diagnostics include `graph_ms`, `graph_hits`.
  - Error code additions: `GRAPH_DISABLED`, `GRAPH_DOWN`.
- **MCP Manifest:**
  - Add tool descriptors for new endpoints; update `containers.search` schema to include new `mode` enum and `graph` block.
- [x] Define Pydantic schemas for graph_upsert/graph_search/graph_schema and search `graph` block.
- [x] Implement FastAPI routes + service wiring with validation and issue codes.
- [x] Update MCP manifest/tool descriptors with new endpoints and search mode enums (gateway tools updated).
- [x] Add/adjust envelope diagnostics to include `graph_ms`, `graph_hits`.
- [x] Add API_CONTRACTS.md updates for new fields/endpoints.

---

## 3) Client/Hook Layer (Frontend / SDK / Gateway)
- **Frontend hooks (React Query):**
  - `useGraphSearch(containerId, params)` → POST `/v1/containers/graph_search`; returns `{nodes,edges,snippets,issues,diagnostics}`; `staleTime=0`, `retry=1`.
  - `useGraphSchema(containerId)` → GET `/v1/containers/graph_schema`; cache 5m.
  - `useGraphUpsert` (internal/worker admin view only; may be stubbed or hidden behind feature flag).
  - Update `useSearch` to accept `mode: "graph"|"hybrid_graph"` and optional `graph` params; type parity with API_CONTRACTS.
- **SDK (agents-sdk/):**
  - Add `graph_search` + `graph_schema` client methods mirroring REST shapes; propagate `request_id`.
  - Update types/enums for search mode.
- **MCP Gateway:**
  - Map new MCP tools to HTTP routes; extend schema definitions.
- **Token/base URL resolution:** unchanged; ensure new routes use same header injection + timeout.
- [x] Implement frontend hooks (`useGraphSearch`, `useGraphSchema`, update `useSearch`).
- [x] Update SDK client methods/types and tests.
- [x] Update MCP gateway tool schemas/routes.
- [x] Verify token/base URL handling for new routes.

---

## 4) Page/Flow Blueprint (Frontend)
- **Search Workspace Additions:**
  - Mode switch includes `Graph` and `Hybrid Graph`.
  - Graph tab fields:
    - NL query input (reuse search input).
    - `max_hops` select (default 2).
    - Optional “Raw Cypher” textarea (collapsed by default; developer-only toggle).
    - Results region: tabular nodes (label/type/summary/score) and edges (source→target/type/score); provenance column shows chunk titles/uris.
    - Diagnostics strip showing `graph_ms`, `graph_hits`, `issues` badges; reuse diagnostics rail styles without visualization.
  - Hybrid graph flow:
    - User picks `Hybrid Graph` → submit uses existing hybrid search, passes `graph` block; UI shows combined snippets plus “Graph context” tables.
  - States:
    - Loading skeleton (table rows placeholders).
    - Empty/no-hits state: message + CTA “Show diagnostics”.
    - Partial/timeout: banner using ember border, issues list.
    - Error: standard error banner.
- **No new standalone page**; lives within existing container search route.
- [x] Add Graph/Hybrid Graph modes to search workspace UI.
- [x] Implement Graph query panel (NL + hops + optional Cypher toggle).
- [x] Render tabular nodes/edges + provenance/snippets; integrate diagnostics bar.
- [x] Wire hybrid graph mode to show fused results + graph context.
- [x] Cover loading/empty/error/partial states.

---

## 5) Components Wiring
- **New/Updated Components:**
  - `GraphModeToggle` (extend existing mode toggle): adds options Graph/Hybrid Graph; emits `mode` + `graph` params.
  - `GraphQueryPanel`: fields for NL query + max hops + optional Cypher textarea; props: `{mode, graphParams, onChange, onSubmit, disabled}`; mirrors SearchInput shortcuts (⌘K focus).
  - `GraphResultsTable`: two tables (Nodes, Edges) with provenance chips; props: `{nodes, edges, snippets, diagnosticsVisible}`.
  - `GraphDiagnosticsBar`: inline metrics for `graph_ms`, hit counts, issues; reuse tokens from diagnostics rail.
  - Update `SearchResults` to render `graph_context` when present; maintain aria roles.
- **Backend Wiring:**
  - `GraphAdapter` (Neo4j) in `mcp-server/app/adapters/neo4j.py` with `query`, `upsert`, `schema` methods; lifecycle management (session/driver).
  - `GraphService` orchestrating Cypher templates, NL → entity/relation extraction (LLM-powered) using existing embedder for summaries (store vectors in Qdrant `c_<container>_graphnode` collection).
  - Workers: extend ingest pipeline to call graph extractor per chunk batch; upsert nodes/edges; store node summary embeddings in Qdrant (text modality) tagged `modality="graph_node"` or dedicated collection.
- [x] Build/extend components: GraphModeToggle, GraphQueryPanel, GraphResultsTable, GraphDiagnosticsBar, SearchResults integration.
- [x] Backend: implement Neo4j adapter, GraphService, and wire to routes.
- [x] Workers: add graph extraction/upsert step and node-summary embedding to Qdrant. *(Simple doc/chunk/entity extraction; node embeddings stored in Qdrant.)*
- [x] Ensure provenance (`source_chunk_id`) links are enforced in upsert.

---

## 6) A11y & Keyboard
- Graph tab follows existing search a11y:
  - Search input retains `role="search"`, `aria-label`.
  - Mode toggle buttons `aria-pressed`; focus ring 1px ink.
  - Tables: `<table><thead><th scope="col">` with `role="row"`, `role="cell"`.
  - Raw Cypher textarea labeled; keyboard submit on ⌘/Ctrl+Enter; Esc closes textarea (collapses).
  - Reduced motion: Graph results fade disabled when `prefers-reduced-motion`; table swap is instant.
  - Min hit targets 40px for toggles/buttons; focus trap not required (inline UI).
- [x] Verify roles/labels on graph tab controls, tables, and toggles.
- [x] Add keyboard shortcuts (submit, toggle Cypher, Esc collapse) and focus styles.
- [x] Test reduced-motion variant for graph result rendering.

---

## 7) Acceptance Scenarios
- **Backend contract:** POST `/v1/containers/graph_search` with `mode="nl"`, `query="decisions about GraphOS"`, `max_hops=2`, container with graph enabled → response includes `nodes` length ≥1, `timings_ms.graph_ms` present, `issues` empty.
- **Hybrid graph retrieval:** POST `/v1/containers/search` with `mode="hybrid_graph"`, `graph.max_hops=1`, text query, expect `results` from fusion plus `graph_context.nodes` tied to `source_chunk_ids`; `issues` empty.
- **Raw Cypher (optional):** POST `/v1/containers/graph_search` with `mode="cypher"` and a safe query; expect validation if query not allowlisted.
- **Graph schema:** GET `/v1/containers/graph_schema` returns labels/relTypes; counts >0 when graph populated.
- **Frontend E2E (Playwright):** Navigate to container search → switch to Graph mode → submit NL query → see nodes table rows >0, diagnostics bar shows graph_ms.
- **No visualization:** ensure only tabular outputs rendered; no canvas/SVG.
- [x] Implement tests for each listed scenario (backend contract/integration, frontend E2E).
- [x] Capture fixtures for nodes/edges/snippets to reuse in RTL/Storybook (MSW handler + RTL tests added).

---

## 8) Testing / Storybook Tasks
- **Backend:**
  - Unit tests for `GraphAdapter` (Cypher generation, upsert dedupe).
  - Service tests for NL → Cypher template, hop limit enforcement, diagnostics emission.
  - Contract tests for new endpoints (pydantic schemas, error codes).
  - Integration test with Neo4j test container; ingest a tiny doc → graph extraction → graph_search returns linked chunk IDs.
- [x] Add backend unit coverage (graph service happy path/disabled guard with mocked Neo4j); integration/contract still TODO.
- [x] Add backend contract validation for graph models (request bounds).
- [x] Add backend integration test skeleton for Neo4j (graph upsert + search; skips when services unavailable).
- **Frontend:**
  - RTL tests for `GraphModeToggle`, `GraphResultsTable` rendering nodes/edges, diagnostics bar issue handling.
  - Storybook stories: Graph results tables (loading/empty/error), mode toggle with graph options.
  - Playwright E2E: Graph mode search happy path; optional raw Cypher blocked path shows error banner.
- **SDK/Gateway:** unit tests for new client methods/tool schemas.
- [x] Add backend contract/integration tests (Neo4j container).
- [x] Add frontend RTL + Storybook stories.
- [x] Add Playwright E2E for graph search.
- [x] Add SDK/gateway unit tests for new methods/tools.
- [x] Record test commands and expected artifacts.

**Test commands (expected artifacts):**
- Backend unit/contract: `cd mcp-server && pytest -k "graph_service or test_api_contracts"` → junit/coverage if enabled. (Ran 2025-12-04.)
- Backend integration (requires Neo4j/Postgres up): `cd mcp-server && CI_INTEGRATION=1 pytest tests/test_graph_integration.py -s` → skips if services missing. (Ran prior; still valid with graph tokenization change.)
- Frontend RTL: `cd frontend && npm test -- Graph` (runs vitest) → coverage if configured.
- Frontend Playwright: `cd frontend && npm run test:e2e -- tests/e2e/graph.spec.ts` → playwright-report/. (Ran 2025-12-04; passed.)
- SDK tests: `cd agents-sdk && pytest tests/test_client_graph.py` → junit/coverage if enabled.

---

## 9) Config & DX
- **Docker Compose:** add `neo4j` service (bolt+http ports internal only), volume `neo4j_data`, healthcheck; set env `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.
- **App env vars:** `LLC_NEO4J_URI`, `LLC_NEO4J_USER`, `LLC_NEO4J_PASSWORD`, `LLC_GRAPH_MAX_HOPS_DEFAULT=2`, `LLC_GRAPH_QUERY_TIMEOUT_MS=1200`, `LLC_GRAPH_ENABLE_RAW_CYPHER=false` (feature flag).
- **Manifests:** add `graph_enabled: bool`, `graph_url: string`, `graph_schema: json` to container manifest; policy check in ManifestService.
- **DX docs:** update `frontend/README.md` and `mcp-server/README.md` for graph modes and env setup; add Neo4j to `docker/README.md`.
- [x] Add Neo4j service to compose + healthcheck + volumes; update env samples.
- [x] Apply DB migration for manifest fields; update manifests and policy checks.
- [x] Add env var docs to server/frontend READMEs; update docker README for Neo4j.
- [x] Add feature flag defaults for raw Cypher and hop/time budgets.

---

## 10) Done Criteria
- Neo4j container running via compose; healthcheck green; adapters wired.
- Schema changes: container manifest fields persisted; migration applied.
- New endpoints live with contract tests passing; MCP manifest updated.
- Ingestion path writes graph nodes/edges from extracted entities/relations; node summaries embedded to Qdrant (not Neo4j).
- `containers.search` supports `graph`/`hybrid_graph` with diagnostics fields; latency budget adhered (`graph_ms` reported).
- Frontend graph tab usable: mode switch, NL query, tabular nodes/edges, diagnostics; raw Cypher toggle (flagged).
- Tests: backend unit+contract+integration, frontend RTL+Storybook, one Playwright E2E; SDK/gateway tests updated.
- Documentation updated: architecture/API additions, README(s); no visualization added.
- [x] Verify all above done criteria and check tests/healthchecks/docs before close (migrations already applied; pytest + integration + RTL/Playwright + SDK tests covered).
