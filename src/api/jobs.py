from datetime import datetime
from typing import Dict
import uuid
import logging
import traceback
from .models import JobStatus, ScraperRequest
from src.scraper.async_scraper import process_urls
from src.models.data_models import DataPoints
from src.utils.url_generator import (
    generate_urls_from_codes,
    find_first_valid_month_code,
    find_last_valid_month_code,
)
from src.utils.file_operations import save_json_pretty, export_to_csv
from src.config.constants import INPUT_DIR, OUTPUT_DIR, LOGS_DIR
import json

# Standard output filenames
STANDARD_JSON_OUTPUT = OUTPUT_DIR / "china_monthly_auto_sales_data_v2.json"
STANDARD_CSV_OUTPUT = OUTPUT_DIR / "china_monthly_auto_sales_data_v2.csv"

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
            # If start/end month not provided, find valid range
            start_month = request.start_month if request.start_month is not None else find_first_valid_month_code(mfr_code, 1)
            end_month = request.end_month if request.end_month is not None else find_last_valid_month_code(mfr_code, 86)
            
            job_logger.info(f"Manufacturer {mfr_code}:")
            job_logger.info(f"  - Start month: {start_month}")
            job_logger.info(f"  - End month: {end_month}")
            job_logger.info(f"  - Max allowed: 86")
            
            if end_month > 86:
                error_msg = f"Invalid month range: end month {end_month} exceeds maximum allowed (86)"
                job_logger.error(error_msg)
                job.status = JobStatus.FAILED
                job.error = error_msg
                return  # Terminate the job
            
            job_logger.info(f"Manufacturer {mfr_code}: Scraping months {start_month} to {end_month}")
            
            for month_code in range(start_month, end_month + 1):
                url = f"http://www.myhomeok.com/xiaoliang/changshang/{mfr_code}_{month_code}.htm"
                urls.append(url)
        
        job_logger.info(f"Generated {len(urls)} URLs to scrape")

        # Initialize data points
        data_keys = list(DataPoints.__fields__.keys())
        data_fields = DataPoints.__fields__
        data_points = [{"name": key, "value": None, "reference": None, "description": data_fields[key].description} 
                      for key in data_keys]

        # Run the scraper and get results
        try:
            scraped_data = await process_urls(urls, data_points)
            job_logger.info("Scraping completed successfully")

            # Save results using existing functions
            save_json_pretty(scraped_data['value'], str(STANDARD_JSON_OUTPUT))
            export_to_csv(str(STANDARD_JSON_OUTPUT), str(STANDARD_CSV_OUTPUT))
            job_logger.info(f"Data saved to {STANDARD_JSON_OUTPUT} and {STANDARD_CSV_OUTPUT}")

        except Exception as scrape_error:
            job_logger.error(f"Scraping failed: {str(scrape_error)}")
            job_logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        # Store results
        job.results = {
            "output_file": str(STANDARD_JSON_OUTPUT),
            "csv_file": str(STANDARD_CSV_OUTPUT)
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