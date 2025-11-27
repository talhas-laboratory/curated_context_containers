"""
Integration test that runs against the real stack (Postgres/Qdrant/MinIO + MCP API).

Skips automatically when CI_INTEGRATION=0 or when services are unreachable.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx
import psycopg
import pytest
from psycopg.rows import dict_row

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKERS_SRC = REPO_ROOT / "workers" / "src"
if str(WORKERS_SRC) not in sys.path:
    sys.path.append(str(WORKERS_SRC))

# Ensure worker settings resolve to host-exposed services when running outside docker.
BASE_URL = os.getenv("MCP_URL", "http://localhost:7801")
POSTGRES_DSN = os.getenv("LLC_POSTGRES_DSN", "postgresql://local:localpw@localhost:5433/registry")
os.environ.setdefault("LLC_POSTGRES_DSN", POSTGRES_DSN)
os.environ.setdefault("LLC_QDRANT_URL", os.getenv("LLC_QDRANT_URL", "http://localhost:6333"))
os.environ.setdefault("LLC_MINIO_ENDPOINT", os.getenv("LLC_MINIO_ENDPOINT", "http://localhost:9000"))

try:
    from workers.pipelines import run_pipeline  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency guard
    run_pipeline = None
    _PIPELINE_IMPORT_ERROR = exc
else:
    _PIPELINE_IMPORT_ERROR = None

DEFAULT_CONTAINER_ID = UUID("00000000-0000-0000-0000-000000000001")
SOURCE_URI = "https://example.com/integration"
PDF_SOURCE_URI = "https://example.com/integration.pdf"


def _load_token() -> str | None:
    token = os.getenv("LLC_MCP_TOKEN")
    if token:
        return token.strip()
    token_path = REPO_ROOT / "docker" / "mcp_token.txt"
    if token_path.exists():
        return token_path.read_text().strip()
    return None


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _require_stack() -> None:
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        resp.raise_for_status()
    except Exception as exc:
        pytest.skip(f"MCP server not reachable at {BASE_URL}: {exc}")
    try:
        with psycopg.connect(POSTGRES_DSN, connect_timeout=5):
            pass
    except Exception as exc:
        pytest.skip(f"Postgres unreachable at {POSTGRES_DSN}: {exc}")


def _bootstrap_database() -> None:
    script = REPO_ROOT / "scripts" / "bootstrap_db.sh"
    if not script.exists():
        pytest.skip("bootstrap_db.sh missing")
    env = {**os.environ, "LLC_POSTGRES_DSN": POSTGRES_DSN}
    try:
        subprocess.run([str(script)], check=True, env=env, capture_output=False)
    except FileNotFoundError:
        pytest.skip("psql not available for bootstrap_db.sh")
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"bootstrap_db.sh failed: {exc}")


def _enqueue_ingest(token: str, *, source: dict | None = None) -> str:
    payload_source = source or {
        "uri": SOURCE_URI,
        "mime": "text/plain",
        "meta": {"text": "integration test body"},
    }
    payload = {
        "container": "expressionist-art",
        "sources": [payload_source],
    }
    resp = httpx.post(
        f"{BASE_URL}/v1/containers/add",
        json=payload,
        headers=_headers(token),
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    jobs = data.get("jobs") or []
    assert jobs, "add_to_container did not return jobs"
    return jobs[0]["job_id"]


def _process_job_via_pipeline(job_id: str) -> None:
    if run_pipeline is None:
        pytest.skip(f"workers pipeline unavailable: {_PIPELINE_IMPORT_ERROR}")
    with psycopg.connect(POSTGRES_DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, kind, payload FROM jobs WHERE id = %s", (UUID(job_id),))
            job = cur.fetchone()
        assert job, "queued job missing from jobs table"
        run_pipeline(conn, job.get("kind") or "ingest", job, heartbeat=None)
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status='done', updated_at=NOW() WHERE id=%s", (UUID(job_id),))
            cur.execute(
                "INSERT INTO job_events (job_id, status, message) VALUES (%s, %s, %s)",
                (UUID(job_id), "done", "integration_test"),
            )
        conn.commit()


def _wait_for_chunk() -> None:
    seen = 0
    with psycopg.connect(POSTGRES_DSN) as conn:
        for _ in range(6):
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chunks WHERE container_id = %s", (DEFAULT_CONTAINER_ID,))
                row = cur.fetchone()
                seen = row[0] if row else 0
            if seen:
                break
            time.sleep(0.5)
    assert seen > 0, "no chunks ingested for default container"


def _search(token: str, query: str = "integration") -> dict:
    resp = httpx.post(
        f"{BASE_URL}/v1/search",
        json={
            "query": query,
            "container_ids": [DEFAULT_CONTAINER_ID.hex],
            "mode": "hybrid",
            "diagnostics": True,
            "k": 5,
        },
        headers=_headers(token),
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


def _cleanup(job_id: str | None, uris: list[str] | None = None) -> None:
    target_uris = uris or [SOURCE_URI]
    with psycopg.connect(POSTGRES_DSN) as conn, conn.cursor() as cur:
        for uri in target_uris:
            cur.execute(
                "DELETE FROM documents WHERE container_id = %s AND uri = %s",
                (DEFAULT_CONTAINER_ID, uri),
            )
        if job_id:
            cur.execute("DELETE FROM job_events WHERE job_id = %s", (UUID(job_id),))
            cur.execute("DELETE FROM jobs WHERE id = %s", (UUID(job_id),))
        conn.commit()


@pytest.mark.integration
def test_ingest_and_search_against_real_stack():
    if os.getenv("CI_INTEGRATION") == "0":
        pytest.skip("integration tests disabled via CI_INTEGRATION=0")

    token = _load_token()
    if not token:
        pytest.skip("Missing LLC_MCP_TOKEN and docker/mcp_token.txt")

    _require_stack()
    _bootstrap_database()

    job_id: str | None = None
    try:
        job_id = _enqueue_ingest(token)
        _process_job_via_pipeline(job_id)
        _wait_for_chunk()
        data = _search(token)
    finally:
        _cleanup(job_id, [SOURCE_URI])

    assert data.get("returned", 0) >= 1
    assert not data.get("issues"), f"Unexpected issues returned: {data.get('issues')}"
    timings = data.get("timings_ms") or {}
    assert "total_ms" in timings
    diagnostics = data.get("diagnostics") or {}
    assert (diagnostics.get("latency_budget_ms") or 0) > 0


@pytest.mark.integration
def test_pdf_ingest_and_search_against_real_stack():
    if os.getenv("CI_INTEGRATION") == "0":
        pytest.skip("integration tests disabled via CI_INTEGRATION=0")

    token = _load_token()
    if not token:
        pytest.skip("Missing LLC_MCP_TOKEN and docker/mcp_token.txt")

    _require_stack()
    _bootstrap_database()

    pdf_source = {
        "uri": PDF_SOURCE_URI,
        "mime": "application/pdf",
        "meta": {"text": "pdf integration content with figures"},
        "title": "integration-pdf",
    }

    job_id: str | None = None
    try:
        job_id = _enqueue_ingest(token, source=pdf_source)
        _process_job_via_pipeline(job_id)
        _wait_for_chunk()
        data = _search(token, query="pdf integration")
    finally:
        _cleanup(job_id, [PDF_SOURCE_URI])

    assert data.get("returned", 0) >= 1
    issues = data.get("issues") or []
    assert "NO_HITS" not in issues
    assert data.get("diagnostics", {}).get("latency_budget_ms", 0) > 0
