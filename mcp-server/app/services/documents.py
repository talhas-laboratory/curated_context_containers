"""Document listing and deletion helpers."""
from __future__ import annotations

import logging
from datetime import datetime
from time import perf_counter
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.minio import minio_adapter
from app.adapters.qdrant import qdrant_adapter
from app.db.models import Chunk, Container, Document
from app.models.documents import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    DocumentItem,
    ListDocumentsRequest,
    ListDocumentsResponse,
)

LOGGER = logging.getLogger(__name__)


def _maybe_uuid(value: str | None) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


async def _resolve_container(session: AsyncSession, identifier: str) -> Container:
    stmt = select(Container).where(
        or_(
            Container.name == identifier,
            *((Container.id == _maybe_uuid(identifier),) if _maybe_uuid(identifier) else ()),
        )
    )
    container = (await session.execute(stmt)).scalar_one_or_none()
    if not container:
        raise ValueError("CONTAINER_NOT_FOUND")
    return container


async def _refresh_container_stats(
    session: AsyncSession,
    container: Container,
    *,
    last_ingest: Optional[datetime] = None,
) -> None:
    """Recompute document + chunk counts for a container."""
    doc_count_stmt = select(func.count()).select_from(Document).where(Document.container_id == container.id)
    chunk_count_stmt = select(func.count()).select_from(Chunk).where(Chunk.container_id == container.id)
    doc_count = (await session.execute(doc_count_stmt)).scalar_one()
    total_chunks = (await session.execute(chunk_count_stmt)).scalar_one()

    stats = dict(container.stats or {})
    stats["document_count"] = int(doc_count)
    stats["chunk_count"] = int(total_chunks)
    if last_ingest is not None:
        stats["last_ingest"] = last_ingest

    await session.execute(
        update(Container)
        .where(Container.id == container.id)
        .values(stats=stats, updated_at=func.now())
    )
    container.stats = stats


async def list_documents_response(
    session: AsyncSession, request: ListDocumentsRequest
) -> ListDocumentsResponse:
    start = perf_counter()
    container = await _resolve_container(session, request.container)
    filters = [Document.container_id == container.id]
    if request.search:
        term = f"%{request.search.lower()}%"
        filters.append(
            or_(
                func.lower(func.coalesce(Document.title, "")).like(term),
                func.lower(func.coalesce(Document.uri, "")).like(term),
            )
        )

    stmt = (
        select(
            Document,
            func.coalesce(func.count(Chunk.id), 0).label("chunk_count"),
        )
        .outerjoin(Chunk, Chunk.doc_id == Document.id)
        .where(*filters)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
        .limit(request.limit)
        .offset(request.offset)
    )
    total_stmt = select(func.count()).select_from(Document).where(*filters)

    rows = (await session.execute(stmt)).all()
    total = (await session.execute(total_stmt)).scalar_one()
    documents: List[DocumentItem] = []
    for document, chunk_count in rows:
        documents.append(
            DocumentItem(
                id=str(document.id),
                uri=document.uri,
                title=document.title,
                mime=document.mime,
                hash=document.hash,
                state=document.state,
                chunk_count=int(chunk_count or 0),
                meta=document.meta or {},
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
        )

    elapsed = int((perf_counter() - start) * 1000)
    return ListDocumentsResponse(
        request_id=str(uuid4()),
        container_id=str(container.id),
        documents=documents,
        total=total,
        timings_ms={"db_query": elapsed},
    )


async def delete_document_response(
    session: AsyncSession, request: DeleteDocumentRequest
) -> DeleteDocumentResponse:
    start = perf_counter()
    container = await _resolve_container(session, request.container)
    document_id = _maybe_uuid(request.document_id)
    if not document_id:
        raise ValueError("INVALID_DOCUMENT_ID")

    doc_stmt = select(Document).where(
        Document.id == document_id, Document.container_id == container.id
    )
    document = (await session.execute(doc_stmt)).scalar_one_or_none()
    if not document:
        raise ValueError("DOCUMENT_NOT_FOUND")

    await session.execute(delete(Chunk).where(Chunk.doc_id == document.id))
    await session.delete(document)

    await _refresh_container_stats(session, container)
    await session.commit()

    async def _cleanup():
        try:
            await qdrant_adapter.delete_document(str(container.id), str(document.id))
        except Exception as exc:  # pragma: no cover - runtime safeguard
            LOGGER.warning(
                "qdrant_cleanup_failed",
                extra={"container_id": str(container.id), "document_id": str(document.id), "error": str(exc)},
            )

        try:
            await minio_adapter.delete_document(str(container.id), str(document.id))
        except Exception as exc:  # pragma: no cover - runtime safeguard
            LOGGER.warning(
                "minio_cleanup_failed",
                extra={"container_id": str(container.id), "document_id": str(document.id), "error": str(exc)},
            )

    await _cleanup()

    elapsed = int((perf_counter() - start) * 1000)
    return DeleteDocumentResponse(
        request_id=str(uuid4()),
        document_id=str(document.id),
        timings_ms={"db_query": elapsed},
    )


async def fetch_document_content(
    session: AsyncSession, request
) -> object:
    """Fetch full document content from MinIO storage.
    
    Returns FetchDocumentResponse with base64-encoded content.
    """
    import base64
    from app.models.documents import FetchDocumentResponse
    
    start = perf_counter()
    container = await _resolve_container(session, request.container)
    document_id = _maybe_uuid(request.document_id)
    if not document_id:
        raise ValueError("INVALID_DOCUMENT_ID")

    doc_stmt = select(Document).where(
        Document.id == document_id, Document.container_id == container.id
    )
    document = (await session.execute(doc_stmt)).scalar_one_or_none()
    if not document:
        raise ValueError("DOCUMENT_NOT_FOUND")

    # Fetch from MinIO
    try:
        content_bytes, mime_type, filename = await minio_adapter.get_document_content(
            str(container.id), str(document.id)
        )
    except FileNotFoundError as exc:
        raise ValueError("DOCUMENT_CONTENT_NOT_FOUND") from exc
    except Exception as exc:
        LOGGER.error(
            "minio_fetch_failed",
            extra={"container_id": str(container.id), "document_id": str(document.id), "error": str(exc)},
        )
        raise ValueError("DOCUMENT_FETCH_FAILED") from exc

    # Encode to base64 for JSON transport
    content_base64 = base64.b64encode(content_bytes).decode("utf-8")
    
    elapsed = int((perf_counter() - start) * 1000)
    return FetchDocumentResponse(
        request_id=str(uuid4()),
        document_id=str(document.id),
        container_id=str(container.id),
        content_base64=content_base64,
        mime_type=mime_type,
        filename=filename,
        size_bytes=len(content_bytes),
        timings_ms={"total_ms": elapsed},
    )
