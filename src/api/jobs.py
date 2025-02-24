from datetime import datetime
from typing import Dict, List
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
from fastapi import APIRouter, HTTPException, Response
from src.db.supabase_client import (
    create_scrape_job, 
    update_url_status, 
    add_log, 
    get_job_status,
    update_job_status,
    get_all_jobs,
    update_job_progress,
    add_job_log,
)
import asyncio
import pandas as pd
from io import StringIO
from pydantic import BaseModel
import os

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

# Request models
class CreateJobRequest(BaseModel):
    job_name: str
    urls: List[str]

class GenerateJobRequest(BaseModel):
    job_name: str
    manufacturer_csv: str
    month_csv: str

class ManufacturerScrapeRequest(BaseModel):
    job_name: str
    manufacturer_codes: List[str]  # Changed to list of codes
    start_month_code: str | None = None
    end_month_code: str | None = None

router = APIRouter()

@router.post("/jobs/")
async def create_job(request: CreateJobRequest) -> Dict:
    """Create a new scraping job"""
    try:
        # Create the job
        job = await create_scrape_job(request.job_name, request.urls)
        job_id = job['id']
        
        # Automatically start the job
        await start_job(job_id)
        
        return {
            "message": "Job created and started successfully", 
            "job_id": job_id,
            "status": "in_progress"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/start")
async def start_job(job_id: int) -> Dict:
    """Start processing a job with parallel URL processing"""
    try:
        # Get job details
        job_result = await get_job_status(job_id)
        job = job_result.data[0]
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Update job status first
        await update_job_status(job_id, "in_progress")
        
        # Initialize data points
        data_keys = list(DataPoints.__fields__.keys())
        data_fields = DataPoints.__fields__
        data_points = [
            {"name": key, "value": None, "reference": None, "description": data_fields[key].description}
            for key in data_keys
        ]
        
        # Process URLs in parallel with a semaphore to limit concurrency
        MAX_CONCURRENT = 5  # Adjust based on your needs
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def process_single_url(job_url):
            """Process a single URL with semaphore"""
            try:
                async with semaphore:
                    # Check if job was cancelled
                    job_status = await get_job_status(job_id)
                    if job_status.data[0]['status'] == 'cancelled':
                        if job_url['status'] in ['pending', 'in_progress']:
                            await update_url_status(job_url['id'], "cancelled")
                        return
                        
                    await update_url_status(job_url['id'], "in_progress")
                    result = await process_urls([job_url['url']], data_points)
                    
                    # Check again for cancellation
                    job_status = await get_job_status(job_id)
                    if job_status.data[0]['status'] == 'cancelled':
                        await update_url_status(job_url['id'], "cancelled")
                        return
                    
                    if 'error' in result or not result.get('value'):
                        print(f"Failed to process URL: {job_url['url']}")  # Debug log
                        await update_url_status(job_url['id'], "failed")
                    else:
                        await update_url_status(job_url['id'], "completed", result['value'][0])
            
            except Exception as e:
                print(f"Failed to process URL: {job_url['url']} with error: {str(e)}")  # Debug log
                await update_url_status(job_url['id'], "failed")
        
        # Create tasks for all pending URLs
        tasks = []
        for job_url in job['job_urls']:
            if job_url['status'] == 'pending':
                task = process_single_url(job_url)  # Don't create_task yet
                tasks.append(task)
        
        # Create a single task that processes all URLs and handles completion
        async def process_all():
            try:
                # Process all URLs silently
                await asyncio.gather(*tasks)
                
                # Get final job status
                final_job = await get_job_status(job_id)
                if not final_job.data:
                    raise Exception(f"Could not find job {job_id}")
                    
                job_data = final_job.data[0]
                if not job_data.get('job_urls'):
                    raise Exception(f"No URLs found for job {job_id}")
                
                try:
                    # Calculate final stats and collect failed URLs
                    completed_urls = [u for u in job_data['job_urls'] if u.get('status') == 'completed']
                    failed_urls = [u for u in job_data['job_urls'] if u.get('status') == 'failed']
                    
                    url_stats = {
                        'total': len(job_data['job_urls']),
                        'completed': len(completed_urls),
                        'failed': len(failed_urls),
                    }
                    
                    # Generate final summary with array format
                    failed_url_list = [u.get('url', 'Unknown URL') for u in failed_urls]
                    summary = f"""
                    Job Complete: {job_data.get('job_name', 'Unknown Job')}
                    =====================================
                    Total URLs processed: {url_stats['total']}
                    Successfully scraped: {url_stats['completed']}
                    Failed: {url_stats['failed']}
                    Success rate: {(url_stats['completed'] / url_stats['total'] * 100):.1f}%
                    
                    Failed URLs ({len(failed_url_list)}): [
                        {chr(10).join('  ' + url for url in failed_url_list) if failed_url_list else 'None'}
                    ]
                    """
                    
                    # Save summary to output directory
                    summary_path = OUTPUT_DIR / f"job_{job_id}_summary.txt"
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    print(f"\nSummary saved to {summary_path}")
                    
                    # Add summary to job logs
                    await add_job_log(
                        job_id=job_id,
                        message=summary,
                        level="INFO"
                    )
                    
                    # Update final status
                    final_status = (
                        "completed" if url_stats['failed'] == 0
                        else "partial_success" if url_stats['completed'] > 0
                        else "failed"
                    )
                    
                    # Send single notification at job completion
                    os.system(f"""
                        osascript -e 'display notification "Status: {final_status}
                        Total: {url_stats['total']}
                        Success: {url_stats['completed']}
                        Failed: {url_stats['failed']}" with title "Job {job_id} Complete"'
                    """)
                    
                    print(f"\nJob {job_id} completed!")
                    print(summary)
                    await update_job_status(job_id, final_status)
                    
                except Exception as e:
                    print(f"Error processing job results: {str(e)}")
                    await update_job_status(job_id, "failed")
                    raise
                
            except Exception as e:
                print(f"Error in job completion: {str(e)}")
                await update_job_status(job_id, "failed")
                # Notify on error
                os.system(f"""
                    osascript -e 'display notification "Job failed: {str(e)}" with title "Job {job_id} Error"'
                """)
        
        # Start processing in background
        asyncio.create_task(process_all())
        
        # Return immediately with minimal info
        return {
            "message": "Job processing started",
            "job_id": job_id
        }
        
    except Exception as e:
        await update_job_status(job_id, "failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job(job_id: int) -> Dict:
    """Get job status and details"""
    try:
        result = await get_job_status(job_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/data")
async def get_job_data(job_id: int, format: str = "json") -> Dict:
    """Get scraped data for a job"""
    try:
        result = await get_job_status(job_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job = result.data[0]
        all_data = []
        
        for url in job['job_urls']:
            if url.get('scraped_data'):
                all_data.extend(url['scraped_data'][0]['data'])
                
        if format == "json":
            return {"data": all_data}
        elif format == "csv":
            # Convert to DataFrame and then to CSV
            df = pd.DataFrame(all_data)
            csv_string = df.to_csv(index=False)
            return Response(
                content=csv_string,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=job_{job_id}_data.csv"}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/")
async def list_jobs(limit: int = 10, offset: int = 0) -> Dict:
    """Get list of all jobs with pagination"""
    try:
        jobs = await get_all_jobs(limit, offset)
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/generate")
async def generate_job(request: GenerateJobRequest) -> Dict:
    """Create a job from CSV files"""
    try:
        urls = generate_urls_from_codes(request.manufacturer_csv, request.month_csv)
        job = await create_scrape_job(request.job_name, urls)
        await start_job(job['id'])
        return {"message": "Job created and started", "job_id": job['id']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int) -> Dict:
    """Cancel a running job"""
    try:
        # Get job status
        job_result = await get_job_status(job_id)
        if not job_result.data:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job = job_result.data[0]
        current_status = job['status']
            
        if current_status not in ['in_progress', 'pending']:
            return {
                "success": False,
                "message": f"Job cannot be cancelled - current status: {current_status}"
            }
            
        # Update job status to cancelled
        await update_job_status(job_id, "cancelled")
        await add_job_log(job_id, "Job cancelled by user", "INFO")
        
        # Get counts for response
        url_counts = {
            'total': len(job['job_urls']),
            'cancelled': len([u for u in job['job_urls'] if u['status'] in ['in_progress', 'pending']]),
            'completed': len([u for u in job['job_urls'] if u['status'] == 'completed']),
            'failed': len([u for u in job['job_urls'] if u['status'] == 'failed'])
        }
        
        # Update any in-progress or pending URLs to cancelled
        for url in job['job_urls']:
            if url['status'] in ['in_progress', 'pending']:
                await update_url_status(url['id'], "cancelled")
                await add_log(url['id'], "URL processing cancelled", "INFO")
        
        return {
            "success": True,
            "message": "Job cancelled successfully",
            "job_id": job_id,
            "previous_status": current_status,
            "url_stats": {
                "total_urls": url_counts['total'],
                "cancelled_urls": url_counts['cancelled'],
                "completed_urls": url_counts['completed'],
                "failed_urls": url_counts['failed']
            }
        }
        
    except Exception as e:
        print(f"Error cancelling job: {e}")
        return {
            "success": False,
            "message": f"Error cancelling job: {str(e)}",
            "job_id": job_id
        }

@router.post("/jobs/{job_id}/retry-failed")
async def retry_failed_urls(job_id: int) -> Dict:
    """Retry failed URLs in a job"""
    try:
        job_result = await get_job_status(job_id)
        job = job_result.data[0]
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        # Get failed URLs
        failed_urls = [url for url in job['job_urls'] if url['status'] == 'failed']
        if not failed_urls:
            return {"message": "No failed URLs to retry"}
            
        # Update job status
        await update_job_status(job_id, "in_progress")
        
        # Initialize data points (same as in start_job)
        data_keys = list(DataPoints.__fields__.keys())
        data_fields = DataPoints.__fields__
        data_points = [
            {"name": key, "value": None, "reference": None, "description": data_fields[key].description}
            for key in data_keys
        ]
        
        # Process each failed URL
        completed = 0
        total = len(failed_urls)
        
        for job_url in failed_urls:
            try:
                await update_url_status(job_url['id'], "in_progress")
                result = await process_urls([job_url['url']], data_points)
                
                if 'error' in result:
                    await update_url_status(job_url['id'], "failed")
                    await add_log(job_url['id'], f"Retry failed: {result['error']}", "ERROR")
                else:
                    await update_url_status(job_url['id'], "completed", result.get('value', []))
                    await add_log(job_url['id'], "Successfully scraped URL on retry", "INFO")
                    completed += 1
                    
                # Update progress
                await update_job_progress(job_id, total, completed)
                    
            except Exception as e:
                await update_url_status(job_url['id'], "failed")
                await add_log(job_url['id'], f"Retry error: {str(e)}", "ERROR")
        
        # Update final job status
        final_status = "completed" if completed == total else "partial_success"
        await update_job_status(job_id, final_status)
        
        return {
            "message": f"Retry completed. {completed}/{total} URLs succeeded",
            "status": final_status
        }
        
    except Exception as e:
        await update_job_status(job_id, "failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: int) -> Dict:
    """Get detailed progress of a job"""
    try:
        print(f"\n=== Getting progress for job {job_id} ===")
        
        # Test Supabase connection first
        print("Testing Supabase connection...")
        try:
            result = await get_job_status(job_id)
            print(f"Supabase response received")
        except Exception as e:
            print(f"Supabase connection error: {str(e)}")
            raise
            
        if not result.data:
            print(f"No data found for job {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
            
        job = result.data[0]
        print(f"Found job: {job['job_name']}")
        urls = job['job_urls']
        
        # Get status counts
        print("Calculating status counts...")
        url_statuses = [url['status'] for url in urls]
        completed = len([s for s in url_statuses if s == 'completed'])
        failed = len([s for s in url_statuses if s == 'failed'])
        in_progress = len([s for s in url_statuses if s == 'in_progress'])
        pending = len([s for s in url_statuses if s == 'pending'])
        
        # Get recent logs
        print("Getting recent logs...")
        recent_logs = []
        for url in urls:
            if url.get('scrape_logs'):
                latest_log = sorted(
                    url['scrape_logs'],
                    key=lambda x: x['created_at'],
                    reverse=True
                )[0]
                recent_logs.append({
                    'url': url['url'],
                    'status': url['status'],
                    'message': latest_log['log_message'],
                    'level': latest_log['log_level'],
                    'timestamp': latest_log['created_at']
                })
        
        # Get currently processing URLs
        print("Getting in-progress URLs...")
        current_urls = [
            {'url': url['url'], 'status': url['status']}
            for url in urls
            if url['status'] == 'in_progress'
        ]
        
        response = {
            "job_id": job_id,
            "job_name": job['job_name'],
            "status": job['status'],
            "progress": {
                "total_urls": job['total_urls'],
                "completed_urls": job['completed_urls'],
                "percentage": job['progress_percentage'],
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
                "pending": pending
            },
            "current_processing": current_urls,
            "recent_logs": recent_logs[:10],  # Last 10 logs
            "started_at": job['created_at'],
            "updated_at": job['completed_at'] or job['created_at']
        }
        
        print(f"Returning response with {len(recent_logs)} logs and {len(current_urls)} in-progress URLs")
        return response
        
    except Exception as e:
        print(f"Error in get_job_progress:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/manufacturer")
async def create_manufacturer_job(request: ManufacturerScrapeRequest) -> Dict:
    """Create a single job to scrape data for multiple manufacturers"""
    try:
        print(f"Creating job for manufacturers: {request.manufacturer_codes}")
        
        # Generate all URLs for all manufacturers
        all_urls = []
        manufacturer_ranges = {}  # Store the range for each manufacturer
        
        for manufacturer_code in request.manufacturer_codes:
            print(f"\nProcessing manufacturer {manufacturer_code}")
            mfr_code_int = int(manufacturer_code)
            
            try:
                # Determine month range for this manufacturer
                start_month = (int(request.start_month_code) if request.start_month_code
                             else find_first_valid_month_code(
                                 manufacturer_code=mfr_code_int,
                                 min_month=1
                             ))
                print(f"Start month for {manufacturer_code}: {start_month}")
                
                end_month = (int(request.end_month_code) if request.end_month_code
                           else find_last_valid_month_code(
                               manufacturer_code=mfr_code_int,
                               max_month=86
                           ))
                print(f"End month for {manufacturer_code}: {end_month}")
                
                # Store the range for this manufacturer
                manufacturer_ranges[manufacturer_code] = {
                    'start': start_month,
                    'end': end_month
                }
                
                # Generate URLs for this manufacturer
                current_month = start_month
                while current_month <= end_month:
                    url = f"http://www.myhomeok.com/xiaoliang/changshang/{manufacturer_code}_{current_month}.htm"
                    all_urls.append(url)
                    current_month += 1
                
                print(f"Generated {end_month - start_month + 1} URLs for manufacturer {manufacturer_code}")
                
            except Exception as e:
                print(f"Error processing manufacturer {manufacturer_code}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to process manufacturer {manufacturer_code}: {str(e)}"
                )
        
        print(f"\nGenerated {len(all_urls)} URLs total")
        
        # Create a single job with all URLs
        job_name = (f"{request.job_name} "
                   f"(Manufacturers: {','.join(request.manufacturer_codes)})")
        
        # Create and start single job with all URLs
        job = await create_scrape_job(job_name, all_urls)
        await start_job(job['id'])
        
        return {
            "message": "Manufacturer scrape job created and started",
            "job_id": job['id'],
            "manufacturer_codes": request.manufacturer_codes,
            "manufacturer_ranges": manufacturer_ranges,
            "total_urls": len(all_urls),
            "urls_per_manufacturer": {
                mfr: ranges['end'] - ranges['start'] + 1
                for mfr, ranges in manufacturer_ranges.items()
            }
        }
        
    except Exception as e:
        print(f"Error in create_manufacturer_job: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_endpoint():
    """Simple endpoint to test if server is responding"""
    print("Test endpoint called")
    return {"status": "ok", "message": "Server is running"}

async def monitor_job_status(job_id: int):
    """Monitor job progress and update status when complete"""
    try:
        while True:
            try:
                # Get current job status
                job_result = await get_job_status(job_id)
                if not job_result.data:
                    print(f"No data found for job {job_id}")
                    break
                    
                job = job_result.data[0]
                
                # Calculate URL stats
                url_stats = {
                    'total': len(job['job_urls']),
                    'completed': len([u for u in job['job_urls'] if u['status'] == 'completed']),
                    'failed': len([u for u in job['job_urls'] if u['status'] == 'failed']),
                    'in_progress': len([u for u in job['job_urls'] if u['status'] == 'in_progress']),
                    'pending': len([u for u in job['job_urls'] if u['status'] == 'pending'])
                }
                
                # Update job progress
                await update_job_progress(
                    job_id=job_id,
                    total_urls=url_stats['total'],
                    completed_urls=url_stats['completed'] + url_stats['failed']
                )
                
                # Check if job is complete (no pending or in-progress URLs)
                if url_stats['in_progress'] == 0 and url_stats['pending'] == 0:
                    # Generate summary report
                    failed_urls = [u['url'] for u in job['job_urls'] if u['status'] == 'failed']
                    summary = f"""
                    Job Summary for {job['job_name']}
                    =====================================
                    Total URLs: {url_stats['total']}
                    Successful: {url_stats['completed']}
                    Failed: {url_stats['failed']}
                    
                    Failed URLs:
                    {chr(10).join(f'- {url}' for url in failed_urls) if failed_urls else 'None'}
                    """
                    
                    try:
                        # Try to add job log
                        await add_job_log(
                            job_id=job_id,
                            message=summary,
                            level="INFO"
                        )
                    except Exception as log_error:
                        print(f"Error adding job log: {log_error}")
                    
                    # Update final status
                    final_status = (
                        "completed" if url_stats['failed'] == 0
                        else "partial_success" if url_stats['completed'] > 0
                        else "failed"
                    )
                    
                    print(f"Job {job_id} completed with status: {final_status}")
                    await update_job_status(job_id, final_status)
                    break
                
                # Wait before checking again
                await asyncio.sleep(5)
                
            except Exception as loop_error:
                print(f"Error in monitoring loop: {loop_error}")
                await asyncio.sleep(5)  # Wait before retrying
            
    except Exception as e:
        print(f"Fatal error monitoring job {job_id}: {e}")
        try:
            await update_job_status(job_id, "failed")
        except:
            pass  # Ignore errors in final status update 