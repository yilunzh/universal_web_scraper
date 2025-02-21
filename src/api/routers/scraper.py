from fastapi import APIRouter, HTTPException
from typing import Dict
from ..jobs import router as jobs_router

router = APIRouter()

# Remove all the old job handling code and use the new jobs router endpoints 