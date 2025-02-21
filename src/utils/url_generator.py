import csv
from typing import List, Dict, Set
from pathlib import Path
import aiohttp
import asyncio
import requests
from tenacity import retry, wait_exponential, stop_after_attempt

async def check_url_status(url: str, cache: Set[str] = None) -> bool:
    """Check if a URL exists by making a GET request"""
    if cache is not None and url in cache:
        return True
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as response:
                exists = response.status == 200
                if exists and cache is not None:
                    cache.add(url)
                print(f"DEBUG: Checking {url} - Status: {response.status}")
                return exists
    except Exception as e:
        print(f"DEBUG: Error checking {url}: {str(e)}")
        return False

async def check_month(manufacturer_code: int, month: int, cache: Set[str] = None) -> bool:
    """Check if a month code exists for a manufacturer."""
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"
    url = base_url.format(manufacturer_code, month)
    return await check_url_status(url, cache)

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def check_url_sync(url: str, cache: Set[str] = None) -> bool:
    """Synchronous version of check_url_status using requests with retries"""
    if cache is not None and url in cache:
        return True
    
    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        exists = response.status_code == 200
        if exists and cache is not None:
            cache.add(url)
        print(f"DEBUG: Checking {url} - Status: {response.status_code}")
        return exists
    except Exception as e:
        print(f"DEBUG: Error checking {url}: {str(e)}")
        raise  # Let tenacity handle the retry

def check_month_sync(manufacturer_code: int, month: int, cache: Set[str] = None) -> bool:
    """Synchronous version of check_month"""
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"
    url = base_url.format(manufacturer_code, month)
    return check_url_sync(url, cache)

def find_first_valid_month_code(manufacturer_code: int, min_month: int) -> int:
    """Find first valid month code using binary search."""
    print(f"Finding first valid month for manufacturer {manufacturer_code}")
    cache = set()
    
    # Ensure min_month is at least 1
    min_month = max(1, min_month)
    print(f"Starting binary search with left={min_month}, right=86")
    
    # Binary search
    left = min_month
    right = 86  # Maximum possible month
    
    # If no valid months found in range, return 1
    if not check_month_sync(manufacturer_code, right, cache):
        print(f"No valid months found up to {right}, returning 1")
        return 1
    
    while left < right:
        mid = (left + right) // 2
        print(f"Checking month {mid}...")
        if check_month_sync(manufacturer_code, mid, cache):
            print(f"Month {mid} exists, looking earlier (right=mid)")
            right = mid
        else:
            print(f"Month {mid} doesn't exist, looking later (left=mid+1)")
            left = mid + 1
    
    print(f"Binary search finished at month {left}")
    return max(1, left)

def find_last_valid_month_code(manufacturer_code: int, max_month: int) -> int:
    """Find last valid month code using binary search."""
    print(f"Finding last valid month for manufacturer {manufacturer_code} with max {max_month}")
    cache = set()
    
    # Check if any data exists
    if not check_month_sync(manufacturer_code, 1, cache):
        print("No data exists for this manufacturer")
        return 1
    
    # Binary search
    left = 1
    right = max_month
    last_valid = 1  # Keep track of last valid month found
    
    print(f"Starting binary search between {left} and {right}")
    while left <= right:
        mid = (left + right) // 2
        print(f"Checking month {mid}...")
        
        if check_month_sync(manufacturer_code, mid, cache):
            print(f"Month {mid} valid, checking if it's the boundary")
            last_valid = mid
            
            # Check if this is the boundary
            if not check_month_sync(manufacturer_code, mid + 1, cache):
                print(f"Found exact boundary at {mid}")
                return mid
                
            # Not the boundary, look in upper half
            left = mid + 1
        else:
            # Invalid month, look in lower half
            print(f"Month {mid} invalid, looking lower")
            right = mid - 1
    
    print(f"Found last valid month: {last_valid}")
    return last_valid

def generate_urls_from_codes(manufacturer_csv_path: str, month_csv_path: str) -> List[str]:
    """Generate URLs by combining manufacturer codes and month codes from CSV files."""
    urls = []
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"

    try:
        # Read files
        with open(manufacturer_csv_path, 'r', encoding='utf-8') as f:
            manufacturer_reader = csv.DictReader(f)
            manufacturer_codes = [int(row['manufacturer_code']) for row in manufacturer_reader]

        with open(month_csv_path, 'r', encoding='utf-8') as f:
            month_reader = csv.DictReader(f)
            month_codes = [int(row['month_year_code']) for row in month_reader]

        # Generate URLs
        for mfr_code in manufacturer_codes:
            if mfr_code in range(62,63):
                print(f"\nProcessing manufacturer {mfr_code}")
                first_valid_month = find_first_valid_month_code(mfr_code, 1)
                last_valid_month = find_last_valid_month_code(mfr_code, max(month_codes))
                print(f"Valid month range: {first_valid_month} to {last_valid_month}")
                
                for month_code in range(first_valid_month, last_valid_month + 1):
                    url = base_url.format(mfr_code, month_code)
                    urls.append(url)
                    print(f"Added URL: {url}")

        print(f"\nGenerated {len(urls)} URLs")
        return urls

    except Exception as e:
        print(f"Error: {e}")
        return [] 