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

def find_first_valid_month_code(manufacturer_code: int, min_month: int = 1) -> int:
    """
    Find the first valid month code using common points and exponential search.
    
    Args:
        manufacturer_code (int): The manufacturer code to check
        min_month (int): The minimum month to check (default: 1)
    
    Returns:
        int: The first valid month code, or -1 if none found
    """
    print(f"Finding first valid month for manufacturer {manufacturer_code}")
    cache = set()
    
    # Ensure min_month is at least 1
    min_month = max(1, min_month)
    max_search = 100  # Reasonable upper limit
    
    # First check if min_month itself is valid
    if check_month_sync(manufacturer_code, min_month, cache):
        return min_month
    
    # Try common month points as optimization (ordered from lowest to highest)
    common_points = [1, 10, 20, 30, 40, 50, 60, 70, 80, 86]
    for point in common_points:
        if min_month <= point <= max_search and check_month_sync(manufacturer_code, point, cache):
            # Found a valid month, binary search for earliest in range [min_month, point]
            return binary_search_first(manufacturer_code, min_month, point, cache)
    
    # If common points didn't work, try exponential search
    bound = 1
    current = min_month
    while current + bound < max_search:
        if check_month_sync(manufacturer_code, current + bound, cache):
            # Found a valid month, binary search for the first valid in range
            return binary_search_first(manufacturer_code, current, current + bound, cache)
        
        current = current + bound
        bound *= 2
        
        # Don't exceed our max search limit
        if current + bound >= max_search:
            # Try one last check at max_search
            if check_month_sync(manufacturer_code, max_search, cache):
                return binary_search_first(manufacturer_code, current, max_search, cache)
            break
    
    # Linear search fallback
    print("Common points and exponential search failed, trying full scan")
    for month in range(min_month, max_search):
        if check_month_sync(manufacturer_code, month, cache):
            return month
    
    print(f"No valid months found for manufacturer {manufacturer_code}")
    return -1

def binary_search_first(manufacturer_code: int, left: int, right: int, cache: set) -> int:
    """Binary search to find the first valid month in a range."""
    first_valid = right  # Initialize to the known valid month
    
    while left <= right:
        mid = (left + right) // 2
        if check_month_sync(manufacturer_code, mid, cache):
            first_valid = mid  # This could be the first valid month
            right = mid - 1  # Look for earlier valid months
        else:
            left = mid + 1  # Look in upper half
            
    return first_valid

def find_last_valid_month_code(manufacturer_code: int, max_month: int = 86) -> int:
    """
    Find the last valid month code using common points and exponential search.
    
    Args:
        manufacturer_code (int): The manufacturer code to check
        max_month (int): The maximum month to check (default: 86)
    
    Returns:
        int: The last valid month code, or -1 if none found
    """
    print(f"Finding last valid month for manufacturer {manufacturer_code}")
    cache = set()
    
    # First check if max_month itself is valid
    if check_month_sync(manufacturer_code, max_month, cache):
        return max_month
    
    # Try common month points as optimization (ordered from highest to lowest)
    common_points = [86, 80, 70, 60, 50, 40, 30, 20, 10, 1]
    for point in sorted(common_points, reverse=True):
        if point <= max_month and check_month_sync(manufacturer_code, point, cache):
            # Found a valid month, binary search for latest in range [point, max_month-1]
            return binary_search_last(manufacturer_code, point, max_month - 1, cache)
    
    # If common points didn't work, try exponential search
    bound = 1
    current = max_month
    while current - bound > 0:
        if check_month_sync(manufacturer_code, current - bound, cache):
            # Found a valid month, binary search for the last valid in range
            return binary_search_last(manufacturer_code, current - bound, current - 1, cache)
        
        current = current - bound
        bound *= 2
        
        # Don't go below 1
        if current - bound <= 0:
            # Try one last check at month 1
            if check_month_sync(manufacturer_code, 1, cache):
                return binary_search_last(manufacturer_code, 1, current - 1, cache)
            break
    
    # Linear search fallback
    print("Common points and exponential search failed, trying full scan")
    for month in range(max_month, 0, -1):
        if check_month_sync(manufacturer_code, month, cache):
            return month
    
    print(f"No valid months found for manufacturer {manufacturer_code}")
    return -1

def binary_search_last(manufacturer_code: int, left: int, right: int, cache: set) -> int:
    """Binary search to find the last valid month in a range."""
    last_valid = left  # Initialize to the known valid month
    
    while left <= right:
        mid = (left + right) // 2
        if check_month_sync(manufacturer_code, mid, cache):
            last_valid = mid  # This could be the last valid month
            left = mid + 1  # Look for later valid months
        else:
            right = mid - 1  # Look in lower half
            
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

# ... existing code ...

# validation code
# first_month = find_first_valid_month_code(120, min_month=1)
# print(first_month)
# last_month = find_last_valid_month_code(120, max_month=86)
# print(last_month)
