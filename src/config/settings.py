import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv('.env.local')

# Constants
GPT_MODEL = "gpt-4o"
MAX_TOKEN = 100000
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

if not FIRECRAWL_API_KEY:
    raise ValueError("FIRECRAWL_API_KEY not found in environment variables") 