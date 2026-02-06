"""FastAPI entrypoint for the MCP server.

This placeholder wires up the health endpoint so compose stacks can smoke-test connectivity
while the full MCP tool surface is implemented.
"""
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging
import os

from sqlalchemy import text

from app.adapters.minio import minio_adapter
from app.adapters.neo4j import neo4j_adapter
from app.adapters.qdrant import qdrant_adapter
from .api.routes import register_routes
from .db.session import get_session, AsyncSessionLocal

logger = logging.getLogger(__name__)

app = FastAPI(title="Local Latent Containers MCP", version="0.1.0")


def _cors_origins() -> list[str]:
    """Compute allowed CORS origins from env or sensible local defaults."""
    raw = os.getenv("MCP_CORS_ORIGINS")
    if raw:
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        if origins:
            return origins
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=".*",  # fallback to wildcard for any dev host
    allow_credentials=False,  # We use bearer tokens; no cookies required
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track agent activity from request headers."""

    async def dispatch(self, request: Request, call_next):
        # Extract agent info from headers
        agent_id = request.headers.get("X-Agent-ID")
        agent_name = request.headers.get("X-Agent-Name")

        # Track agent activity if headers present
        if agent_id and agent_id != "anonymous":
            try:
                from .services.agent_tracking import track_agent_activity
                
                # Get database session
                async for session in get_session():
                    try:
                        await track_agent_activity(session, agent_id, agent_name)
                    except Exception as e:
                        logger.warning(f"Failed to track agent activity: {e}")
                    break  # Only need one iteration
            except Exception as e:
                logger.warning(f"Agent tracking middleware error: {e}")

        # Continue processing request
        response = await call_next(request)
        return response


# Add agent tracking middleware
app.add_middleware(AgentTrackingMiddleware)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def readiness(response: Response) -> dict[str, object]:
    checks: dict[str, bool] = {}
    errors: dict[str, str] = {}

    async def check_db() -> bool:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True

    def check_qdrant() -> bool:
        qdrant_adapter.client.get_collections()
        return True

    def check_minio() -> bool:
        minio_adapter.client.bucket_exists(minio_adapter.bucket)
        return True

    def check_neo4j() -> bool:
        return neo4j_adapter.healthcheck()

    async def run(name: str, task: asyncio.Future) -> None:
        try:
            ok = await task
            checks[name] = bool(ok)
            if not ok:
                errors[name] = "unhealthy"
        except Exception as exc:
            checks[name] = False
            errors[name] = str(exc)

    await asyncio.gather(
        run("postgres", check_db()),
        run("qdrant", asyncio.to_thread(check_qdrant)),
        run("minio", asyncio.to_thread(check_minio)),
        run("neo4j", asyncio.to_thread(check_neo4j)),
    )

    all_ok = all(checks.values()) if checks else True
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    payload: dict[str, object] = {"status": "ok" if all_ok else "degraded", "checks": checks}
    if errors:
        payload["errors"] = errors
    return payload


register_routes(app)
