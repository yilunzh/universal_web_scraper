from datetime import datetime
from typing import Dict
import uuid
import logging
import traceback
from .models import JobStatus, ScraperRequest
from src.scraper.async_scraper import process_urls
from src.models.data_models import DataPoints
from src.utils.url_generator import generate_urls_from_codes
from src.config.constants import INPUT_DIR, OUTPUT_DIR, LOGS_DIR

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Add file handler for job-specific logs
def get_job_logger(job_id: str):
    job_log_file = LOGS_DIR / f"job_{job_id}.log"
    handler = logging.FileHandler(job_log_file)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    return logger, handler

class Job:
    def __init__(self, request: ScraperRequest):
        self.id = str(uuid.uuid4())
        self.status = JobStatus.QUEUED
        self.request = request
        self.results = None
        self.error = None
        self.start_time = None
        self.end_time = None

# In-memory job storage
jobs: Dict[str, Job] = {}

async def run_scraper_job(job_id: str, request: ScraperRequest):
    """Background task to run the scraper"""
    job_logger, handler = get_job_logger(job_id)
    job = jobs[job_id]
    job.status = JobStatus.RUNNING
    job.start_time = datetime.now()

    try:
        job_logger.info(f"Starting job {job_id}")
        job_logger.info(f"Request parameters: {request.dict()}")

        # Generate URLs based on request parameters
        urls = []
        for mfr_code in request.manufacturer_codes:
            for month_code in range(request.start_month, request.end_month + 1):
                url = f"http://www.myhomeok.com/xiaoliang/changshang/{mfr_code}_{month_code}.htm"
                urls.append(url)
        
        job_logger.info(f"Generated {len(urls)} URLs to scrape")

        # Initialize data points
        data_keys = list(DataPoints.__fields__.keys())
        data_fields = DataPoints.__fields__
        data_points = [{"name": key, "value": None, "reference": None, "description": data_fields[key].description} 
                      for key in data_keys]

        # Set up output filename for this job
        filename = OUTPUT_DIR / f"job_{job_id}.json"
        job_logger.info(f"Output will be saved to {filename}")

        # Run the scraper
        try:
            await process_urls(urls, data_points, str(filename))
            job_logger.info("Scraping completed successfully")
        except Exception as scrape_error:
            job_logger.error(f"Scraping failed: {str(scrape_error)}")
            job_logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        # Store results
        job.results = {
            "output_file": str(filename),
            "csv_file": str(filename).replace('.json', '.csv')
        }
        job.status = JobStatus.COMPLETED
        job_logger.info("Job completed successfully")

    except Exception as e:
        error_msg = f"Job failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        job_logger.error(error_msg)
        job.status = JobStatus.FAILED
        job.error = error_msg
    finally:
        job.end_time = datetime.now()
        job_logger.info(f"Job ended with status: {job.status}")
        logger.removeHandler(handler) 