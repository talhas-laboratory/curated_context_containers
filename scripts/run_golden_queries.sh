#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
QUERIES_JSON="$ROOT_DIR/golden_queries.json"
MCP_URL=${MCP_URL:-"http://localhost:7801"}
OUTPUT_PATH=${GOLDEN_QUERIES_SUMMARY:-"$ROOT_DIR/.artifacts/golden_summary.json"}
MCP_TOKEN_PATH=${MCP_TOKEN_PATH:-"$ROOT_DIR/docker/mcp_token.txt"}
BUDGET_MS=""
JUDGMENTS_PATH=""
BUDGET_P95_MS=""
RERANK="false"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "python or python3 not found on PATH; set PYTHON_BIN to a valid interpreter." >&2
    exit 1
  fi
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --budget-ms)
      BUDGET_MS="${2:-}"
      shift 2
      ;;
    --budget-ms=*)
      BUDGET_MS="${1#*=}"
      shift
      ;;
    --budget-p95-ms)
      BUDGET_P95_MS="${2:-}"
      shift 2
      ;;
    --budget-p95-ms=*)
      BUDGET_P95_MS="${1#*=}"
      shift
      ;;
    --judgments)
      JUDGMENTS_PATH="${2:-}"
      shift 2
      ;;
    --judgments=*)
      JUDGMENTS_PATH="${1#*=}"
      shift
      ;;
    --rerank)
      RERANK="true"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${MCP_TOKEN:-}" && -f "$MCP_TOKEN_PATH" ]]; then
  export MCP_TOKEN=$(cat "$MCP_TOKEN_PATH")
fi
: "${MCP_TOKEN:=}"
export MCP_TOKEN
export BUDGET_MS
export JUDGMENTS_PATH
export BUDGET_P95_MS
export RERANK

mkdir -p "$(dirname "$OUTPUT_PATH")"

ROOT_DIR="$ROOT_DIR" MCP_URL="$MCP_URL" OUTPUT_PATH="$OUTPUT_PATH" "$PYTHON_BIN" - <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
import math

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency for CI/sql checks
    psycopg = None

def _norm_doc_id(value: str | None) -> str:
    if not value:
        return ""
    return str(value).replace("-", "")

root = Path(os.environ.get("ROOT_DIR", "."))
queries_path = root / "golden_queries.json"
if not queries_path.exists():
    print("golden_queries.json not found", file=sys.stderr)
    sys.exit(1)

queries = json.loads(queries_path.read_text())
mcp_url = os.environ.get("MCP_URL", "http://localhost:7801")
rerank_enabled = os.environ.get("RERANK", "false").lower() == "true"
headers = ["Content-Type: application/json"]
if os.environ.get("MCP_TOKEN"):
    headers.append(f"Authorization: Bearer {os.environ['MCP_TOKEN']}")
budget_env = os.environ.get("BUDGET_MS")
budget_ms = int(budget_env) if budget_env else None
b95_env = os.environ.get("BUDGET_P95_MS")
budget_p95 = int(b95_env) if b95_env else None
judgments_path = os.environ.get("JUDGMENTS_PATH") or ""
judgments = {}
if judgments_path:
    jpath = Path(judgments_path)
    if jpath.exists():
        try:
            content = jpath.read_text().strip()
            if content:
                judgments = json.loads(content)
            else:  # empty file, treat as no judgments
                print(f"Judgments file {jpath} is empty; skipping judgments.", file=sys.stderr)
        except Exception as exc:
            print(f"Failed to read judgments file {jpath}: {exc}", file=sys.stderr)
            judgments = {}
    else:
        print(f"Judgments file {jpath} not found; skipping judgments.", file=sys.stderr)

summary = []
failures = []
containers = set()
latencies = []
for query in queries:
    payload = json.dumps({
        "query": query["query"],
        "container_ids": [query["container"]],
        "rerank": rerank_enabled,
    })
    curl_cmd = [
        "curl", "-s", "-X", "POST",
        f"{mcp_url}/v1/search"
    ]
    for header in headers:
        curl_cmd.extend(["-H", header])
    curl_cmd.extend(["-d", payload])
    result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    results = data.get("results") or []
    dedup_doc_ids = []
    seen_doc_ids = set()
    for val in (_norm_doc_id(res.get("doc_id")) for res in results if res.get("doc_id")):
        if not val or val in seen_doc_ids:
            continue
        seen_doc_ids.add(val)
        dedup_doc_ids.append(val)
    doc_ids = dedup_doc_ids
    row = {
        "id": query["id"],
        "returned": data.get("returned"),
        "total_hits": data.get("total_hits"),
        "timings_ms": data.get("timings_ms", {}),
        "issues": data.get("issues", []),
        "rerank": rerank_enabled,
        "ndcg": None,
        "recall": None,
        "doc_ids": doc_ids,
    }
    total_ms = (row["timings_ms"] or {}).get("total_ms")
    if budget_ms is not None:
        row["budget_ms"] = budget_ms
        row["over_budget_ms"] = max(0, (total_ms or 0) - budget_ms)
        if total_ms and total_ms > budget_ms:
            failures.append(f"{query['id']}:over_budget")
    if total_ms is not None:
        latencies.append(total_ms)
    truth = judgments.get(query["id"])
    if truth:
        if isinstance(truth, dict):
            rels = {_norm_doc_id(str(k)): float(v) for k, v in truth.items()}
        else:
            rels = {_norm_doc_id(str(doc_id)): 1.0 for doc_id in truth}
        gains = []
        for rank, doc_id in enumerate(doc_ids, start=1):
            rel = float(rels.get(_norm_doc_id(doc_id), 0.0))
            if rel > 0:
                gains.append(rel / (math.log2(rank + 1)))
        dcg = sum(gains)
        ideal = sorted(rels.values(), reverse=True)
        idcg = sum(rel / (math.log2(i + 2)) for i, rel in enumerate(ideal))
        row["ndcg"] = round(dcg / idcg, 4) if idcg else 0.0
        found = sum(1 for doc_id in doc_ids if _norm_doc_id(doc_id) in rels)
        row["recall"] = round(found / max(len(rels), 1), 4)
    summary.append(row)
    if (row.get("returned") or 0) == 0:
        failures.append(query["id"])
    containers.add(query["container"])

timing_totals = {}
for row in summary:
    for key, value in (row.get("timings_ms") or {}).items():
        timing_totals.setdefault(key, []).append(value or 0)

averages = {
    "returned": sum((row.get("returned") or 0) for row in summary) / max(len(summary), 1),
    "total_hits": sum((row.get("total_hits") or 0) for row in summary) / max(len(summary), 1),
    "timings": {k: sum(v) / len(v) for k, v in timing_totals.items()},
}
latency_percentiles = {}
if latencies:
    latencies_sorted = sorted(latencies)
    p95_index = int(0.95 * (len(latencies_sorted) - 1))
    p50_index = int(0.5 * (len(latencies_sorted) - 1))
    latency_percentiles["p50_ms"] = latencies_sorted[p50_index]
    latency_percentiles["p95_ms"] = latencies_sorted[p95_index]
    if budget_p95 is not None and latencies_sorted[p95_index] > budget_p95:
        failures.append(f"p95_over_budget:{latencies_sorted[p95_index]}")

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "query_count": len(summary),
    "averages": averages,
    "queries": summary,
}
if budget_ms is not None:
    report["budget_ms"] = budget_ms
if budget_p95 is not None:
    report["budget_p95_ms"] = budget_p95
if latency_percentiles:
    report["latency_percentiles_ms"] = latency_percentiles

dsn = os.environ.get("LLC_POSTGRES_DSN")
sql_checks = {}
if dsn and psycopg is not None:
    try:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            for container_ref in containers:
                cur.execute(
                    "SELECT id FROM containers WHERE name = %s",
                    (container_ref,),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        "SELECT id FROM containers WHERE id = %s",
                        (container_ref,),
                    )
                    row = cur.fetchone()
                if not row:
                    sql_checks[container_ref] = {"error": "container_not_found"}
                    failures.append(f"container_lookup:{container_ref}")
                    continue
                container_id = row[0]
                cur.execute(
                    "SELECT COUNT(*) FROM chunks WHERE container_id = %s",
                    (container_id,),
                )
                chunk_count = cur.fetchone()[0]
                cur.execute(
                    "SELECT COUNT(*) FROM embedding_cache",
                )
                cache_row = cur.fetchone()[0]
                sql_checks[container_name] = {
                    "chunk_count": chunk_count,
                    "embedding_cache_rows_total": cache_row,
                }
                if chunk_count == 0:
                    failures.append(f"sql_chunk_count:{container_name}")
    except Exception as exc:  # pragma: no cover - optional path
        sql_checks = {"error": str(exc)}

if sql_checks:
    report["sql_checks"] = sql_checks

output_path = Path(os.environ.get("OUTPUT_PATH", "."))
output_path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if failures:
    print(f"Golden query failures: {', '.join(failures)}", file=sys.stderr)
    sys.exit(1)
PY
