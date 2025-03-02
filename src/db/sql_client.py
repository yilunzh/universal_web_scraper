import os
import traceback
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import json

# Import the existing Supabase client
from .supabase_client import get_supabase_client

# Load environment variables
load_dotenv()
load_dotenv('.env.local')  # Load .env.local which should override .env

async def execute_sql_query(
    query: str, 
    limit: int = 1000
) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Execute a SQL query against the Supabase database using the built-in exec_sql function.
    
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
    
    try:
        # Format the query: remove trailing semicolons and whitespace
        formatted_query = query.strip()
        if formatted_query.endswith(';'):
            formatted_query = formatted_query[:-1]
        
        # Add LIMIT if it doesn't exist
        if "limit" not in cleaned_query:
            formatted_query = formatted_query + f" LIMIT {limit}"
        
        print(f"Executing query: {formatted_query}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Call the exec_sql RPC function
        try:
            response = supabase.rpc('exec_sql', {'sql': formatted_query}).execute()
            
            # In the newer Supabase client, we need to handle the response differently
            # Get the data from the response
            data = response.data
            
            # If data is not a list or is empty, handle appropriately
            if not data:
                return [], [], None
            
            if isinstance(data, dict) and 'error' in data:
                return [], [], f"Query error: {data['error']}"
            
            # If data is not a list (e.g., it's a dictionary with information)
            if data and not isinstance(data, list):
                # Try to convert to list if it's not already
                data = [data]
                
            # Extract column names from the first row
            columns = list(data[0].keys()) if data and len(data) > 0 else []
            
            print(f"Query returned {len(data)} rows")
            return data, columns, None
            
        except Exception as e:
            # Check if this is a dictionary with error information
            if hasattr(e, 'message'):
                return [], [], f"Database error: {e.message}"
            return [], [], f"Error executing RPC: {str(e)}"
    
    except Exception as e:
        error_message = f"Error executing query: {str(e)}\n{traceback.format_exc()}"
        return [], [], error_message