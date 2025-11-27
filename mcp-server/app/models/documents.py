"""Pydantic schemas for document management endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    id: str
    uri: Optional[str] = None
    title: Optional[str] = None
    mime: str
    hash: str
    state: str = "active"
    chunk_count: int = 0
    meta: dict | None = None
    created_at: datetime
    updated_at: datetime


class ListDocumentsRequest(BaseModel):
    container: str = Field(description="Container UUID or slug")
    limit: int = Field(default=25, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    search: Optional[str] = Field(default=None, description="Optional substring filter")


class ListDocumentsResponse(BaseModel):
    version: str = "v1"
    request_id: str
    partial: bool = False
    container_id: str
    documents: List[DocumentItem]
    total: int
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class DeleteDocumentRequest(BaseModel):
    container: str = Field(description="Container UUID or slug")
    document_id: str = Field(description="Document UUID")


class DeleteDocumentResponse(BaseModel):
    version: str = "v1"
    request_id: str
    document_id: str
    deleted: bool = True
    timings_ms: dict = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)

