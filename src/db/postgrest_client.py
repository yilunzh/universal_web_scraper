import os
import httpx
import json
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()
load_dotenv('.env.local')  # Load .env.local which should override .env

async def execute_postgrest_query(
    table_name: str,
    columns: List[str] = None,
    filters: Dict[str, Any] = None,
    limit: int = 1000
) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Execute a query using Supabase's PostgREST API.
    This method uses the REST-based filtering rather than raw SQL.
    
    Args:
        table_name: Name of the table to query
        columns: List of columns to select (None for all columns)
        filters: Dictionary of filters to apply (column_name -> value)
        limit: Maximum number of rows to return
    
    Returns:
        Tuple containing:
        - List of records (as dictionaries)
        - List of column names
        - Error message (if any)
    """
    try:
        # Get Supabase URL and key from environment
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            return [], [], "Missing Supabase credentials"
        
        # Make a direct HTTP request to the Supabase REST API
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "count=exact"
        }
        
        # Build the query parameters
        column_select = "*" if not columns else ",".join(columns)
        
        # Construct the endpoint URL
        endpoint = f"{supabase_url}/rest/v1/{table_name}"
        
        # Build query parameters
        params = {
            "select": column_select,
            "limit": limit
        }
        
        # Make the request
        async with httpx.AsyncClient() as client:
            # Add filters if provided
            if filters:
                for column, value in filters.items():
                    # For exact matches
                    params[column] = f"eq.{value}"
                    
            print(f"Executing PostgREST query on {table_name} with params: {params}")
            
            response = await client.get(
                endpoint,
                headers=headers,
                params=params
            )
            
            # Check for errors
            if response.status_code >= 400:
                return [], [], f"Database error: {response.status_code} - {response.text}"
            
            # Parse the response
            try:
                data = response.json()
                # Extract column names from the first row
                columns = list(data[0].keys()) if data and len(data) > 0 else []
                print(f"Query returned {len(data)} rows")
                return data, columns, None
            except json.JSONDecodeError:
                return [], [], f"Error parsing response: {response.text}"
    
    except Exception as e:
        error_message = f"Error executing query: {str(e)}\n{traceback.format_exc()}"
        return [], [], error_message

async def execute_filtered_query(
    table_name: str,
    filter_expressions: List[str], 
    limit: int = 1000
) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Execute a more complex query using Supabase's PostgREST API with custom filter expressions.
    
    Args:
        table_name: Name of the table to query
        filter_expressions: List of PostgREST filter expressions (e.g. ["year=gte.2020", "total_units_sold=gte.1000"])
        limit: Maximum number of rows to return
    
    Returns:
        Tuple containing:
        - List of records (as dictionaries)
        - List of column names
        - Error message (if any)
    """
    try:
        # Get Supabase URL and key from environment
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            return [], [], "Missing Supabase credentials"
        
        # Make a direct HTTP request to the Supabase REST API
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "count=exact"
        }
        
        # Construct the endpoint URL
        endpoint = f"{supabase_url}/rest/v1/{table_name}"
        
        # Build query parameters
        params = {
            "select": "*",
            "limit": limit
        }
        
        # Add filter expressions
        for expr in filter_expressions:
            if "=" in expr:
                key, value = expr.split("=", 1)
                params[key] = value
        
        # Make the request
        async with httpx.AsyncClient() as client:
            print(f"Executing filtered query on {table_name} with params: {params}")
            
            response = await client.get(
                endpoint,
                headers=headers,
                params=params
            )
            
            # Check for errors
            if response.status_code >= 400:
                return [], [], f"Database error: {response.status_code} - {response.text}"
            
            # Parse the response
            try:
                data = response.json()
                # Extract column names from the first row
                columns = list(data[0].keys()) if data and len(data) > 0 else []
                print(f"Query returned {len(data)} rows")
                return data, columns, None
            except json.JSONDecodeError:
                return [], [], f"Error parsing response: {response.text}"
    
    except Exception as e:
        error_message = f"Error executing query: {str(e)}\n{traceback.format_exc()}"
        return [], [], error_message 