from workers.jobs import worker


class FakeCursor:
    def __init__(self, rows=None, queries=None):
        self.rows = list(rows or [])
        self.queries = queries if queries is not None else []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.queries.append((query.strip(), params))
        return self

    def fetchone(self):
        if not self.rows:
            return None
        return self.rows.pop(0)

    def fetchall(self):
        return list(self.rows)


class FakeConnection:
    def __init__(self, row_batches=None):
        self.row_batches = list(row_batches or [])
        self.queries = []
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self):
        rows = self.row_batches.pop(0) if self.row_batches else []
        return FakeCursor(rows=rows, queries=self.queries)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


def test_mark_failed_requeues_and_logs_event():
    rows = [[{"status": "queued", "retries": 1}]]
    conn = FakeConnection(row_batches=rows)

    status = worker.mark_failed(conn, "job-1", "boom")

    assert status == "queued"
    assert conn.commit_count >= 2  # one for status update, one for event insert
    assert any("job_events" in query for query, _ in conn.queries)


def test_reap_stale_jobs_marks_failed_when_exceeded():
    rows = [[{"id": "job-2", "status": "failed", "retries": 3}]]
    conn = FakeConnection(row_batches=rows)

    recycled = worker.reap_stale_jobs(conn)

    assert recycled == [("job-2", "failed")]
    assert any("job_events" in query and params and params[1] == "failed" for query, params in conn.queries)


def test_touch_heartbeat_updates_timestamp():
    conn = FakeConnection()

    worker.touch_heartbeat(conn, "job-3")

    assert conn.commit_count == 1
    assert any("last_heartbeat" in query for query, _ in conn.queries)
