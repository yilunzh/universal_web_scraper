import os
import asyncio
from pathlib import Path
from src.scraper.async_scraper import process_urls
from src.models.data_models import DataPoints
from src.utils.url_generator import generate_urls_from_codes
from src.config.logging_config import logger
from src.config.constants import PROJECT_ROOT, DATA_DIR, INPUT_DIR, OUTPUT_DIR

def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [DATA_DIR, INPUT_DIR, OUTPUT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

def check_required_files():
    """Check if required input files exist."""
    required_files = {
        'manufacturer_code.csv': INPUT_DIR / 'manufacturer_code.csv',
        'month_code.csv': INPUT_DIR / 'month_code.csv'
    }
    
    missing_files = []
    for name, path in required_files.items():
        if not path.exists():
            missing_files.append(name)
    
    if missing_files:
        raise FileNotFoundError(
            f"Missing required files: {', '.join(missing_files)}. "
            f"Please ensure they are present in {INPUT_DIR}"
        )

def main():
    """Main execution function that handles the web scraping process."""
    try:
        logger.info("Starting web scraping process")
        
        # Ensure directory structure
        ensure_directories()
        logger.info("Directory structure verified")
        
        # Check required files
        check_required_files()
        logger.info("Required input files found")
        
        # Generate URLs to process
        manufacturer_csv = INPUT_DIR / 'manufacturer_code.csv'
        month_csv = INPUT_DIR / 'month_code.csv'
        urls = generate_urls_from_codes(str(manufacturer_csv), str(month_csv))
        logger.info(f"Generated {len(urls)} URLs to process")
        
        # Initialize data points from Pydantic model
        data_keys = list(DataPoints.__fields__.keys())
        data_fields = DataPoints.__fields__
        data_points = [{"name": key, "value": None, "reference": None, "description": data_fields[key].description} for key in data_keys]
        
        # Set up output filename
        entity_name = 'china_monthly_auto_sales_data_v2'
        filename = OUTPUT_DIR / f"{entity_name}.json"
        
        # Run the async scraping
        asyncio.run(process_urls(urls, data_points, str(filename)))
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.exception("An unexpected error occurred")
        return 1
    
    logger.info("Scraping process completed successfully")
    return 0

if __name__ == "__main__":
    exit(main()) 