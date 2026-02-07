"""FastAPI entrypoint for the MCP server.

This placeholder wires up the health endpoint so compose stacks can smoke-test connectivity
while the full MCP tool surface is implemented.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging
import os
import time

from app.core.config import get_settings
from app.core.runtime_state import set_migration_report
from app.migrations.runner import run_best_effort_migrations
from app.services.health import gather_checks
from .api.routes import register_routes
from .db.session import get_session

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler (startup/shutdown).

    Runs database migrations at startup when enabled.
    """
    if settings.auto_migrate:
        logger.info("migrations_start", extra={"auto_migrate": True})
        report = await run_best_effort_migrations()
        # Store for /ready and /v1/system/status
        app.state.migration_report = report
        set_migration_report(report)

        if not report.required_ok:
            logger.error("migrations_failed", extra={"report": report.to_dict()})
            # If Postgres failed, refuse to start.
            raise RuntimeError("postgres_migrations_failed")

        if not report.ok:
            logger.warning("migrations_degraded", extra={"report": report.to_dict()})
        else:
            logger.info("migrations_ok", extra={"report": report.to_dict()})

    yield


app = FastAPI(title="Local Latent Containers MCP", version="0.1.0", lifespan=lifespan)


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

    def __init__(self, app, min_interval_s: float = 30.0):
        super().__init__(app)
        self._min_interval_s = float(min_interval_s)
        self._last_seen: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        # Extract agent info from headers
        agent_id = request.headers.get("X-Agent-ID")
        agent_name = request.headers.get("X-Agent-Name")

        # Track agent activity if headers present
        if agent_id and agent_id != "anonymous" and request.url.path not in {"/health", "/ready", "/metrics", "/v1/system/status"}:
            try:
                # Throttle DB writes: we only update last_active every N seconds per agent.
                now = time.monotonic()
                should_track = True
                async with self._lock:
                    last = self._last_seen.get(agent_id)
                    if last is not None and (now - last) < self._min_interval_s:
                        should_track = False
                    else:
                        self._last_seen[agent_id] = now

                if should_track:
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
app.add_middleware(AgentTrackingMiddleware, min_interval_s=settings.agent_tracking_min_interval_seconds)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def readiness(response: Response) -> dict[str, object]:
    checks, errors = await gather_checks()

    all_ok = all(checks.values()) if checks else True
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    payload: dict[str, object] = {"status": "ok" if all_ok else "degraded", "checks": checks}
    if errors:
        payload["errors"] = errors
    migration_report = getattr(app.state, "migration_report", None)
    if migration_report:
        payload["migrations"] = migration_report.to_dict()
    return payload


register_routes(app)
