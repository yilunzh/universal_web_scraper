

This document describes the **dependencies** for our Python + FastAPI Universal Web Scraper and provides a recommended **file/folder structure**. The scraper uses **Firecrawl** for scraping, **Pydantic** for data modeling, and **Supabase** for database storage.

## 1. Python Dependencies

Below is a minimal list of Python packages required for this project. You can copy these lines into a `requirements.txt` file or install them directly:

```txt
fastapi==0.95.2
uvicorn==0.22.0
pydantic==1.10.7
httpx==0.24.0  # or aiohttp, if Firecrawl depends on it
firecrawl==<VERSION>  # Replace with the correct version
supabase==0.0.0  # Replace with the correct version of the Supabase client
python-dotenv==1.0.0  # For loading .env environment variables
```

**Note**: Versions are examples. Please adjust them to match the latest stable releases or your specific environment needs.

### Optional Packages

- **pytest** or **unittest** for testing (`pytest==7.2.0`, for example)
- **requests** if you need any synchronous HTTP calls
- **celery** or **RQ** if you need advanced background task management (instead of native `asyncio`)

## 2. Environment Variables

Create a `.env` file in the **project root** to store secrets and environment variables. For example:

```env
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<your-supabase-service-role-key>
```

**Important**: Add `.env` to your `.gitignore` to avoid committing sensitive information.

## 3. Project Folder Structure

Below is a recommended file/folder structure. It separates configuration, database access, scraping logic, data models (Pydantic), and API routes (FastAPI endpoints).

```
my_universal_scraper/
├── README.md
├── requirements.txt
├── requirements.md  # (This file: describing dependencies & structure)
├── .gitignore
├── .env  # Environment variables (Supabase, etc.)
├── app/
│   ├── main.py  # Main entry point for the FastAPI app
│   ├── config.py  # Config (loads env vars, includes global settings)
│   ├── chat_interface.py  # FastAPI routes for chat-like user input
│   ├── status_dashboard.py  # FastAPI routes for job status & history
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── base.py  # Core logic for scheduling & orchestrating async tasks
│   │   ├── scraping.py  # Wrapper functions integrating Firecrawl for scraping
│   │   └── data_extractors.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── job_models.py  # Pydantic models for requests, job statuses
│   │   └── data_models.py  # Pydantic models for scraped data
│   └── db/
│       ├── __init__.py
│       ├── supabase_client.py  # Connects to Supabase, handles DB operations
│       └── db_utils.py  # Helper functions for DB tasks
├── tests/
│   ├── test_tasks.py
│   ├── test_endpoints.py
│   └── test_db.py
└── docker-compose.yml  # Optional: if you want to containerize or run local Supabase
```

### Explanation of Key Files

1. **`app/main.py`**
   - Initializes the FastAPI application and includes your routes

2. **`app/config.py`**
   - Loads environment variables via `python-dotenv` or Pydantic's `BaseSettings`

3. **`app/chat_interface.py`**
   - FastAPI routes that handle chat-like requests. Users can submit a single URL or a range of URLs
   - If input is ambiguous, can prompt for clarification

4. **`app/status_dashboard.py`**
   - Routes that display job progress, status of each scrape, and history of past jobs

5. **`app/tasks/base.py`**
   - Orchestrates asynchronous scraping tasks using `asyncio`
   - Manages job states (pending, in progress, completed, failed) and logs events or errors to the database

6. **`app/tasks/scraping.py`**
   - Calls **Firecrawl** to fetch and parse page content asynchronously
   - Passes the results to data extractor functions or directly into Pydantic models

7. **`app/tasks/data_extractors.py`**
   - Helper functions that parse specific data points (e.g., `title`, `author`, `content`) from raw HTML/JSON

8. **`app/models/job_models.py`**
   - Pydantic models describing a "job request" (e.g., single URL or range of pages) and job status updates

9. **`app/models/data_models.py`**
   - Pydantic models for the final structured data (e.g., `title`, `author`, `date`, `content`) to be stored in Supabase

10. **`app/db/supabase_client.py`**
    - Connects to your Supabase project and provides CRUD operations for job status and scraped data

11. **`app/db/db_utils.py`**
    - Utility functions for database tasks, queries, or error handling

12. **`tests/`**
    - Contains unit/integration tests to validate your scraping logic, endpoints, and DB interactions

## 4. Running the Application

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   - Create/edit your `.env` to include Supabase credentials (and any other settings)
   - Ensure `.env` is not tracked by version control

3. **Run the FastAPI app**:
   ```bash
   uvicorn app.main:app --reload
   ```
   Your API will be available at http://127.0.0.1:8000.
   You can also explore the interactive docs at http://127.0.0.1:8000/docs.

4. **Submit a scraping job**:
   Send a POST request to `/chat/` (or whichever endpoint you define) with JSON like:
   ```json
   {
     "url": "https://example.com/posts",
     "start_page": 1,
     "end_page": 5
   }
   ```
   The server should respond with a job ID and initial status.

5. **Check job status**:
   - GET `/jobs/` to see all jobs
   - GET `/jobs/{job_id}` to see status of a specific job (e.g. pending, in progress, completed, error)

## 5. Future Enhancements

- **Front-end UI**: Build a minimal React/Vue/Angular or Streamlit dashboard to monitor job statuses in real time
- **Robust Task Queue**: Integrate Celery or RQ if you need advanced scheduling, retries, or distributed workers
- **Scheduling**: Add CRON-like jobs for recurring scrapes
- **Error Handling & Retries**: Improve logging, add automated retries for pages that fail
- **Authentication**: Secure your endpoints (e.g., with OAuth or JWT) if exposed publicly