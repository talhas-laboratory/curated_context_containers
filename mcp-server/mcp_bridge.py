# /// script
# dependencies = [
#     "fastmcp<3.0.0",
#     "httpx>=0.20.0",
# ]
# ///

from fastmcp import FastMCP
import httpx
import os
import json
import logging

# Ensure logs go to stderr to protect stdout JSON-RPC
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configuration
# Hardcoded for reliability - environment variable passing to uv run is unreliable
API_URL = "http://talhas-laboratory.tailefe062.ts.net/api/v1"
TOKEN = "b14b66033a9d16fd82e059cfc43d2e2df9e3a620c764416235c155c6b97454d1"

mcp = FastMCP("Latent Containers")

def _headers():
    return {"Authorization": f"Bearer {TOKEN}"}

@mcp.tool()
def list_containers() -> str:
    """List all available containers and their IDs."""
    try:
        with httpx.Client() as client:
            resp = client.post(
                f"{API_URL}/containers/list",
                headers=_headers(),
                json={}
            )
            resp.raise_for_status()
            data = resp.json()
            # Simplify output for LLM
            summary = []
            for c in data.get("containers", []):
                summary.append(f"Name: {c['name']} (ID: {c['id']}) - State: {c['state']}")
            return "\n".join(summary) if summary else "No containers found."
    except Exception as e:
        return f"Error listing containers: {str(e)}"

@mcp.tool()
def search_container(query: str, container_names: list[str], mode: str = "hybrid") -> str:
    """
    Search inside containers.
    Args:
        query: The search question or topic.
        container_names: List of container NAMES to search in.
        mode: Search mode. Options: "semantic", "graph", "hybrid" (default).
    """
    try:
        with httpx.Client() as client:
            resp = client.post(
                f"{API_URL}/search",
                headers=_headers(),
                json={
                    "query": query,
                    "container_ids": container_names, # Backend handles names too
                    "k": 5,
                    "modes": [mode]
                }
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                return "No results found."
            
            output = []
            for item in results:
                snippet = item.get("snippet") or item.get("text") or ""
                score = item.get("score", 0)
                source = item.get("container_name", "unknown")
                output.append(f"[{source}] (Score: {score:.2f}): {snippet[:500]}...")
            return "\n\n".join(output)
    except Exception as e:
        return f"Error searching: {str(e)}"

@mcp.tool()
def create_container(name: str, description: str = "") -> str:
    """Create a new container for storing knowledge."""
    try:
        with httpx.Client() as client:
            resp = client.post(
                f"{API_URL}/containers/create",
                headers=_headers(),
                json={
                    "name": name, 
                    "description": description,
                    "modalities": ["text", "pdf", "image"], # Default to all
                    "theme": "research" 
                }
            )
            resp.raise_for_status()
            return f"Container '{name}' created successfully. ID: {resp.json()['container_id']}"
    except Exception as e:
        return f"Error creating container: {str(e)}"

@mcp.tool()
def add_knowledge(container_name: str, text: str, title: str) -> str:
    """
    Add text knowledge to a container.
    Args:
        container_name: The name of the container.
        text: The content to add.
        title: A short title for this content.
    """
    try:
        with httpx.Client() as client:
            resp = client.post(
                f"{API_URL}/containers/add",
                headers=_headers(),
                json={
                    "container": container_name,
                    "sources": [{"uri": f"inline:{text}", "title": title, "modality": "text"}],
                    "mode": "sync"
                },
                timeout=60.0
            )
            resp.raise_for_status()
            return f"Knowledge added to '{container_name}' successfully."
    except Exception as e:
        return f"Error adding knowledge: {str(e)}"

if __name__ == "__main__":
    mcp.run()
