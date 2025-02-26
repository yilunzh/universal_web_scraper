from supabase import create_client
from typing import Dict, List
import os
from datetime import datetime
import traceback
from supabase.client import ClientOptions
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()
load_dotenv('.env.local')  # Load .env.local which should override .env

print("\n=== Initializing Supabase Client ===")
try:
    # Create options object correctly
    options = ClientOptions(
        schema='public',
        headers={},
        persist_session=False,
        auto_refresh_token=False
    )
    
    # Get values from environment after loading dotenv
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Validate environment variables
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in environment variables")
    
    supabase = create_client(
        supabase_url,
        supabase_key,
        options=options
    )
    print("✓ Supabase client created")
    
    # Test the connection immediately
    test_query = supabase.table('scrape_jobs').select("*").limit(1).execute()
    print("✓ Test query successful")
except Exception as e:
    print(f"ERROR initializing Supabase:")
    print(f"Error type: {type(e)}")
    print(f"Error message: {str(e)}")
    print(f"Traceback: {traceback.format_exc()}")
    raise

# Add at the start of the file after client initialization
print("Initializing Supabase client...")
print(f"URL: {os.getenv('SUPABASE_URL')}")
print(f"Key length: {len(os.getenv('SUPABASE_SERVICE_ROLE_KEY'))}")

def get_supabase_client():
    """Get the Supabase client instance."""
    return supabase

async def create_scrape_job(job_name: str, urls: List[str]) -> Dict:
    """Create a new scrape job with multiple URLs"""
    
    # Insert the job
    job_data = {
        'job_name': job_name,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'total_urls': len(urls),
        'completed_urls': 0,
        'progress_percentage': 0
    }
    job = supabase.table('scrape_jobs').insert(job_data).execute()
    job_id = job.data[0]['id']
    
    # Insert the URLs
    url_data = [
        {
            'job_id': job_id,
            'url': url,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        for url in urls
    ]
    supabase.table('job_urls').insert(url_data).execute()
    
    return job.data[0]

async def update_url_status(job_url_id: int, status: str, data: Dict = None):
    """Update status and optionally add scraped data for a URL"""
    
    # Update URL status
    supabase.table('job_urls').update({
        'status': status,
        'completed_at': datetime.utcnow().isoformat() if status in ['completed', 'failed'] else None
    }).eq('id', job_url_id).execute()
    
    # If we have scraped data, store it
    if data:
        supabase.table('scraped_data').insert({
            'job_url_id': job_url_id,
            'data': data,
            'created_at': datetime.utcnow().isoformat()
        }).execute()

async def add_log(job_url_id: int, message: str, level: str = 'INFO'):
    """Add a log entry for a URL"""
    supabase.table('scrape_logs').insert({
        'job_url_id': job_url_id,
        'log_message': message,
        'log_level': level,
        'created_at': datetime.utcnow().isoformat()
    }).execute()

async def get_job_status(job_id: int) -> Dict:
    """Get detailed status of a job including all URLs and recent logs"""
    print(f"\n=== Getting status for job {job_id} ===")
    try:
        print("Building query...")
        # Get job with basic URL status counts
        result = supabase.table('scrape_jobs')\
            .select('*, job_urls(status)')\
            .eq('id', job_id)\
            .execute()
        print("Basic query executed")
        
        if not result.data:
            print("No job found with this ID")
            return result
            
        # Get the basic job status
        job = result.data[0]
        urls = job['job_urls']
        
        # Calculate URL processing stats
        url_stats = {
            'total': len(urls),
            'processed': len([u for u in urls if u['status'] in ['completed', 'failed']]),
            'completed': len([u for u in urls if u['status'] == 'completed']),
            'failed': len([u for u in urls if u['status'] == 'failed']),
            'in_progress': len([u for u in urls if u['status'] == 'in_progress']),
            'pending': len([u for u in urls if u['status'] == 'pending'])
        }
        url_stats['remaining'] = url_stats['total'] - url_stats['processed']
        
        # Add stats to job data
        job['url_stats'] = url_stats
        result.data[0] = job
        
        # If job is still running, return basic status
        if job['status'] == 'in_progress':
            print("Job is in progress, returning basic status")
            return result
            
        # For completed jobs, get full details including logs
        print("Getting full job details...")
        full_result = supabase.table('scrape_jobs')\
            .select('''
                *,
                job_urls!inner (
                    *,
                    scraped_data (*),
                    scrape_logs (*)
                )
            ''')\
            .eq('id', job_id)\
            .execute()
        
        # Add stats to full result
        if full_result.data:
            full_result.data[0]['url_stats'] = url_stats
            
        print("Full query executed")
        return full_result
        
    except Exception as e:
        print(f"ERROR in get_job_status:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise

async def update_job_status(job_id: int, status: str):
    """Update the overall job status"""
    supabase.table('scrape_jobs').update({
        'status': status,
        'completed_at': datetime.utcnow().isoformat() if status in ['completed', 'failed', 'partial_success'] else None
    }).eq('id', job_id).execute()

async def get_all_jobs(limit: int = 10, offset: int = 0) -> Dict:
    """Get all jobs with pagination"""
    return supabase.table('scrape_jobs')\
        .select('*, job_urls(status)')\
        .order('created_at', desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()

async def update_job_progress(job_id: int, total_urls: int, completed_urls: int):
    """Update job progress"""
    supabase.table('scrape_jobs').update({
        'total_urls': total_urls,
        'completed_urls': completed_urls,
        'progress_percentage': (completed_urls / total_urls * 100) if total_urls > 0 else 0
    }).eq('id', job_id).execute()

async def subscribe_to_job_updates(job_id: int, callback):
    """Subscribe to real-time updates for a job"""
    subscription = supabase\
        .table('scrape_jobs')\
        .on('UPDATE', lambda payload: callback(payload))\
        .eq('id', job_id)\
        .subscribe()
    return subscription

async def add_job_log(job_id: int, message: str, level: str = 'INFO'):
    """Add a log entry for the entire job"""
    try:
        result = supabase.table('job_logs').insert({
            'job_id': job_id,
            'log_message': message,
            'log_level': level,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        return result
    except Exception as e:
        print(f"Error adding job log: {str(e)}")
        # Fall back to URL-based logging
        job_result = supabase.table('scrape_jobs')\
            .select('job_urls(id)')\
            .eq('id', job_id)\
            .execute()
        if job_result.data and job_result.data[0]['job_urls']:
            first_url = job_result.data[0]['job_urls'][0]
            await add_log(
                job_url_id=first_url['id'],
                message=f"[JOB LOG] {message}",
                level=level
            ) 