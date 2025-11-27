"""Agent session management."""

import os
from typing import Optional
from uuid import uuid4

import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class SessionConfig(BaseSettings):
    """Configuration for agent sessions."""

    base_url: str = "http://localhost:7801"
    token: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3

    class Config:
        env_prefix = "LLC_"


class AgentSession:
    """Manages authentication and HTTP session for an agent.

    Handles:
    - Bearer token authentication
    - Request ID tracking
    - Agent identity headers
    - HTTP client lifecycle

    Example:
        session = AgentSession(
            agent_id="research-bot-001",
            agent_name="Research Bot",
            base_url="http://localhost:7801",
            token="your-token"
        )

        async with session:
            response = await session.post("/v1/search", {...})
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: Optional[str] = None,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize agent session.

        Args:
            agent_id: Unique agent identifier (will be tracked in logs/metrics)
            agent_name: Human-readable agent name
            base_url: LLC API base URL (default: http://localhost:7801)
            token: Bearer token for authentication (can also use LLC_TOKEN env var)
            timeout: Request timeout in seconds
        """
        self.agent_id = agent_id
        self.agent_name = agent_name or agent_id

        # Use provided values or fall back to environment/defaults
        config = SessionConfig(
            base_url=base_url or os.getenv("LLC_BASE_URL", "http://localhost:7801"),
            token=token or os.getenv("LLC_TOKEN"),
            timeout=timeout,
        )

        self.base_url = config.base_url.rstrip("/")
        self.token = config.token
        self.timeout = config.timeout

        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._default_headers(),
        )

    def _default_headers(self) -> dict[str, str]:
        """Build default headers for all requests."""
        headers = {
            "Content-Type": "application/json",
            "X-Agent-ID": self.agent_id,
            "X-Agent-Name": self.agent_name,
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup client."""
        await self.close()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        request_id: Optional[str] = None,
    ) -> httpx.Response:
        """Make HTTP request to LLC API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/v1/search")
            json: JSON body for POST/PATCH requests
            params: Query parameters
            headers: Additional headers (merged with defaults)
            request_id: Optional request ID for tracing

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        url = f"{self.base_url}{path}"

        # Merge headers
        req_headers = self._default_headers()
        if headers:
            req_headers.update(headers)

        # Add request ID if provided
        if request_id:
            req_headers["X-Request-ID"] = request_id
        else:
            req_headers["X-Request-ID"] = str(uuid4())

        response = await self.client.request(
            method=method,
            url=url,
            json=json,
            params=params,
            headers=req_headers,
        )

        # Raise for 4xx/5xx
        response.raise_for_status()

        return response

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, json: Optional[dict] = None, **kwargs) -> httpx.Response:
        """POST request."""
        return await self.request("POST", path, json=json, **kwargs)

    async def patch(self, path: str, json: Optional[dict] = None, **kwargs) -> httpx.Response:
        """PATCH request."""
        return await self.request("PATCH", path, json=json, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE request."""
        return await self.request("DELETE", path, **kwargs)

