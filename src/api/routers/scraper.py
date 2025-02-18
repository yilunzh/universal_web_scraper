from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List
from ..models import ScraperRequest, JobStatus
from ..jobs import jobs, Job, run_scraper_job

router = APIRouter()

@router.post("/start")
async def start_scraper(request: ScraperRequest, background_tasks: BackgroundTasks):
    """Start a new scraping job"""
    job = Job(request)
    jobs[job.id] = job
    
    background_tasks.add_task(run_scraper_job, job.id, request)
    
    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job started successfully"
    }

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a specific job"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "start_time": job.start_time,
        "end_time": job.end_time,
        "error": job.error
    }

@router.get("/results/{job_id}")
async def get_job_results(job_id: str):
    """Get the results of a completed job"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Job is not completed. Current status: {job.status}"
        )
    
    return {
        "job_id": job_id,
        "status": job.status,
        "results": job.results,
        "start_time": job.start_time,
        "end_time": job.end_time
    } 