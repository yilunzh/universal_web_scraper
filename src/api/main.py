from fastapi import FastAPI
from .routers import scraper
from .jobs import router as jobs_router  # Updated import

app = FastAPI(title="China Auto Sales Scraper API")

# Include the scraper router
app.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
app.include_router(jobs_router, prefix="/api")  # Add the jobs router 