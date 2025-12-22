"""Router registration utilities."""
from fastapi import APIRouter, FastAPI

from . import collaboration, containers, documents, jobs, search, admin
from app.core.metrics import metrics_router

router = APIRouter(prefix="/v1", tags=["mcp"])


@router.get("/status")
async def api_status() -> dict[str, str]:
    return {"message": "MCP server scaffolding ready"}


def register_routes(app: FastAPI) -> None:
    app.include_router(router)
    app.include_router(containers.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(jobs.router)
    app.include_router(collaboration.router)
    app.include_router(admin.router)
    app.include_router(metrics_router)
