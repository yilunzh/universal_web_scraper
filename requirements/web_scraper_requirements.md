You are an expert AI software engineer. 
Please build a Universal Web Scraper tool with the following specifications:

1. **Input Handling**:
   - It should accept both a single URL and a range of URLs (i.e., multiple pages of a specific URL pattern).
   - If a range of URLs is given, generate all the URLs and queue them for scraping asynchronously.

2. **Asynchronous Scraping**:
   - Integrate the Firecrawl library to perform the web requests and parsing.
   - Use an asynchronous framework or library (e.g., asyncio, aiohttp, or relevant Firecrawl async features) to handle multiple scrape jobs in parallel.

3. **Data Extraction with Pydantic**:
   - Define one or more Pydantic models representing the structured data fields we want from each page. 
   - Example fields might include: 
     - `title: str`
     - `content: str`
     - `published_date: datetime`
     - `author: str`
   - Map the scraped data to these models for clean validation and transformation.

4. **Supabase Integration**:
   - Create or connect to a Supabase project and set up a table (e.g., `scraped_data`) to store the structured data.
   - Each row in the table should include the full structured data (all relevant fields), as well as metadata (like `url`, `timestamp`, and `status`).

5. **Chat Interface**:
   - Provide a basic chat-like interface (could be CLI-based or a minimal web UI) that allows the user to:
     - Enter a URL or range of URLs to scrape.
     - If the user input is ambiguous, ask clarifying questions (e.g., “Which page range do you want?”).
     - Confirm the scraping job before proceeding.

6. **Status/Progress & History Interface**:
   - Implement a simple web or CLI dashboard to track:
     - Current jobs in progress with their statuses (pending, scraping, completed, errored).
     - Historical jobs with timestamps, final status, and logs or error messages.
   - This can be as simple as a table or list that updates when each scraping job starts and finishes.

7. **Error Handling & Logging**:
   - For each URL, capture success/failure status. 
   - Log errors (e.g., network timeouts, parsing errors) and continue with the remaining URLs.
   - Provide a summary of any errors or skipped pages in the dashboard.

8. **Code Implementation**:
   - Use Python for the core code.
   - Rely on asyncio (or a similar async framework) to schedule the scraping tasks concurrently.
   - Integrate Firecrawl for the actual fetching and parsing logic.
   - Use Pydantic for data validation and schema enforcement.
   - Save the validated data into Supabase.

9. **Final Deliverables**:
   - A self-contained Python codebase or set of scripts that run the universal web scraper.
   - A minimal interface (could be Streamlit, FastAPI endpoints, or a command-line interface) for:
     - Submitting scraping jobs via chat-like prompts.
     - Viewing job statuses and historical results.

Please follow best practices for asynchronous programming, error handling, and code organization. 
