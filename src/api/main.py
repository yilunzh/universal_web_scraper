from fastapi import FastAPI
from .routers import scraper

app = FastAPI(title="China Auto Sales Scraper API")

# Include the scraper router
app.include_router(scraper.router, prefix="/scraper", tags=["scraper"]) 