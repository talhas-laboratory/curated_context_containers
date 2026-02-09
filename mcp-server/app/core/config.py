"""Centralized settings module using Pydantic BaseSettings."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Local Latent Containers MCP"
    environment: str = Field(default="local")
    postgres_dsn: str = Field(default="postgresql://local:localpw@postgres:5432/registry")
    qdrant_url: str = Field(default="http://qdrant:6333")
    minio_endpoint: str = Field(default="http://minio:9000")
    minio_access_key: str = Field(default="localminio")
    minio_secret_key: str = Field(default="localminio123")
    minio_secure: bool = Field(default=False)
    minio_bucket: str = Field(default="containers")
    nomic_api_key: str = Field(default="", repr=False)
    nomic_api_url: str = Field(default="https://api-atlas.nomic.ai/v1/embedding/text")
    nomic_image_url: str = Field(default="https://api-atlas.nomic.ai/v1/embedding/image")
    embedder_provider: str = Field(default="nomic", description="nomic | google")
    google_api_key: str = Field(default="", repr=False)
    google_embed_model: str = Field(default="models/text-embedding-004")
    embedding_dims: int = Field(default=768)
    nomic_image_model: str = Field(default="nomic-embed-image-v1")
    semantic_dedup_threshold: float = Field(default=0.96)
    embedding_cache_ttl_seconds: int = Field(default=60 * 60 * 24 * 7)
    search_latency_budget_ms: int = Field(default=900)
    rerank_api_url: str = Field(default="", description="Optional rerank provider endpoint")
    rerank_api_key: str | None = Field(default=None, repr=False)
    rerank_timeout_ms: int = Field(default=200)
    rerank_top_k_in: int = Field(default=50)
    rerank_top_k_out: int = Field(default=10)
    rerank_cache_ttl_seconds: int = Field(default=300)
    rerank_cache_size: int = Field(default=256)
    mcp_token_path: str = Field(default="")
    mcp_token: str | None = Field(default=None, repr=False)
    manifests_path: str = Field(default="manifests")
    default_principal: str = Field(default="agent:local")
    neo4j_uri: str = Field(default="bolt://neo4j:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="localneo4j", repr=False)
    graph_max_hops_default: int = Field(default=2)
    graph_query_timeout_ms: int = Field(default=1200)
    graph_enable_raw_cypher: bool = Field(default=True)
    graph_nl2cypher_enabled: bool = Field(default=False)
    graph_nl2cypher_url: str = Field(default="", description="Endpoint for NL→Cypher model")
    graph_nl2cypher_api_key: str | None = Field(default=None, repr=False)
    # Use a faster default model to avoid timeouts in clients with ~10s ceilings.
    graph_nl2cypher_model: str = Field(
        default="anthropic/claude-3-haiku",
        description="OpenRouter model id for NL→Cypher translation",
    )
    # Keep this below common client/tool timeouts; 8s is a safer ceiling than 12s.
    graph_nl2cypher_timeout_ms: int = Field(default=8000)
    admin_fastpath: bool = Field(
        default=True,
        description="When true, admin refresh/export jobs are marked done immediately (dev/test convenience)",
    )
    agent_tracking_min_interval_seconds: int = Field(
        default=30,
        description="Minimum interval between agent last_active updates (reduces write load).",
    )
    auto_migrate: bool = Field(
        default=True,
        description="When true, the API attempts to run Postgres migrations on startup (serialized via advisory lock).",
    )
    enable_document_fetch: bool = Field(
        default=False,
        description="When true, enables the /v1/documents/fetch endpoint and MCP tool for retrieving full document content.",
    )

    @property
    def async_postgres_dsn(self) -> str:
        if "+asyncpg" in self.postgres_dsn:
            return self.postgres_dsn
        if self.postgres_dsn.startswith("postgresql://"):
            return self.postgres_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.postgres_dsn

    class Config:
        env_file = ".env"
        env_prefix = "LLC_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
