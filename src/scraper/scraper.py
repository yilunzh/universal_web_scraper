import time
import csv
import asyncio
import aiohttp
from typing import Dict, List, Any
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from langsmith import traceable
from firecrawl import FirecrawlApp
from src.config.settings import MAX_TOKEN, FIRECRAWL_API_KEY
import instructor
from openai import AsyncOpenAI
from src.models.data_models import DataPoints
from pathlib import Path

# Initialize OpenAI client with instructor for async operations
client = instructor.patch(AsyncOpenAI())

# Load manufacturer names from CSV
def load_manufacturer_names() -> Dict[int, str]:
    """Load manufacturer codes and names from CSV."""
    manufacturer_names = {}
    csv_path = Path("data/input/manufacturer_code.csv")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = int(row['manufacturer_code'])
            name = row['manufacturer_name']
            manufacturer_names[code] = name
    return manufacturer_names

# Get manufacturer name from code
def get_manufacturer_name(code: int) -> str:
    """Get the correct manufacturer name for a given code."""
    names = load_manufacturer_names()
    return names.get(code, "Unknown")

@retry(
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(3)
)
async def scrape_url_content(url: str) -> Dict:
    """Scrape content from a URL with retries"""
    try:
        print(f"Scraping URL: {url}")
        response = firecrawl.scrape(url)
        return {"content": response.text, "error": None}
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {"content": None, "error": str(e)}

async def process_single_url(url: str, data_points: List[Dict], semaphore: asyncio.Semaphore) -> Dict:
    """Process a single URL with rate limiting"""
    async with semaphore:
        try:
            result = await scrape_url_content(url)
            if result["error"]:
                return {"error": result["error"]}
            
            content = result["content"]
            return await extract_data_from_content(content, data_points, [], url)
            
        except Exception as e:
            return {"error": str(e)}

async def process_urls(urls: List[str], data_points: List[Dict]) -> Dict:
    """Process multiple URLs concurrently with rate limiting"""
    try:
        # Process first URL immediately
        if len(urls) == 1:
            # Create a semaphore for single URL
            semaphore = asyncio.Semaphore(1)
            result = await process_single_url(urls[0], data_points, semaphore)
            return {
                "value": [result] if "error" not in result else [],
                "errors": [{"url": urls[0], "error": result["error"]}] if "error" in result else None
            }

        # For multiple URLs, process concurrently
        MAX_CONCURRENT = 5  # Adjust based on API limits
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        # Create and start task for each URL
        for url in urls:
            asyncio.create_task(
                process_single_url(url, data_points, semaphore)
            )

        # Return immediately
        return {"message": "Processing started"}

    except Exception as e:
        print(f"Error in process_urls: {e}")
        return {"error": str(e)}

@traceable(run_type="tool", name="Extract Data")
async def extract_data_from_content(content: str, data_points: List[Dict], links_scraped: List[str], url: str) -> Dict:
    """Extract structured data from parsed content using the GPT model."""
    try:
        # Get manufacturer code from URL
        mfr_code = int(url.split('_')[0].split('/')[-1])
        correct_name = get_manufacturer_name(mfr_code)

        # Create a dynamic model based on the data points
        fields = {}
        for point in data_points:
            if point["name"] == "manufacturers":
                fields[point["name"]] = (List[Dict], point["description"])

        # Extract data using the GPT model asynchronously
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=DataPoints,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from text."},
                {"role": "user", "content": f"Extract the following information from this content: {content}"}
            ]
        )

        # Get the data and add reference
        extracted_data = response.model_dump()
        
        # Add reference URL and check manufacturer name
        if "manufacturers" in extracted_data and isinstance(extracted_data["manufacturers"], list):
            for manufacturer in extracted_data["manufacturers"]:
                manufacturer["reference"] = url
                # Only override if names don't match
                if manufacturer.get("manufacturer_name") != correct_name:
                    print(f"Correcting manufacturer name from '{manufacturer.get('manufacturer_name')}' to '{correct_name}'")
                    manufacturer["manufacturer_name"] = correct_name

        return extracted_data

    except Exception as e:
        print(f"Error extracting data: {e}")
        return {"error": str(e)}