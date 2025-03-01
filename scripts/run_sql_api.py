import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()
load_dotenv(project_root / '.env.local')  # Load .env.local which should override .env

import uvicorn

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("API_PORT", 8000))
    
    print(f"Starting FastAPI server on port {port}...")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True) 