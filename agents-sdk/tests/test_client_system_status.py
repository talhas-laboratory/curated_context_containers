import httpx
import pytest

from llc_agents import AgentSession, ContainerClient


def _mock_transport():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/system/status":
            return httpx.Response(
                200,
                json={
                    "version": "v1",
                    "request_id": "req-system",
                    "status": "degraded",
                    "required_ok": True,
                    "checks": {"postgres": True, "qdrant": False, "minio": True, "neo4j": True},
                    "errors": {"qdrant": "connection refused"},
                    "migrations": None,
                    "issues": ["QDRANT_DOWN"],
                },
            )
        raise AssertionError(f"Unhandled path: {request.url.path}")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_system_status_roundtrip():
    transport = _mock_transport()
    session = AgentSession(agent_id="test-agent", base_url="http://test", token="t")
    session.client = httpx.AsyncClient(transport=transport, base_url="http://test")
    async with session:
        client = ContainerClient(session)
        status = await client.system_status()
        assert status.status == "degraded"
        assert status.checks["qdrant"] is False
        assert status.errors and "qdrant" in status.errors

