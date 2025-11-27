"""ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, JSON, Enum, Text
from sqlalchemy.dialects.postgresql import INT4RANGE, TSRANGE, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Container(Base):
    __tablename__ = "containers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    theme: Mapped[str | None]
    description: Mapped[str | None]
    modalities: Mapped[list[str]] = mapped_column(ARRAY(Text))
    embedder: Mapped[str]
    embedder_version: Mapped[str]
    dims: Mapped[int]
    policy: Mapped[dict[str, Any]] = mapped_column(JSON)
    acl: Mapped[dict[str, Any]] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(Enum("active", "paused", "archived", name="container_state"))
    stats: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now())
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class ContainerVersion(Base):
    __tablename__ = "container_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    container_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    version: Mapped[str]
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime]


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    kind: Mapped[str] = mapped_column(Enum("ingest", "refresh", "export", name="job_kind"))
    status: Mapped[str] = mapped_column(Enum("queued", "running", "done", "failed", name="job_status"))
    container_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    error: Mapped[str | None]
    retries: Mapped[int]
    last_heartbeat: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    container_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    uri: Mapped[str | None]
    mime: Mapped[str]
    hash: Mapped[str]
    title: Mapped[str | None]
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    container_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    doc_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    modality: Mapped[str]
    text: Mapped[str | None]
    tsv: Mapped[str] = mapped_column(TSVECTOR)
    offsets: Mapped[Any | None] = mapped_column(INT4RANGE)
    tsrange: Mapped[Any | None] = mapped_column(TSRANGE)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    embedding_version: Mapped[str]
    dedup_of: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now())
