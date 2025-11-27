"""Job enqueue helpers."""
from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Container, Job
from app.models.containers import AddSource, ContainersAddRequest, ContainersAddResponse, JobSummary
from app.services import manifests


class ContainerNotFoundError(ValueError):
    """Raised when a container lookup fails."""


class JobValidationError(ValueError):
    """Raised when a source payload violates manifest/policy."""

    def __init__(self, code: str, message: str):
        super().__init__(code)
        self.code = code
        self.message = message


def _derive_modality(source: AddSource) -> str:
    """Infer modality from mime type or URI."""
    if source.mime:
        if source.mime.startswith("application/pdf"):
            return "pdf"
        if source.mime.startswith("image/"):
            return "image"
    if source.uri.lower().endswith(".pdf"):
        return "pdf"
    if source.uri.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
        return "image"
    return "text"


def _validate_sources(
    sources: List[AddSource],
    allowed_modalities: List[str],
    manifest: dict | None = None,
) -> None:
    """Validate requested sources against manifest-defined policy."""
    manifest = manifest or {}
    pdf_limits = manifest.get("pdf") or {}
    max_pdf_pages = pdf_limits.get("max_pages")
    limits = manifest.get("limits") or {}
    max_size_mb = limits.get("max_size_mb")

    for source in sources:
        modality = _derive_modality(source)
        if allowed_modalities and modality not in allowed_modalities:
            raise JobValidationError(
                "BLOCKED_MODALITY",
                f"modality '{modality}' not allowed; allowed={allowed_modalities}",
            )
        meta = source.meta or {}
        if modality == "pdf" and max_pdf_pages:
            pages = meta.get("pages") or meta.get("page_count")
            if pages and pages > max_pdf_pages:
                raise JobValidationError(
                    "PAYLOAD_TOO_LARGE",
                    f"pdf pages {pages} exceed limit {max_pdf_pages}",
                )
        if max_size_mb:
            size_bytes = meta.get("size_bytes")
            if size_bytes and size_bytes > max_size_mb * 1024 * 1024:
                raise JobValidationError(
                    "PAYLOAD_TOO_LARGE",
                    f"payload size {size_bytes}B exceeds limit {max_size_mb}MB",
                )


async def enqueue_jobs(session: AsyncSession, request: ContainersAddRequest) -> ContainersAddResponse:
    start = perf_counter()

    container_filters = [Container.name == request.container]
    candidate_uuid = _maybe_uuid(request.container)
    if candidate_uuid:
        container_filters.append(Container.id == candidate_uuid)
    container_stmt = select(Container).where(or_(*container_filters))
    container = (await session.execute(container_stmt)).scalar_one_or_none()
    if not container:
        raise ContainerNotFoundError("CONTAINER_NOT_FOUND")

    manifest = manifests.load_manifest(container.name) or {}
    allowed_modalities = manifest.get("modalities") or list(container.modalities or [])
    _validate_sources(request.sources, allowed_modalities, manifest)

    job_summaries: List[JobSummary] = []
    for source in request.sources:
        job_id = uuid4()
        job = Job(
            id=job_id,
            kind="ingest",
            status="queued",
            container_id=container.id,
            payload={"source": source.model_dump(), "container_id": str(container.id)},
            error=None,
            retries=0,
        )
        session.add(job)
        job_summaries.append(
            JobSummary(
                job_id=str(job_id),
                status="queued",
                source_uri=source.uri,
                submitted_at=datetime.utcnow(),
            )
        )

    await session.commit()
    elapsed = int((perf_counter() - start) * 1000)
    return ContainersAddResponse(
        request_id=str(uuid4()),
        jobs=job_summaries,
        timings_ms={"db_query": elapsed},
    )
def _maybe_uuid(value: str | None) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None
