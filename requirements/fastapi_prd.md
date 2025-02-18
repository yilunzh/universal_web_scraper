**Goal**  
Transform the existing repository into a FastAPI application that provides three endpoints:

1. **POST** `/scraper/start`: Start a new scraping job.
2. **GET** `/scraper/status/{job_id}`: Check the status of a specific job.
3. **GET** `/scraper/results/{job_id}`: Fetch the results of a completed job.

**Instructions**  

1. **Create a new directory**: `src/api/`  
2. **Inside `src/api/`, create a file** named `main.py`.  
3. **In `main.py`**, define a FastAPI application with:
   - A global dictionary or similar structure to store jobs and their statuses/results.
   - A `POST /scraper/start` endpoint that:
     - Accepts JSON input with scraping parameters (e.g., URL, month_code, manufacturer_code).
     - Generates a unique `job_id`.
     - Initializes the job state (e.g., "queued").
     - Launches the scraper in a background task.  
   - A `GET /scraper/status/{job_id}` endpoint that:
     - Returns the status of the requested job (`queued`, `running`, `completed`, etc.).  
   - A `GET /scraper/results/{job_id}` endpoint that:
     - Returns the results once the job is marked as `completed`.
   - A background function that:
     - Updates the job state to `running`.
     - **Calls the existing scraper logic** (found in `src/scraper/scraper.py` or similar).
     - On completion, saves or returns the data to the job’s record.
     - Marks the job as `completed`.  

4. **Refactor** the existing scraper code (e.g., in `src/scraper/`) so it can be called programmatically:
   - A function like `def run_scraper(url, month_code, manufacturer_code) -> dict:` 
     that returns the final data (dictionary or list of records) instead of writing directly to file.  

5. **Tie it all together**:  
   - When `POST /scraper/start` is called, create a `job_id`, store initial state, and start the background task.  
   - The background task should import and call `run_scraper` from the existing scraper code.  
   - Once scraping is done, store the results in memory (or optionally in the `data/output` folder **and** a database like Supabase if desired).  

6. **Example `main.py`** (you can adapt as needed):

```python
# src/api/main.py

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
import time
# from src.scraper.scraper import run_scraper  # Uncomment once you refactor your scraper

app = FastAPI()

# In-memory storage for jobs
jobs = {}

# Pydantic model for request data
class ScraperRequest(BaseModel):
    url: str
    month_code: str
    manufacturer_code: str

@app.post("/scraper/start")
def start_scraper(request: ScraperRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "queued",
        "results": None
    }
    # Launch the scraper as a background task
    background_tasks.add_task(run_scraper_job, job_id, request)
    return {"job_id": job_id, "status": "queued"}

def run_scraper_job(job_id: str, request: ScraperRequest):
    jobs[job_id]["status"] = "running"

    # -----------------------------
    # Replace the lines below with a call to your actual scraper function, e.g.:
    # results = run_scraper(
    #     url=request.url,
    #     month_code=request.month_code,
    #     manufacturer_code=request.manufacturer_code,
    # )
    # The snippet below is just a placeholder to simulate scraping time.
    time.sleep(5)
    results = {
        "url": request.url,
        "month_code": request.month_code,
        "manufacturer_code": request.manufacturer_code,
        "data": ["sample", "scraped", "values"]
    }
    # -----------------------------

    # Store results and mark job complete
    jobs[job_id]["results"] = results
    jobs[job_id]["status"] = "completed"

@app.get("/scraper/status/{job_id}")
def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    return {
        "job_id": job_id,
        "status": job["status"]
    }

@app.get("/scraper/results/{job_id}")
def get_job_results(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    if job["status"] != "completed":
        return {"error": "Job not completed yet"}
    return {
        "job_id": job_id,
        "results": job["results"]
    }
