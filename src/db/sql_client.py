import os
import traceback
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import httpx
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

# This is a stub function that always returns False
async def check_sql_function_exists() -> bool:
    return False

# Example RPC function implementations

async def call_manufacturer_stats_rpc(manufacturer_name: str, year: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Example of calling an RPC function in Supabase.
    
    This assumes you have created the following PostgreSQL function in your Supabase instance:
    
    ```sql
    CREATE OR REPLACE FUNCTION get_manufacturer_stats(p_manufacturer text, p_year integer)
    RETURNS TABLE (
        manufacturer_name text,
        year integer,
        total_annual_sales bigint,
        peak_month integer,
        peak_month_sales integer,
        model_count bigint
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        WITH monthly_sales AS (
            SELECT 
                month,
                SUM(total_units_sold) as month_total
            FROM china_auto_sales
            WHERE manufacturer_name = p_manufacturer AND year = p_year
            GROUP BY month
        ),
        model_counts AS (
            SELECT COUNT(DISTINCT model_name) as unique_models
            FROM china_auto_sales
            WHERE manufacturer_name = p_manufacturer AND year = p_year
        )
        SELECT 
            p_manufacturer as manufacturer_name,
            p_year as year,
            SUM(month_total) as total_annual_sales,
            (SELECT month FROM monthly_sales ORDER BY month_total DESC LIMIT 1) as peak_month,
            (SELECT MAX(month_total) FROM monthly_sales) as peak_month_sales,
            (SELECT unique_models FROM model_counts) as model_count
        FROM monthly_sales;
    END;
    $$;
    ```
    
    Args:
        manufacturer_name: Name of the manufacturer to get stats for
        year: Year to get stats for
        
    Returns:
        Tuple containing:
        - List of records (as dictionaries)
        - Error message (if any)
    """
    try:
        # Method 1: Using Supabase client
        supabase = get_supabase_client()
        response = supabase.rpc(
            'get_manufacturer_stats',
            {'p_manufacturer': manufacturer_name, 'p_year': year}
        ).execute()
        
        # Handle the response format according to the client version
        data = response.data
        
        if not data:
            return [], None
            
        return data, None
        
    except Exception as e:
        error_message = f"Error calling RPC function: {str(e)}\n{traceback.format_exc()}"
        return [], error_message

async def call_rpc_with_http(function_name: str, params: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Generic function to call any RPC function via direct HTTP request
    
    Args:
        function_name: Name of the RPC function to call
        params: Parameters to pass to the function
        
    Returns:
        Tuple containing:
        - List of records (as dictionaries)
        - Error message (if any)
    """
    try:
        # Get Supabase URL and key from environment
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            return [], "Missing Supabase credentials"
        
        # Make a direct HTTP request to the Supabase RPC API
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        
        # RPC endpoint URL
        rpc_endpoint = f"{supabase_url}/rest/v1/rpc/{function_name}"
        
        # Make the request
        async with httpx.AsyncClient() as client:
            print(f"Calling RPC function: {function_name} with params: {params}")
            response = await client.post(
                rpc_endpoint,
                headers=headers,
                json=params
            )
            
            # Check for errors
            if response.status_code >= 400:
                return [], f"RPC error: {response.status_code} - {response.text}"
            
            # Parse the response
            try:
                data = response.json()
                if isinstance(data, list):
                    return data, None
                elif isinstance(data, dict):
                    return [data], None
                else:
                    return [], f"Unexpected response format: {type(data)}"
            except json.JSONDecodeError:
                return [], f"Error parsing response: {response.text}"
    
    except Exception as e:
        error_message = f"Error calling RPC function: {str(e)}\n{traceback.format_exc()}"
        return [], error_message

# Example usage:
# async def get_stats_example():
#     # Using the Supabase client approach
#     data, error = await call_manufacturer_stats_rpc("长安汽车", 2021)
#     if error:
#         print(f"Error: {error}")
#     else:
#         print(f"Stats: {data}")
#
#     # Using the direct HTTP approach
#     data, error = await call_rpc_with_http(
#         "get_manufacturer_stats", 
#         {"p_manufacturer": "长安汽车", "p_year": 2021}
#     )
#     if error:
#         print(f"Error: {error}")
#     else:
#         print(f"Stats: {data}")