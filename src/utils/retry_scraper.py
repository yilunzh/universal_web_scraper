from tenacity import retry, wait_exponential, stop_after_attempt
from src.scraper.scraper import extract_data_from_content
from src.scraper.async_scraper import process_urls

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
async def retry_scrape_url(url: str, data_points: List[Dict]) -> Dict:
    """Retry scraping a single URL with exponential backoff"""
    result = await process_urls([url], data_points)
    if 'error' in result:
        raise Exception(f"Failed to scrape {url}: {result['error']}")
    return result 