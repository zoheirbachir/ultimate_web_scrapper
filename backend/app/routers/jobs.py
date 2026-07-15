from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import get_current_user
from app.schemas import JobCreate, JobOut, ResultOut

router = APIRouter(prefix="/v1", tags=["jobs"])


def _store(request: Request):
    return request.app.state.store


def _runner(request: Request):
    return request.app.state.runner


@router.post("/jobs", response_model=JobOut)
async def create_job(payload: JobCreate, request: Request,
                     user_id: str = Depends(get_current_user)):
    store = _store(request)
    job = await store.create_job(user_id, payload.model_dump(), total=len(payload.urls))
    _runner(request).submit(job["id"], user_id)
    return job


@router.get("/jobs", response_model=List[JobOut])
async def list_jobs(request: Request, user_id: str = Depends(get_current_user)):
    return await _store(request).list_jobs(user_id)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, request: Request, user_id: str = Depends(get_current_user)):
    job = await _store(request).get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/results", response_model=List[ResultOut])
async def get_results(job_id: str, request: Request, user_id: str = Depends(get_current_user)):
    store = _store(request)
    if not await store.get_job(job_id, user_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return await store.list_results(job_id, user_id)


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: str, request: Request, user_id: str = Depends(get_current_user)):
    store = _store(request)
    job = await store.get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in ("queued", "running"):
        await store.set_job_status(job_id, "canceled", finished=True)
    return await store.get_job(job_id, user_id)
