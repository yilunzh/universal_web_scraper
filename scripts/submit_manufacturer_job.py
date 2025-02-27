#!/usr/bin/env python3
import requests
import argparse
from typing import List
import sys
from pathlib import Path
import pandas as pd
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import config after adding project root to path
from src.config.langsmith import disable_logging as disable_langsmith_logging

# Disable LangSmith logging
disable_langsmith_logging()

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
        "manufacturer_codes": manufacturer_codes,
        "start_month_code": start_month,
        "end_month_code": end_month
    }
        
    # Submit request
    print(f"\nSubmitting job for manufacturers: {', '.join(manufacturer_codes)}")
    print(f"Month range: {start_month or 'auto'} to {end_month or 'auto'}")
    
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
        '--manufacturer-codes',
        required=False,
        nargs='+',  # Accept one or more values
        default=None,
        help='One or more manufacturer codes (e.g., "99 100" or "99,100"). If not provided, all manufacturers will be processed.'
    )
    parser.add_argument(
        '--job-name',
        help='Optional job name'
    )
    parser.add_argument(
        '--start-month',
        help='Optional start month code'
    )
    parser.add_argument(
        '--end-month',
        help='Optional end month code'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='API URL (default: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    manufacturer_codes = []
    if args.manufacturer_codes:
        # Process the list of manufacturer codes
        manufacturer_codes = []
        for code_arg in args.manufacturer_codes:
            # Handle comma-separated values within each argument
            if ',' in code_arg:
                manufacturer_codes.extend([code.strip() for code in code_arg.split(',') if code.strip()])
            else:
                if code_arg.strip():  # Only add non-empty codes
                    manufacturer_codes.append(code_arg.strip())
                
        print(f"Processing specified manufacturer codes: {', '.join(manufacturer_codes)}")
    else:
        # Process all manufacturers
        print("No manufacturer codes provided. Processing all manufacturers...")
        # Use standard pandas to read the CSV
        manufacturer_df = pd.read_csv(f"{project_root}/data/input/manufacturer_code.csv")
        manufacturer_codes = manufacturer_df['manufacturer_code'].astype(str).tolist()
        print(f"Found {len(manufacturer_codes)} manufacturer codes to process")
    
    # Filter out any empty codes
    manufacturer_codes = [code for code in manufacturer_codes if code]
    
    # Process all manufacturer codes in a single job
    if manufacturer_codes:
        print(f"Submitting job for {len(manufacturer_codes)} manufacturer codes")
        result = submit_manufacturer_job(
            manufacturer_codes=manufacturer_codes,
            job_name=args.job_name,
            start_month=args.start_month,
            end_month=args.end_month,
            api_url=args.api_url
        )
        
        if result:
            print("\nUse this command to check job status:")
            print(f"curl {args.api_url}/api/jobs/{result['job_id']}")
    else:
        print("No valid manufacturer codes to process")
    
    print("Job submission completed")

if __name__ == "__main__":
    main() 