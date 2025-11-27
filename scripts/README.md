# Scripts

Utility scripts (CLI helpers, golden query runners, data loaders) live here.

- `bootstrap_db.sh` — applies the canonical SQL schema via `psql`
- `compose_smoke_test.sh` — spins up the docker stack, bootstraps the DB, and hits MCP health/list/search endpoints (with a sample ingest)
- `run_golden_queries.sh` — executes `golden_queries.json` against the MCP search endpoint, emits `.artifacts/golden_summary.json`, and fails if any query exceeds `--budget-ms` (latency budget)
- `frontend/tests/e2e/search.spec.ts` — Playwright smoke for the frontend search flow (requires `frontend/node_modules/playwright`; run via `cd frontend && npm run e2e:search`)

## Golden queries usage

```
./scripts/run_golden_queries.sh --budget-ms 900
# Optional relevance judgments for nDCG/recall:
# ./scripts/run_golden_queries.sh --budget-ms 900 --judgments path/to/judgments.json
# Optional p95 guard across all queries:
# ./scripts/run_golden_queries.sh --budget-ms 900 --budget-p95-ms 900
```

Environment:
- `MCP_URL` defaults to `http://localhost:7801`
- `MCP_TOKEN` or `docker/mcp_token.txt` for bearer auth
- `GOLDEN_QUERIES_SUMMARY` overrides artifact output path (default `.artifacts/golden_summary.json`)
- `JUDGMENTS_PATH` (or `--judgments`) optional JSON map of query IDs to doc_id relevances for nDCG/recall
- `BUDGET_P95_MS` optional aggregate latency guard (fails if p95 exceeds)

The script writes a JSON summary with per-query timings/issues, latency percentiles (p50/p95), and exits non-zero if any query returned `0` results or exceeded the latency budget (per query or p95). Missing or empty judgments are skipped with a warning.

## E2E search usage

```
cd frontend
npm run e2e:search
# To skip in CI: CI_E2E=0 npm run e2e:search
```

Environment:
- `FRONTEND_URL` (default `http://localhost:3000/containers/expressionist-art/search`)
- `NEXT_PUBLIC_MCP_TOKEN`/`LLC_MCP_TOKEN` for bearer auth propagated to localStorage
- `NEXT_PUBLIC_MCP_BASE_URL` defaults to `http://localhost:7801`
