from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ScraperRequest(BaseModel):
    manufacturer_codes: List[int]
    start_month: int
    end_month: int

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    results: Optional[dict] 