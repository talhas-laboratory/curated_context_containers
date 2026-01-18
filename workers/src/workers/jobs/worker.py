"""Minimal worker loop scaffolding against the Postgres-backed queue."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Callable, Iterator, List, Tuple

import psycopg
from psycopg.rows import dict_row

from workers.logging import configure_logging
from workers.config import settings
from workers.metrics import start_metrics_server

POLL_INTERVAL = settings.worker_poll_interval
MAX_RETRIES = settings.worker_max_retries
VISIBILITY_TIMEOUT = settings.worker_visibility_timeout
HEARTBEAT_INTERVAL = settings.worker_heartbeat_interval
ERROR_BACKOFF = settings.worker_error_backoff
LOGGER = configure_logging()


def get_dsn() -> str:
    return settings.postgres_dsn


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(get_dsn(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def claim_job(conn: psycopg.Connection) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
               SET status = 'running', updated_at = NOW(), last_heartbeat = NOW()
             WHERE id = (
                 SELECT id
                   FROM jobs
                  WHERE status = 'queued'
                  ORDER BY created_at ASC
                  LIMIT 1
                  FOR UPDATE SKIP LOCKED
             )
         RETURNING id, kind, payload, retries;
            """
        )
        row = cur.fetchone()
        conn.commit()
        if row:
            record_job_event(conn, row["id"], "running", "claimed")
        return row


def mark_done(conn: psycopg.Connection, job_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status='done', updated_at=NOW() WHERE id=%s",
            (job_id,),
        )
    conn.commit()
    record_job_event(conn, job_id, "done", "completed")


def mark_failed(conn: psycopg.Connection, job_id: str, error: str) -> str:
    """Increment retries; mark failed when retries exceed cap, else requeue."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
               SET status = CASE WHEN retries + 1 >= %s THEN 'failed'::job_status ELSE 'queued'::job_status END,
                   retries = retries + 1,
                   error = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (MAX_RETRIES, error[:500], job_id),
        )
        cur.execute("SELECT status, retries FROM jobs WHERE id=%s", (job_id,))
        next_state = cur.fetchone()
    conn.commit()
    status = next_state["status"] if next_state else "queued"
    record_job_event(conn, job_id, status, f"error: {error[:200]}")
    return status


def record_job_event(conn: psycopg.Connection, job_id: str, status: str, message: str | None = None) -> None:
    """Append an entry into job_events; best-effort (errors swallowed)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_events (job_id, status, message)
                VALUES (%s, %s, %s)
                """,
                (job_id, status, message),
            )
        conn.commit()
    except Exception:  # pragma: no cover - best effort logging
        conn.rollback()


def touch_heartbeat(conn: psycopg.Connection, job_id: str) -> None:
    """Update heartbeat timestamp for a running job."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET last_heartbeat = NOW(), updated_at = NOW() WHERE id = %s",
            (job_id,),
        )
    conn.commit()


def reap_stale_jobs(conn: psycopg.Connection) -> List[Tuple[str, str]]:
    """Recycle jobs stuck in running past visibility timeout."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
               SET status = CASE WHEN retries + 1 >= %s THEN 'failed'::job_status ELSE 'queued'::job_status END,
                   retries = retries + 1,
                   updated_at = NOW(),
                   last_heartbeat = NOW()
             WHERE status = 'running'
               AND COALESCE(last_heartbeat, updated_at, created_at) < NOW() - (%s || ' seconds')::interval
         RETURNING id, status, retries;
            """,
            (MAX_RETRIES, VISIBILITY_TIMEOUT),
        )
        rows = cur.fetchall()
    conn.commit()
    recycled: List[Tuple[str, str]] = []
    for row in rows or []:
        recycled.append((row["id"], row["status"]))
        record_job_event(conn, row["id"], row["status"], "reaped_stale")
    return recycled


def process_job(conn: psycopg.Connection, job: dict) -> None:  # pragma: no cover
    from workers.pipelines import run_pipeline
    heartbeat: Callable[[], None] = lambda: touch_heartbeat(conn, job["id"])
    run_pipeline(conn, job["kind"], job, heartbeat=heartbeat)


def worker_loop() -> None:
    with get_connection() as conn:
        while True:
            reap_stale_jobs(conn)
            job = claim_job(conn)
            if not job:
                time.sleep(POLL_INTERVAL)
                continue
            LOGGER.info("job_claimed", job_id=job["id"], kind=job["kind"], retries=job["retries"])
            try:
                touch_heartbeat(conn, job["id"])
                process_job(conn, job)
            except Exception as exc:  # pylint: disable=broad-except
                status = mark_failed(conn, job["id"], str(exc))
                LOGGER.error(
                    "job_failed",
                    job_id=job["id"],
                    kind=job["kind"],
                    error=str(exc),
                    retries=job["retries"] + 1,
                    status=status,
                )
                time.sleep(ERROR_BACKOFF)
            else:
                mark_done(conn, job["id"])
                LOGGER.info("job_completed", job_id=job["id"], kind=job["kind"])


if __name__ == "__main__":
    start_metrics_server()
    worker_loop()
