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
    nomic_api_url: str = Field(default="https://api-atlas.nomic.ai/v1/embedding")
    embedder_provider: str = Field(default="nomic", description="nomic | google")
    google_api_key: str = Field(default="", repr=False)
    google_embed_model: str = Field(default="models/text-embedding-004")
    embedding_dims: int = Field(default=768)
    semantic_dedup_threshold: float = Field(default=0.96)
    embedding_cache_ttl_seconds: int = Field(default=60 * 60 * 24 * 7)
    search_latency_budget_ms: int = Field(default=900)
    rerank_api_url: str = Field(default="", description="Optional rerank provider endpoint")
    rerank_api_key: str | None = Field(default=None, repr=False)
    rerank_timeout_ms: int = Field(default=200)
    rerank_top_k_in: int = Field(default=50)
    rerank_top_k_out: int = Field(default=10)
    mcp_token_path: str = Field(default="docker/mcp_token.txt")
    mcp_token: str | None = Field(default=None, repr=False)
    manifests_path: str = Field(default="manifests")
    default_principal: str = Field(default="agent:local")

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
