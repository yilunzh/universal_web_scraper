import json
import time
from typing import List, Dict
import asyncio
from langsmith import traceable
from .state import ScrapingState
from src.utils.validation import validate_entry
from src.utils.file_operations import save_json_pretty, export_to_csv
from src.utils.notifications import send_mac_notification
from .scraper import extract_data_from_content
from firecrawl import FirecrawlApp
from src.config.settings import MAX_TOKEN
from pathlib import Path
from src.config.constants import OUTPUT_DIR

@traceable(run_type="chain", name="Async Scrape")
async def async_scrape(url: str, data_points: List[Dict], links_scraped: List[str], semaphore: asyncio.Semaphore) -> Dict:
    """
    Asynchronously scrape a given URL and extract structured data.
    
    Args:
        url (str): The URL to scrape
        data_points (List[Dict]): The list of data points to extract
        links_scraped (List[str]): List of already scraped links
        semaphore (asyncio.Semaphore): Semaphore to limit concurrent requests
        
    Returns:
        Dict: The extracted structured data or an error message
    """
    app = FirecrawlApp()
    
    try:
        # Add small delay between requests
        await asyncio.sleep(1)
        
        async with semaphore:  # Limit concurrent requests
            try:
                async def async_scrape_url():
                    # Add delay between requests to avoid overwhelming the server
                    await asyncio.sleep(2)
                    
                    scraped_data = app.scrape_url(url)
                    if scraped_data["metadata"]["statusCode"] == 200:
                        markdown = scraped_data["markdown"][: (MAX_TOKEN * 2)]
                        links_scraped.append(url)
                        return await extract_data_from_content(markdown, data_points, links_scraped, url)
                    else:
                        status_code = scraped_data["metadata"]["statusCode"]
                        if status_code == 404:
                            return {"error": f"Page not found (404) for URL: {url}"}
                        raise Exception(f"HTTP {status_code} error")

                # Run with timeout using asyncio
                try:
                    return await asyncio.wait_for(
                        async_scrape_url(),
                        timeout=120  # 120 seconds timeout
                    )
                except asyncio.TimeoutError:
                    print(f"Timeout while scraping URL {url}")
                    return {"error": "Operation timed out"}

            except Exception as e:
                print(f"Error scraping URL {url}")
                print(f"Exception: {e}")
                return {"error": str(e)}

    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return {"error": str(e)}

@traceable(run_type="chain", name="Process single URL")
async def process_url(url: str, data_points: List[Dict], filename: str, state: ScrapingState) -> None:
    """
    Process a single URL with proper error handling.
    
    Args:
        url (str): The URL to process
        data_points (List[Dict]): The data points to extract
        filename (str): The output filename
        state (ScrapingState): Shared state for the scraping process
    """
    print(f"Processing {url}")
    try:
        data = await async_scrape(url, data_points, state.links_scraped, state.semaphore)
        
        if isinstance(data, dict):
            if "manufacturers" in data and isinstance(data["manufacturers"], list):
                manufacturer_data = data["manufacturers"][0]
                try:
                    if validate_entry(manufacturer_data, url):
                        manufacturer_data["reference"] = url
                        state.all_data.extend([manufacturer_data])
                        save_json_pretty(state.all_data, filename)
                        state.results["successful"].append(url)
                        print(f"Successfully processed {url}")
                    else:
                        state.results["failed"].append({"url": url, "reason": "Failed validation"})
                except Exception as save_error:
                    print(f"Error saving data for {url}: {str(save_error)}")
                    state.results["failed"].append({"url": url, "reason": f"Save error: {str(save_error)}"})
            else:
                error_msg = data.get("error", "Invalid data format - missing manufacturers data")
                state.results["failed"].append({"url": url, "reason": error_msg})
                print(f"Invalid data format for {url}: {data}")
        else:
            state.results["failed"].append({"url": url, "reason": f"Invalid response format: {type(data)}"})
            print(f"Invalid response type for {url}: {type(data)}, Data: {data}")
        
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        state.results["failed"].append({"url": url, "reason": str(e)})

@traceable(run_type="chain", name="Process URLs")
async def process_urls(urls: List[str], data_points: List[Dict], filename: str) -> None:
    """
    Process multiple URLs concurrently with a limit on concurrent requests.
    """
    state = ScrapingState()
    
    # Create tasks for all URLs
    tasks = [process_url(url, data_points, filename, state) for url in urls]
    
    # Process URLs concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Generate summary report
    print("\n=== Scraping Summary ===")
    print(f"Total URLs processed: {len(urls)}")
    print(f"Successful: {len(state.results['successful'])}")
    print(f"Failed: {len(state.results['failed'])}")
    
    if state.results["failed"]:
        print("\nFailed URLs and reasons:")
        for failure in state.results["failed"]:
            print(f"URL: {failure['url']}")
            print(f"Reason: {failure['reason']}")
            print("-" * 50)
    
    print(f"\nTotal records collected: {len(state.all_data)}")
    export_to_csv(filename, filename.replace('.json', '.csv'))
    
    # Save the results report
    report_filename = OUTPUT_DIR / f"scraping_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(state.results, f, indent=4, ensure_ascii=False)
    print(f"\nDetailed report saved to {report_filename}")
    
    # Send notification
    send_mac_notification(
        "Web Scraping Complete", 
        f"Collected {len(state.all_data)} records. Success: {len(state.results['successful'])}, Failed: {len(state.results['failed'])}"
    ) 