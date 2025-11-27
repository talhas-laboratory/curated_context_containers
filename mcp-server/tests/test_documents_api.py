"""Tests for document management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.documents import (
    DeleteDocumentResponse,
    DocumentItem,
    ListDocumentsResponse,
)
from app.services import documents as documents_service

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer local-dev-token"}


@pytest.fixture(autouse=True)
def override_services(monkeypatch):
    async def fake_list(session, request):
        return ListDocumentsResponse(
            request_id="list-1",
            container_id="container-1",
            documents=[
                DocumentItem(
                    id="doc-1",
                    uri="https://example.com/doc.pdf",
                    title="Doc 1",
                    mime="application/pdf",
                    hash="hash",
                    state="active",
                    chunk_count=3,
                    meta={},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ],
            total=1,
            timings_ms={"db_query": 1},
        )

    async def fake_delete(session, request):
        if request.document_id == "missing":
            raise ValueError("DOCUMENT_NOT_FOUND")
        return DeleteDocumentResponse(
            request_id="del-1",
            document_id=request.document_id,
            timings_ms={"db_query": 2},
        )

    monkeypatch.setattr(documents_service, "list_documents_response", fake_list)
    monkeypatch.setattr(documents_service, "delete_document_response", fake_delete)
    yield
    app.dependency_overrides.clear()


def test_list_documents_endpoint():
    response = client.post(
        "/v1/documents/list",
        json={"container": "expressionist-art"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["container_id"] == "container-1"
    assert len(payload["documents"]) == 1
    assert payload["documents"][0]["chunk_count"] == 3


def test_delete_document_endpoint():
    response = client.post(
        "/v1/documents/delete",
        json={"container": "expressionist-art", "document_id": "doc-1"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == "doc-1"


def test_delete_document_missing_returns_404():
    response = client.post(
        "/v1/documents/delete",
        json={"container": "expressionist-art", "document_id": "missing"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "DOCUMENT_NOT_FOUND"

