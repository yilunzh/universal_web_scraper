import os
import asyncpg
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()
load_dotenv('.env.local')  # Load .env.local which should override .env

async def execute_sql_direct(
    query: str,
    limit: int = 1000
) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Execute a SQL query directly against the Supabase PostgreSQL database
    using asyncpg.
    
    Args:
        query: SQL query to execute (must be a SELECT query)
        limit: Maximum number of rows to return
    
    Returns:
        Tuple containing:
        - List of records (as dictionaries)
        - List of column names
        - Error message (if any)
    """
    # Validate that this is a SELECT query for security
    cleaned_query = query.strip().lower()
    if not cleaned_query.startswith("select"):
        return [], [], "Only SELECT queries are allowed for security reasons"
    
    # Extract connection parameters from environment variables
    db_host = os.getenv("SUPABASE_DB_HOST") or os.getenv("POSTGRES_HOST")
    db_port = os.getenv("SUPABASE_DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    db_name = os.getenv("SUPABASE_DB_NAME") or os.getenv("POSTGRES_DATABASE")
    db_user = os.getenv("SUPABASE_DB_USER") or os.getenv("POSTGRES_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    
    # Check if we have all required parameters
    if not all([db_host, db_name, db_user, db_password]):
        return [], [], "Missing database connection parameters. Please check your environment variables."
    
    try:
        # Add LIMIT if it doesn't exist
        if "limit" not in cleaned_query:
            query = query.rstrip(';') + f" LIMIT {limit};"
        else:
            # Ensure query ends with semicolon
            if not query.rstrip().endswith(';'):
                query = query + ";"
                
        print(f"Executing query via direct connection: {query}")
        
        # Connect to the database
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        try:
            # Execute the query
            results = await conn.fetch(query)
            
            # Convert to list of dictionaries
            data = [dict(row) for row in results]
            
            # Extract column names from the first row
            columns = list(data[0].keys()) if data and len(data) > 0 else []
            
            print(f"Query returned {len(data)} rows")
            return data, columns, None
        finally:
            # Ensure connection is closed
            await conn.close()
    
    except Exception as e:
        error_message = f"Error executing query: {str(e)}\n{traceback.format_exc()}"
        return [], [], error_message 