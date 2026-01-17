# Step 6 — Testing & Automation (Execution-Proof Plan)

Purpose: Ship contract, integration, smoke, golden, and CI automation such that quality gates can run unattended locally and in CI. Follow these tasks top-to-bottom; each line is actionable and tied to concrete routes, scripts, and acceptance criteria.

## References
- API contracts: `single_source_of_truth/architecture/API_CONTRACTS.md`
- Data model: `single_source_of_truth/architecture/DATA_MODEL.md`
- Existing scripts: `scripts/bootstrap_db.sh`, `scripts/compose_smoke_test.sh`, `run_golden_queries.sh` (to extend)
- Services: `/v1/containers/add`, `/v1/search`, Postgres DSN `LLC_POSTGRES_DSN`, Qdrant `LLC_QDRANT_URL`, MinIO `LLC_MINIO_*`
- Auth: bearer token `LLC_MCP_TOKEN`

## 1) Integration test (backend, real deps)
- [x] Create `mcp-server/tests/test_integration_search.py` (or similar) that:
  - Spins against real Postgres/Qdrant/MinIO (compose stack) using env DSNs.
  - Bootstraps with `scripts/bootstrap_db.sh` or inserts fixtures (one container id `000...001`).
  - Calls `/v1/containers/add` with `{"container":"expressionist-art","sources":[{"uri":"https://example.com/integration","mime":"text/plain","meta":{"text":"integration test body"}}]}` using bearer token.
  - Waits/polls until at least 1 document/chunk ingested (query DB or sleep + search).
  - Calls `/v1/search` with `{"query":"integration","container_ids":["000...001"],"mode":"hybrid","diagnostics":true,"k":5}`.
  - Asserts: HTTP 200; `returned>=1`; `diagnostics.timings_ms` present; `issues` empty; `diagnostics.latency_budget_ms` >0.
  - Cleans up inserted doc/chunk rows.
- [x] Wire test to skip if env `CI_INTEGRATION=0` or if deps unreachable; emit clear skip reason.

## 2) Golden queries pipeline upgrade
- [x] Update `run_golden_queries.sh` to:
  - Accept `--budget-ms` flag; fail with non-zero exit if `total_ms` > budget for any query.
  - Emit JSON summary to `.artifacts/golden_summary.json` with per-query `returned`, `total_hits`, `timings_ms.total_ms`, `issues`.
  - Optionally compute placeholder nDCG/recall (can be stubbed returning `null` with TODO noted).
- [x] Add README block in `scripts/` describing usage, required env vars, sample output paths.

## 3) CI workflow (contract → smoke → integration → golden)
- [x] Create/extend GitHub Actions workflow (e.g., `.github/workflows/ci.yml`) to:
  - Spin Postgres/Qdrant/MinIO via services.
  - Steps: `make migrate` → `pytest mcp-server/tests` (unit/contract) → `make smoke` → integration test step (mark as required) → golden queries step (allowed to fail only if nDCG stubbed? set `continue-on-error: false`).
  - Pass bearer token via secret (`LLC_MCP_TOKEN`), set DSNs to service hosts.
  - Cache `~/.cache/pip` and npm if frontend tests added later.
- [x] Ensure artifacts upload: `./.artifacts/golden_summary.json`, smoke logs, pytest JUnit XML.

## 4) End-to-end script (search UI path)
- [x] Add Playwright or lightweight Node script under `frontend/e2e/search.e2e.ts` (or `scripts/e2e_search.js`) that:
  - Launches against running frontend (`npm run dev` or static) and MCP stack.
  - Sets token via env/localStorage.
  - Opens `/containers/<id>/search`, submits query “smoke”, waits for results list >0, opens document modal, verifies provenance text present.
  - Exits non-zero on failure; configurable base URLs via env.
- [x] Document how to run locally (`npm run e2e:search`) and how to skip in CI if frontend not built.

## 5) Coverage/metrics surfacing
- [x] Add pytest coverage config (`pytest --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing`) to backend test command; note in Makefile or docs.
- [x] If Playwright used, enable HTML trace on failure and store under `.artifacts/e2e-trace.zip` in CI.

## 6) Acceptance checklist
- [ ] `pytest mcp-server/tests/test_integration_search.py -q` passes against compose services.
- [ ] `run_golden_queries.sh --budget-ms 900` produces `.artifacts/golden_summary.json` and exits 0 when under budget; exits non-zero when over budget.
- [ ] CI workflow runs migrate → unit/contract → smoke → integration → golden; artifacts uploaded.
- [ ] E2E search script runs locally end-to-end or is marked skipped with rationale in `TECHNICAL_DEBT.md`.
- [ ] Docs updated (scripts README and/or `single_source_of_truth/work/BLOCKERS.md` if something is deferred).
