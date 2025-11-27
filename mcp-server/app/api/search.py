"""Search endpoints."""
from fastapi import APIRouter, Depends

from app.db.session import get_session
from app.models.search import SearchRequest, SearchResponse
from app.services import search as search_service
from app.core.security import verify_bearer_token

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    session=Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
) -> SearchResponse:
    return await search_service.search_response(session, payload)
