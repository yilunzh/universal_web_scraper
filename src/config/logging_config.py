import logging
from pathlib import Path
import time

def setup_logging():
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'scraper_{timestamp}.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger('china_auto_sales_scraper')
    logger.setLevel(logging.INFO)
    
    return logger

# Create and export logger
logger = setup_logging() 