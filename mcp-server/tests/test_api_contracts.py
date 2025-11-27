"""Contract tests for MCP API schemas and error responses."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ.setdefault("LLC_MCP_TOKEN", "local-dev-token")

from uuid import uuid4

from app.main import app
from app.db.session import get_session
from app.models.containers import (
    AddSource,
    ContainersAddRequest,
    ContainersAddResponse,
    DescribeContainerRequest,
    DescribeContainerResponse,
    ListContainersRequest,
    ListContainersResponse,
    ContainerDetail,
    ContainerStats,
    ContainerSummary,
    JobSummary,
)
from app.models.documents import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    DocumentItem,
    ListDocumentsRequest,
    ListDocumentsResponse,
)
from app.models.search import SearchRequest, SearchResponse, SearchResult
from app.services import containers as container_service
from app.services import jobs as job_service
from app.services import search as search_service


client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer local-dev-token"}
JSON_HEADERS = {**AUTH_HEADERS, "Content-Type": "application/json"}

SAMPLE_CONTAINER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    async def fake_session():
        yield None

    async def fake_list_response(session, request):
        return ListContainersResponse(
            request_id="test-list",
            containers=[
                ContainerSummary(
                    id=SAMPLE_CONTAINER_ID,
                    name="expressionist-art",
                    theme="art",
                    modalities=["text"],
                    state="active",
                    stats=ContainerStats(),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ],
            total=1,
            timings_ms={"db_query": 1},
        )

    async def fake_describe_response(session, request):
        if request.container not in {SAMPLE_CONTAINER_ID, "expressionist-art"}:
            raise ValueError("CONTAINER_NOT_FOUND")
        return DescribeContainerResponse(
            request_id="test-describe",
            container=ContainerDetail(
                id=SAMPLE_CONTAINER_ID,
                name="expressionist-art",
                theme="art",
                modalities=["text"],
                state="active",
                stats=ContainerStats(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                description="Sample container",
                embedder="nomic",
                embedder_version="1.0",
                dims=1408,
                policy={},
            ),
            timings_ms={"db_query": 1},
        )

    async def fake_enqueue_jobs(session, request):
        job_id = str(uuid4())
        return ContainersAddResponse(
            request_id="test-add",
            jobs=[
                JobSummary(
                    job_id=job_id,
                    status="queued",
                    source_uri=request.sources[0].uri if request.sources else "https://example.com",
                    submitted_at=datetime.now(timezone.utc),
                )
            ],
        )

    async def fake_search_response(session, request):
        issues = []
        diagnostics = {"mode": request.mode, "bm25_hits": 1, "vector_hits": 1}
        if any(cid not in {SAMPLE_CONTAINER_ID, "expressionist-art"} for cid in request.container_ids):
            issues.append("CONTAINER_NOT_FOUND")
            diagnostics["bm25_hits"] = 0
            diagnostics["vector_hits"] = 0
        return SearchResponse(
            request_id="test-search",
            query=request.query,
            results=[
                SearchResult(
                    chunk_id=str(uuid4()),
                    doc_id=str(uuid4()),
                    container_id=SAMPLE_CONTAINER_ID,
                    container_name="expressionist-art",
                    title="Doc",
                    snippet="Snippet",
                    uri="https://example.com",
                    score=0.5,
                    modality="text",
                    provenance={},
                    meta={},
                )
            ],
            total_hits=1,
            returned=1,
            timings_ms={"bm25_ms": 1, "vector_ms": 2, "total_ms": 3},
            diagnostics=diagnostics,
            issues=issues,
        )

    app.dependency_overrides[get_session] = fake_session
    monkeypatch.setattr(container_service, "list_containers_response", fake_list_response)
    monkeypatch.setattr(container_service, "describe_container_response", fake_describe_response)
    monkeypatch.setattr(job_service, "enqueue_jobs", fake_enqueue_jobs)
    monkeypatch.setattr(search_service, "search_response", fake_search_response)
    yield
    app.dependency_overrides.clear()


class TestListContainersContract:
    """Contract tests for containers.list endpoint."""

    def test_list_containers_request_schema(self):
        """Validate ListContainersRequest schema."""
        # Valid request
        req = ListContainersRequest(state="active", limit=25, offset=0)
        assert req.state == "active"
        assert req.limit == 25
        assert req.offset == 0

        # Default values
        req_default = ListContainersRequest()
        assert req_default.state == "active"
        assert req_default.limit == 25
        assert req_default.offset == 0

    def test_list_containers_request_validation(self):
        """Test request validation rules."""
        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            ListContainersRequest(limit=101)

        # Invalid limit (too low)
        with pytest.raises(ValidationError):
            ListContainersRequest(limit=0)

        # Invalid offset (negative)
        with pytest.raises(ValidationError):
            ListContainersRequest(offset=-1)

    def test_list_containers_response_schema(self):
        """Validate ListContainersResponse schema."""
        response = ListContainersResponse(
            request_id="test-123",
            containers=[],
            total=0,
            timings_ms={"db_query": 10},
        )
        assert response.version == "v1"
        assert response.request_id == "test-123"
        assert response.containers == []
        assert response.total == 0
        assert response.timings_ms["db_query"] == 10
        assert response.issues == []

    def test_list_containers_endpoint_format(self):
        """Test endpoint response format."""
        response = client.post("/v1/containers/list", json={}, headers=AUTH_HEADERS)
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] == "v1"
        assert "request_id" in data
        assert isinstance(data["containers"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["timings_ms"], dict)
        assert isinstance(data["issues"], list)


class TestDescribeContainerContract:
    """Contract tests for containers.describe endpoint."""

    def test_describe_container_request_schema(self):
        """Validate DescribeContainerRequest schema."""
        req = DescribeContainerRequest(container="test-container")
        assert req.container == "test-container"

        # Should accept UUID or slug
        req_uuid = DescribeContainerRequest(container="123e4567-e89b-12d3-a456-426614174000")
        assert req_uuid.container == "123e4567-e89b-12d3-a456-426614174000"

    def test_describe_container_response_schema(self):
        """Validate DescribeContainerResponse schema."""
        from datetime import datetime
        
        response = DescribeContainerResponse(
            request_id="test-123",
            container={
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "test-container",
                "theme": "Test Theme",
                "modalities": ["text"],
                "state": "active",
                "stats": {"document_count": 0, "chunk_count": 0, "size_mb": 0.0},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "description": "Test description",
                "embedder": "nomic-embed-text-v1",
                "embedder_version": "1.0.0",
                "dims": 768,
                "policy": {},
            },
        )
        assert response.version == "v1"
        assert response.container.name == "test-container"
        assert response.container.dims == 768

    def test_describe_container_error_response(self):
        """Test error response format for non-existent container."""
        response = client.post(
            "/v1/containers/describe", 
            json={"container": "non-existent-container"},
            headers=AUTH_HEADERS,
        )
        # Should return 404 with proper error structure
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data


class TestContainersAddContract:
    """Contract tests for containers.add endpoint."""

    def test_add_source_schema(self):
        """Validate AddSource schema."""
        source = AddSource(uri="https://example.com/doc.pdf")
        assert source.uri == "https://example.com/doc.pdf"
        assert source.title is None
        assert source.mime is None
        assert source.meta == {}

        # With optional fields
        source_full = AddSource(
            uri="https://example.com/doc.pdf",
            title="Test Document",
            mime="application/pdf",
            meta={"author": "Test"},
        )
        assert source_full.title == "Test Document"
        assert source_full.mime == "application/pdf"

    def test_containers_add_request_schema(self):
        """Validate ContainersAddRequest schema."""
        req = ContainersAddRequest(
            container="test-container",
            sources=[AddSource(uri="https://example.com/doc.pdf")],
        )
        assert req.container == "test-container"
        assert len(req.sources) == 1
        assert req.sources[0].uri == "https://example.com/doc.pdf"

    def test_containers_add_request_validation(self):
        """Test request validation."""
        # Missing required container
        with pytest.raises(ValidationError):
            ContainersAddRequest(sources=[])

        # Missing required sources
        with pytest.raises(ValidationError):
            ContainersAddRequest(container="test")

        # Empty sources list should be valid (but may return error from service)
        req = ContainersAddRequest(container="test", sources=[])
        assert req.sources == []

    def test_containers_add_response_schema(self):
        """Validate ContainersAddResponse schema."""
        from datetime import datetime
        
        response = ContainersAddResponse(
            request_id="test-123",
            jobs=[
                {
                    "job_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "queued",
                    "source_uri": "https://example.com/doc.pdf",
                    "submitted_at": datetime.utcnow(),
                }
            ],
        )
        assert response.version == "v1"
        assert len(response.jobs) == 1
        assert response.jobs[0].status == "queued"

    def test_containers_add_endpoint_format(self):
        """Test endpoint response format."""
        response = client.post(
            "/v1/containers/add",
            json={
                "container": "test-container",
                "sources": [{"uri": "https://example.com/doc.pdf"}],
            },
            headers=AUTH_HEADERS,
        )
        # May return 404 if container doesn't exist, but format should be valid
        data = response.json()
        assert "version" in data or "detail" in data


class TestSearchContract:
    """Contract tests for containers.search endpoint."""

    def test_search_request_schema(self):
        """Validate SearchRequest schema."""
        req = SearchRequest(
            query="test query",
            container_ids=["container-1"],
            mode="hybrid",
            k=10,
        )
        assert req.query == "test query"
        assert req.container_ids == ["container-1"]
        assert req.mode == "hybrid"
        assert req.k == 10

    def test_search_request_validation(self):
        """Test search request validation."""
        # Valid modes
        for mode in ["semantic", "bm25", "hybrid"]:
            req = SearchRequest(query="test", container_ids=["c1"], mode=mode)
            assert req.mode == mode

        # Invalid mode
        with pytest.raises(ValidationError):
            SearchRequest(query="test", container_ids=["c1"], mode="invalid")

        # k out of range
        with pytest.raises(ValidationError):
            SearchRequest(query="test", container_ids=["c1"], k=0)

        with pytest.raises(ValidationError):
            SearchRequest(query="test", container_ids=["c1"], k=101)

        # Missing required container_ids
        with pytest.raises(ValidationError):
            SearchRequest(query="test")

    def test_search_response_schema(self):
        """Validate SearchResponse schema."""
        response = SearchResponse(
            request_id="test-123",
            query="test query",
            results=[],
            total_hits=0,
            returned=0,
            timings_ms={"total": 100},
        )
        assert response.version == "v1"
        assert response.query == "test query"
        assert response.results == []
        assert response.total_hits == 0

    def test_search_response_with_results(self):
        """Test response with sample results."""
        from datetime import datetime
        
        response = SearchResponse(
            request_id="test-123",
            query="test query",
            results=[
                {
                    "chunk_id": "123e4567-e89b-12d3-a456-426614174000",
                    "doc_id": "123e4567-e89b-12d3-a456-426614174001",
                    "container_id": "container-1",
                    "container_name": "Test Container",
                    "title": "Test Document",
                    "snippet": "Test snippet...",
                    "uri": "https://example.com/doc.pdf",
                    "score": 0.85,
                    "modality": "text",
                    "provenance": {"source": "url"},
                    "meta": {},
                }
            ],
            total_hits=1,
            returned=1,
            timings_ms={"embed": 50, "vector": 30, "bm25": 20, "total": 100},
            diagnostics={"mode": "hybrid", "bm25_hits": 1, "vector_hits": 1},
        )
        assert len(response.results) == 1
        assert response.results[0].score == 0.85
        assert response.results[0].title == "Test Document"

    def test_search_endpoint_format(self):
        """Test search endpoint response format."""
        response = client.post(
            "/v1/search",
            json={
                "query": "test query",
                "container_ids": ["test-container"],
                "mode": "bm25",
                "k": 5,
            },
            headers=AUTH_HEADERS,
        )
        assert response.status_code in [200, 404]  # 404 if container doesn't exist
        
        if response.status_code == 200:
            data = response.json()
            assert data["version"] == "v1"
            assert "request_id" in data
            assert "query" in data
            assert isinstance(data["results"], list)
            assert isinstance(data["timings_ms"], dict)
            assert isinstance(data["issues"], list)


class TestDocumentsContract:
    """Contract tests for documents APIs."""

    def test_list_documents_request_schema(self):
        req = ListDocumentsRequest(container="expressionist-art")
        assert req.limit == 25
        assert req.offset == 0
        assert req.container == "expressionist-art"

        req_with_filters = ListDocumentsRequest(
            container="expressionist-art", limit=50, offset=5, search="notes"
        )
        assert req_with_filters.limit == 50
        assert req_with_filters.search == "notes"

        with pytest.raises(ValidationError):
            ListDocumentsRequest(container="c", limit=0)

        with pytest.raises(ValidationError):
            ListDocumentsRequest(container="c", limit=500)

    def test_list_documents_response_schema(self):
        response = ListDocumentsResponse(
            request_id="req-1",
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
            timings_ms={"db_query": 5},
        )
        assert response.documents[0].chunk_count == 3
        assert response.total == 1

    def test_delete_document_request_schema(self):
        req = DeleteDocumentRequest(container="expressionist-art", document_id="doc-1")
        assert req.document_id == "doc-1"

    def test_delete_document_response_schema(self):
        response = DeleteDocumentResponse(
            request_id="req-2",
            document_id="doc-1",
            timings_ms={"db_query": 2},
        )
        assert response.deleted is True
        assert response.document_id == "doc-1"


class TestErrorResponseContract:
    """Contract tests for error response formats."""

    def test_error_response_structure(self):
        """Test that errors follow consistent structure."""
        # Test various error conditions
        test_cases = [
            # Invalid JSON
            ("/v1/containers/list", "invalid json"),
            # Missing required fields
            ("/v1/search", {"container_ids": []}),  # Missing query
            # Invalid enum values
            ("/v1/search", {"query": "test", "container_ids": ["c1"], "mode": "invalid"}),
        ]
        
        for endpoint, payload in test_cases:
            if isinstance(payload, str):
                response = client.post(endpoint, data=payload, headers=JSON_HEADERS)
            else:
                response = client.post(endpoint, json=payload, headers=AUTH_HEADERS)
            
            # Should return 4xx error
            assert response.status_code >= 400
            
            data = response.json()
            # Error responses should have detail field
            assert "detail" in data

    def test_issue_codes_format(self):
        """Test that issue codes follow expected format."""
        # Make a request that might generate issues
        response = client.post(
            "/v1/search",
            json={
                "query": "test",
                "container_ids": ["non-existent-container"],
                "mode": "bm25",
                "k": 10,
            },
            headers=AUTH_HEADERS,
        )
        
        if response.status_code == 200:
            data = response.json()
            # Issues should be a list of strings
            assert isinstance(data.get("issues", []), list)
            for issue in data.get("issues", []):
                assert isinstance(issue, str)
                # Issue codes should be uppercase with underscores
                assert issue.isupper() or "_" in issue


class TestTimingsContract:
    """Contract tests for timing fields."""

    def test_timings_ms_format(self):
        """Test that timings_ms follows expected format."""
        response = client.post("/v1/containers/list", json={}, headers=AUTH_HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            timings = data.get("timings_ms", {})
            
            # timings_ms should be a dict of string -> int
            assert isinstance(timings, dict)
            for key, value in timings.items():
                assert isinstance(key, str)
                assert isinstance(value, (int, float))
                assert value >= 0  # Timings should be non-negative

    def test_diagnostics_format(self):
        """Test that diagnostics follows expected format."""
        response = client.post(
            "/v1/search",
            json={
                "query": "test",
                "container_ids": ["test-container"],
                "mode": "bm25",
                "k": 5,
            },
            headers=AUTH_HEADERS,
        )
        
        if response.status_code == 200:
            data = response.json()
            diagnostics = data.get("diagnostics", {})
            
            # diagnostics should be a dict
            assert isinstance(diagnostics, dict)
            
            # Should contain expected fields for search
            if "mode" in diagnostics:
                assert diagnostics["mode"] in ["semantic", "bm25", "hybrid"]
            
            # Hit counts should be integers
            for key in ["bm25_hits", "vector_hits"]:
                if key in diagnostics:
                    assert isinstance(diagnostics[key], int)
                    assert diagnostics[key] >= 0
