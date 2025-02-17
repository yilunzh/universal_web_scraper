import time
from typing import Dict, List, Any
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from langsmith import traceable
from firecrawl import FirecrawlApp
from src.config.settings import MAX_TOKEN, FIRECRAWL_API_KEY
import instructor
from openai import AsyncOpenAI
from src.models.data_models import DataPoints

# Initialize OpenAI client with instructor for async operations
client = instructor.patch(AsyncOpenAI())

@traceable(run_type="tool", name="Extract Data")
async def extract_data_from_content(content: str, data_points: List[Dict], links_scraped: List[str], url: str) -> Dict:
    """
    Extract structured data from parsed content using the GPT model.
    
    Args:
        content (str): The content to extract data from
        data_points (List[Dict]): The data points to extract
        links_scraped (List[str]): List of already scraped links
        url (str): The URL being processed
        
    Returns:
        Dict: The extracted structured data
    """
    try:
        # Create a dynamic model based on the data points
        fields = {}
        for point in data_points:
            if point["name"] == "manufacturers":
                fields[point["name"]] = (List[Dict], point["description"])

        # Extract data using the GPT model asynchronously
        response = await client.chat.completions.create(
            model="gpt-4",
            response_model=DataPoints,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from text."},
                {"role": "user", "content": f"Extract the following information from this content: {content}"}
            ]
        )

        # Get the data and add reference
        extracted_data = response.model_dump()
        
        # Add reference URL to each manufacturer in the list
        if "manufacturers" in extracted_data and isinstance(extracted_data["manufacturers"], list):
            for manufacturer in extracted_data["manufacturers"]:
                manufacturer["reference"] = url

        return extracted_data

    except Exception as e:
        print(f"Error extracting data: {e}")
        return {"error": str(e)}