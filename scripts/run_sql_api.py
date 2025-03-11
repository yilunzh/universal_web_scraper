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
    # Check for PORT (used by Render and other cloud providers) first
    port = int(os.environ.get("PORT", os.environ.get("API_PORT", 8000)))
    
    # In production, bind to 0.0.0.0
    host = "0.0.0.0"
    
    # Disable reload in production
    # Render sets PYTHON_ENV to 'production' automatically
    reload_mode = os.environ.get("PYTHON_ENV", "development") != "production"
    
    print(f"Starting FastAPI server on {host}:{port} (reload: {reload_mode})...")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=reload_mode) 