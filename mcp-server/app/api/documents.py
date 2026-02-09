"""Document management endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import verify_bearer_token
from app.core.config import get_settings
from app.db.session import get_session
from app.models.documents import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    FetchDocumentRequest,
    FetchDocumentResponse,
    ListDocumentsRequest,
    ListDocumentsResponse,
)
from app.services import documents as document_service

router = APIRouter(prefix="/v1/documents", tags=["documents"])
settings = get_settings()


@router.post("/list", response_model=ListDocumentsResponse)
async def list_documents(
    payload: ListDocumentsRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> ListDocumentsResponse:
    try:
        return await document_service.list_documents_response(session, payload)
    except ValueError as exc:
        if str(exc) == "CONTAINER_NOT_FOUND":
            raise HTTPException(status_code=404, detail="CONTAINER_NOT_FOUND") from exc
        raise


@router.post("/delete", response_model=DeleteDocumentResponse)
async def delete_document(
    payload: DeleteDocumentRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> DeleteDocumentResponse:
    try:
        return await document_service.delete_document_response(session, payload)
    except ValueError as exc:
        message = str(exc)
        if message in {"CONTAINER_NOT_FOUND", "DOCUMENT_NOT_FOUND"}:
            raise HTTPException(status_code=404, detail=message) from exc
        if message == "INVALID_DOCUMENT_ID":
            raise HTTPException(status_code=400, detail=message) from exc
        raise


@router.post("/fetch", response_model=FetchDocumentResponse)
async def fetch_document(
    payload: FetchDocumentRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> FetchDocumentResponse:
    """Fetch full document content from storage.
    
    This endpoint is only available when LLC_ENABLE_DOCUMENT_FETCH=true.
    """
    if not settings.enable_document_fetch:
        raise HTTPException(
            status_code=404,
            detail="Document fetch feature is disabled. Set LLC_ENABLE_DOCUMENT_FETCH=true to enable."
        )
    
    try:
        return await document_service.fetch_document_content(session, payload)
    except ValueError as exc:
        message = str(exc)
        if message in {"CONTAINER_NOT_FOUND", "DOCUMENT_NOT_FOUND", "DOCUMENT_CONTENT_NOT_FOUND"}:
            raise HTTPException(status_code=404, detail=message) from exc
        if message in {"INVALID_DOCUMENT_ID", "DOCUMENT_FETCH_FAILED"}:
            raise HTTPException(status_code=400, detail=message) from exc
        raise






















