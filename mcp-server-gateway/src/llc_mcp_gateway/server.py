"""MCP Server Gateway for Local Latent Containers.

This server exposes the LLC FastAPI backend as MCP tools that can be
consumed by AI agents (Claude Desktop, Cursor, etc.).
"""

import asyncio
import os
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource


class LLCMCPGateway:
    """Gateway that bridges MCP protocol to LLC FastAPI backend."""

    def __init__(
        self,
        base_url: str = "http://localhost:7801",
        token: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("LLC_MCP_TOKEN", "")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.server = Server("llc-mcp-gateway")

        # Register tool handlers
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="containers_list",
                    description=(
                        "List available context containers with optional filtering. "
                        "Returns container metadata including name, theme, modalities, and stats. "
                        "Use this to discover what containers exist before searching."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "enum": ["active", "paused", "archived", "all"],
                                "default": "active",
                                "description": "Filter by container state",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 25,
                                "minimum": 1,
                                "maximum": 100,
                                "description": "Number of containers to return",
                            },
                            "offset": {
                                "type": "integer",
                                "default": 0,
                                "minimum": 0,
                                "description": "Pagination offset",
                            },
                            "search": {
                                "type": "string",
                                "description": "Optional substring to filter container names",
                            },
                            "include_stats": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include document/chunk counts and size",
                            },
                        },
                    },
                ),
                Tool(
                    name="containers_describe",
                    description=(
                        "Get detailed metadata for a specific container including manifest, "
                        "policy, embedder configuration, and comprehensive statistics. "
                        "Use this after discovering a container to understand its scope and capabilities."
                    ),
                    inputSchema={
                        "type": "object",
                        "required": ["container"],
                        "properties": {
                            "container": {
                                "type": "string",
                                "description": "Container UUID or slug name",
                            },
                        },
                    },
                ),
                Tool(
                    name="containers_search",
                    description=(
                        "Execute semantic or hybrid search across one or more containers. "
                        "Returns ranked results with snippets, scores, and provenance. "
                        "Supports multiple search modes (semantic, hybrid, bm25), optional reranking, "
                        "and metadata filtering. Use this as the primary information retrieval tool."
                    ),
                    inputSchema={
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query text",
                            },
                            "container_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of container IDs/slugs to search (searches all if omitted)",
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["semantic", "hybrid", "bm25"],
                                "default": "hybrid",
                                "description": "Search mode (hybrid recommended for best results)",
                            },
                            "rerank": {
                                "type": "boolean",
                                "default": False,
                                "description": "Apply reranking for improved relevance (adds latency)",
                            },
                            "k": {
                                "type": "integer",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                                "description": "Number of results to return",
                            },
                            "diagnostics": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include timing and scoring diagnostics",
                            },
                            "filters": {
                                "type": "object",
                                "description": "Optional filters (modality, metadata)",
                                "properties": {
                                    "modality": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Filter by modality (text, image, pdf)",
                                    },
                                    "metadata": {
                                        "type": "object",
                                        "description": "Filter by metadata key-value pairs",
                                    },
                                },
                            },
                        },
                    },
                ),
                Tool(
                    name="containers_add",
                    description=(
                        "Submit ingestion jobs to add new sources to a container. "
                        "Sources can be URLs (https://, file://), uploaded content, or references. "
                        "Returns job IDs that can be polled for status. "
                        "Use this to dynamically expand a container's knowledge base."
                    ),
                    inputSchema={
                        "type": "object",
                        "required": ["container", "sources"],
                        "properties": {
                            "container": {
                                "type": "string",
                                "description": "Container UUID or slug",
                            },
                            "sources": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["uri"],
                                    "properties": {
                                        "uri": {
                                            "type": "string",
                                            "description": "Source URI (https://, file://)",
                                        },
                                        "title": {
                                            "type": "string",
                                            "description": "Optional title override",
                                        },
                                        "mime": {
                                            "type": "string",
                                            "description": "MIME type (auto-detected if omitted)",
                                        },
                                        "modality": {
                                            "type": "string",
                                            "description": "Modality (text, pdf, image, web)",
                                        },
                                        "meta": {
                                            "type": "object",
                                            "description": "Optional metadata (author, tags, etc.)",
                                        },
                                    },
                                },
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["async", "blocking"],
                                "default": "async",
                                "description": "Async returns immediately; blocking waits for completion",
                            },
                            "timeout_ms": {
                                "type": "integer",
                                "default": 5000,
                                "description": "Timeout for blocking mode (milliseconds)",
                            },
                        },
                    },
                ),
                Tool(
                    name="jobs_status",
                    description=(
                        "Check status of ingestion jobs. "
                        "Returns current state (queued, running, completed, failed) and error details if any. "
                        "Use this to monitor progress of containers_add operations."
                    ),
                    inputSchema={
                        "type": "object",
                        "required": ["job_ids"],
                        "properties": {
                            "job_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of job UUIDs to check",
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls by proxying to LLC backend."""
            try:
                result = await self._execute_tool(name, arguments)
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by calling the LLC backend API."""
        # Map tool names to API endpoints
        endpoint_map = {
            "containers_list": "/v1/containers/list",
            "containers_describe": "/v1/containers/describe",
            "containers_search": "/v1/search",
            "containers_add": "/v1/containers/add",
            "jobs_status": "/v1/jobs/status",
        }

        if name not in endpoint_map:
            raise ValueError(f"Unknown tool: {name}")

        endpoint = endpoint_map[name]
        url = f"{self.base_url}{endpoint}"

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = await self.client.post(url, json=arguments, headers=headers)

        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", error_detail)
            except Exception:
                pass
            raise RuntimeError(
                f"API request failed (HTTP {response.status_code}): {error_detail}"
            )

        return response.json()

    async def run(self):
        """Start the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def cleanup(self):
        """Clean up resources."""
        await self.client.aclose()


async def main():
    """Main entry point."""
    # Get configuration from environment
    base_url = os.getenv("LLC_BASE_URL", "http://localhost:7801")
    token = os.getenv("LLC_MCP_TOKEN")

    if not token:
        print(
            "Warning: LLC_MCP_TOKEN not set. Authentication may fail.",
            flush=True,
        )

    gateway = LLCMCPGateway(base_url=base_url, token=token)

    try:
        await gateway.run()
    finally:
        await gateway.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

