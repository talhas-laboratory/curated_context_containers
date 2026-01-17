import uuid

from workers.pipelines import _upsert_document


class StubCursor:
    """Very small cursor stub that replays prepared row batches."""

    def __init__(self, row_batches):
        # Each execute() call consumes one batch of rows to serve via fetchone()
        self._row_batches = [list(batch) for batch in row_batches]
        self.queries = []
        self._current_rows = []

    def execute(self, query, params=None):
        self.queries.append((query.strip(), params))
        self._current_rows = self._row_batches.pop(0) if self._row_batches else []

    def fetchone(self):
        if not self._current_rows:
            return None
        return self._current_rows.pop(0)


def test_upsert_document_marks_real_duplicates():
    doc_id = uuid.uuid4()
    cursor = StubCursor(
        [
            [{"id": doc_id}],  # existing document
            [{"any": 1}],  # chunk exists -> treat as duplicate
        ]
    )

    result_id, duplicate = _upsert_document(
        cursor,
        uuid.uuid4(),
        {"uri": "https://example.com/doc.pdf"},
        "application/pdf",
        "hash-1",
    )

    assert result_id == doc_id
    assert duplicate is True


def test_upsert_document_reprocesses_stale_documents_without_chunks():
    doc_id = uuid.uuid4()
    cursor = StubCursor(
        [
            [{"id": doc_id}],  # existing doc
            [],  # no chunks -> treat as stale
        ]
    )

    result_id, duplicate = _upsert_document(
        cursor,
        uuid.uuid4(),
        {"uri": "https://example.com/doc.pdf", "title": "Doc"},
        "application/pdf",
        "hash-2",
    )

    assert result_id == doc_id
    assert duplicate is False
    assert any("UPDATE documents" in query for query, _ in cursor.queries)


def test_upsert_document_inserts_when_missing():
    generated = uuid.uuid4()
    cursor = StubCursor(
        [
            [],  # no existing document
            [{"id": generated}],  # returning id from insert
        ]
    )

    result_id, duplicate = _upsert_document(
        cursor,
        uuid.uuid4(),
        {"uri": "https://example.com/doc.pdf"},
        "application/pdf",
        "hash-3",
    )

    assert result_id == generated
    assert duplicate is False






















