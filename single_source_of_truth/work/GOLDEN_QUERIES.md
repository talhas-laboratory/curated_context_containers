# Golden Query Set — Phase 1 Draft

**Purpose:** Provide a repeatable set of smoke/evaluation queries per container so we can track relevance and latency. Update this file whenever new containers or scenarios are added.

## Containers Covered

| ID | Name | Theme |
|----|------|-------|
| `00000000-0000-0000-0000-000000000001` | expressionist-art | German Expressionism |

## Queries

| Query ID | Container UUID | Query Text | Expected Evidence | Notes |
|----------|----------------|------------|-------------------|-------|
| GQ-001 | 00000000-0000-0000-0000-000000000001 | "color theory expressionist art" | Results reference palette, chroma, Kandinsky | Baseline relevance |
| GQ-002 | 00000000-0000-0000-0000-000000000001 | "Der Blaue Reiter manifesto" | Mentions of 1912 publication | Tests PDF ingestion |
| GQ-003 | 00000000-0000-0000-0000-000000000001 | "expressionist brushwork" | Snippets describing stroke techniques | Diagnostics toggle on |

## Evaluation Procedure

1. Run `scripts/run_golden_queries.sh` (requires docker stack / MCP running).
2. Record `total_hits`, `returned`, and latency for each query.
3. Note qualitative issues (missing chunks, wrong container) and update `issues` column here if needed.
4. Once ingestion expands, add new containers/queries and ensure this file reflects them.

### Automation Hooks

- CI (`.github/workflows/ci.yml`) now runs `make golden-queries` on push/PR + daily cron (09:00 UTC).
- Summary JSON is written to `.artifacts/golden_summary.json` (and uploaded as `golden-query-report` artifact) so design/frontend can visualize trends without rerunning curl requests.
- Set `GOLDEN_QUERIES_SUMMARY=/desired/path.json` to override location when running locally.
- Script exits non-zero when any golden query returns `returned == 0`, exceeds `--budget-ms`, or p95 exceeds `--budget-p95-ms`; includes p50/p95 latency.
- Optional `--judgments path/to/judgments.json` enables recall/nDCG calculation per query when relevance data exists (keys: query IDs, values: doc_id list or map).
- When `LLC_POSTGRES_DSN` is present, the script performs SQL assertions (chunk counts + embedding cache rows) for each container and fails if any container has zero chunks.

## Next Steps

- Add additional containers once they exist (e.g., `stoic-philosophy`).
- Pipe CI artifact into PATTERNS.md and frontend diagnostics panel once hydration path is in place.
