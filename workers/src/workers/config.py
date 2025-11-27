"""Worker settings."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_dsn: str = Field(default="postgresql://local:localpw@postgres:5432/registry")
    qdrant_url: str = Field(default="http://qdrant:6333")
    embedding_dims: int = Field(default=768)
    embedder_provider: str = Field(default="nomic", description="nomic | google")
    google_api_key: str = Field(default="", repr=False)
    google_embed_model: str = Field(default="models/text-embedding-004")
    worker_poll_interval: float = Field(default=5.0)
    worker_max_retries: int = Field(default=3)
    worker_visibility_timeout: int = Field(
        default=300,
        description="Seconds before a running job is considered stale and re-queued/failed.",
    )
    worker_heartbeat_interval: int = Field(
        default=30,
        description="Seconds between heartbeats while a job is running.",
    )
    worker_error_backoff: float = Field(
        default=2.0,
        description="Seconds to back off before reprocessing a failed job attempt.",
    )
    nomic_api_key: str = Field(default="", repr=False)
    nomic_api_url: str = Field(default="https://api-atlas.nomic.ai/v1/embedding")
    minio_endpoint: str = Field(default="http://minio:9000")
    minio_access_key: str = Field(default="localminio")
    minio_secret_key: str = Field(default="localminio123", repr=False)
    minio_secure: bool = Field(default=False)
    minio_bucket: str = Field(default="containers")
    semantic_dedup_threshold: float = Field(
        default=0.96,
        description="Cosine similarity threshold for marking chunks as semantic duplicates.",
    )
    embedding_cache_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 7,
        description="Seconds before an embedding cache entry is considered stale and recomputed.",
    )
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9105)
    metrics_host: str = Field(default="0.0.0.0")

    class Config:
        env_prefix = "LLC_"


settings = Settings()
