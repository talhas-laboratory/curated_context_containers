"""Admin endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.models.admin import RefreshRequest, RefreshResponse, ExportRequest, ExportResponse
from app.services import admin as admin_service
from app.services.jobs import ContainerNotFoundError
from app.core.security import verify_bearer_token

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> RefreshResponse:
    try:
        return await admin_service.enqueue_refresh(session, payload)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/export", response_model=ExportResponse)
async def export(
    payload: ExportRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> ExportResponse:
    try:
        return await admin_service.enqueue_export(session, payload)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
