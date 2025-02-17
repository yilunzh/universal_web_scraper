from asyncio import Semaphore
from typing import List, Dict

class ScrapingState:
    def __init__(self):
        self.links_scraped: List[str] = []
        self.all_data: List[Dict] = []
        self.results: Dict = {
            "successful": [],
            "failed": []
        }
        self.semaphore = Semaphore(5) 