from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScraperRequest(BaseModel):
    manufacturer_codes: List[int]
    start_month: Optional[int] = None
    end_month: Optional[int] = None

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    results: Optional[dict] 