"""Bearer-token authentication helpers for MCP endpoints."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

security = HTTPBearer(auto_error=False)


@lru_cache
def _load_expected_token() -> str:
    """Load the expected MCP bearer token from env or disk."""
    settings = get_settings()
    if settings.mcp_token:
        return settings.mcp_token.strip()

    token_path = Path(settings.mcp_token_path)
    if not token_path.exists():
        raise RuntimeError(
            f"MCP token file not found at {token_path}. "
            "Configure LLC_MCP_TOKEN or place the token file before starting the server."
        )
    token = token_path.read_text().strip()
    if not token:
        raise RuntimeError(f"MCP token file at {token_path} is empty.")
    return token


def verify_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> bool:
    """Validate Authorization header against the configured token."""
    if credentials is None or not credentials.scheme:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected = _load_expected_token()
    if credentials.scheme.lower() != "bearer" or credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
