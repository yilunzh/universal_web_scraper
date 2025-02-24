#!/usr/bin/env python3
import requests
import argparse
from typing import List
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def submit_manufacturer_job(
    manufacturer_codes: List[str],
    job_name: str = None,
    start_month: str = None,
    end_month: str = None,
    api_url: str = "http://localhost:8000"
) -> dict:
    """Submit a manufacturer scraping job to the API."""
    
    # Generate default job name if none provided
    if not job_name:
        job_name = f"Manufacturers {','.join(manufacturer_codes)} Scrape"
    
    # Prepare request data
    data = {
        "job_name": job_name,
        "manufacturer_codes": manufacturer_codes
    }
    
    # Add optional parameters if provided
    if start_month:
        data["start_month_code"] = start_month
    if end_month:
        data["end_month_code"] = end_month
        
    # Submit request
    print(f"\nSubmitting job for manufacturers: {', '.join(manufacturer_codes)}")
    response = requests.post(
        f"{api_url}/api/jobs/manufacturer",
        json=data
    )
    
    # Handle response
    if response.status_code == 200:
        result = response.json()
        print("\nJob created successfully!")
        print(f"Job ID: {result['job_id']}")
        print(f"Total URLs: {result['total_urls']}")
        print("\nURLs per manufacturer:")
        for mfr, count in result['urls_per_manufacturer'].items():
            print(f"- Manufacturer {mfr}: {count} URLs")
        return result
    else:
        print(f"\nError creating job: {response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Submit a manufacturer scraping job')
    parser.add_argument(
        'manufacturers',
        nargs='+',
        help='One or more manufacturer codes (e.g., 88 89)'
    )
    parser.add_argument(
        '--name',
        help='Optional job name'
    )
    parser.add_argument(
        '--start',
        help='Optional start month code'
    )
    parser.add_argument(
        '--end',
        help='Optional end month code'
    )
    parser.add_argument(
        '--api',
        default='http://localhost:8000',
        help='API URL (default: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    result = submit_manufacturer_job(
        manufacturer_codes=args.manufacturers,
        job_name=args.name,
        start_month=args.start,
        end_month=args.end,
        api_url=args.api
    )
    
    if result:
        print("\nUse this command to check job status:")
        print(f"curl {args.api}/api/jobs/{result['job_id']}")

if __name__ == "__main__":
    main() 