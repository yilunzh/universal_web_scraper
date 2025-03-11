from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import scraper
from .routers import sql  # Import our new SQL router
from .jobs import router as jobs_router  # Updated import

app = FastAPI(title="China Auto Sales Scraper API")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the scraper router
app.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
app.include_router(jobs_router, prefix="/api")  # Add the jobs router
app.include_router(sql.router, prefix="/sql", tags=["sql"])  # Add the SQL router 