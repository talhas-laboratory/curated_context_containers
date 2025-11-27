"""Job status endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.db.session import get_session
from app.db.models import Job
from app.core.security import verify_bearer_token

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


class JobStatusRequest(BaseModel):
    job_ids: List[str]


@router.post("/status")
async def get_job_status(
    request: JobStatusRequest,
    session: AsyncSession = Depends(get_session),
    authenticated: bool = Depends(verify_bearer_token),
):
    """Get status for one or more jobs."""
    if not request.job_ids:
        return {"jobs": []}
    
    try:
        uuids = [UUID(jid) for jid in request.job_ids]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid job ID format: {exc}") from exc
    
    stmt = select(Job).where(Job.id.in_(uuids))
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    
    job_map = {str(job.id): job for job in jobs}
    
    return {
        "jobs": [
            {
                "job_id": jid,
                "status": job_map[jid].status if jid in job_map else "not_found",
                "error": job_map[jid].error if jid in job_map and job_map[jid].error else None,
                "created_at": job_map[jid].created_at.isoformat() if jid in job_map else None,
                "updated_at": job_map[jid].updated_at.isoformat() if jid in job_map else None,
            }
            for jid in request.job_ids
        ]
    }
