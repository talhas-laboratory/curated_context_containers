"""FastAPI entrypoint for the MCP server.

This placeholder wires up the health endpoint so compose stacks can smoke-test connectivity
while the full MCP tool surface is implemented.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

from .api.routes import register_routes
from .db.session import get_session

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


register_routes(app)
