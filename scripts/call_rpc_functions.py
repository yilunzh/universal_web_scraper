#!/usr/bin/env python3
"""
Utility script to call RPC functions in Supabase

This script demonstrates how to call RPC functions in a Supabase database
using direct HTTP requests.

Usage:
    # Call a specific RPC function
    python scripts/call_rpc_functions.py get_manufacturer_stats '{"p_manufacturer": "长安汽车", "p_year": 2021}'
    
    # Call the top models function
    python scripts/call_rpc_functions.py get_top_models '{"p_year": 2021, "p_limit": 5}'
    
    # Execute a SQL query using the exec_sql function
    python scripts/call_rpc_functions.py exec_sql '{"sql": "SELECT SUM(total_units_sold) FROM china_auto_sales WHERE manufacturer_name = '"'"'长安汽车'"'"' AND year = 2021"}'

Requirements:
    - httpx
    - python-dotenv
"""

import os
import asyncio
import httpx
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv('.env.local')  # Load .env.local which should override .env

async def call_rpc_function(function_name: str, params: dict) -> dict:
    """
    Call an RPC function in Supabase
    
    Args:
        function_name: Name of the RPC function to call
        params: Parameters to pass to the function
        
    Returns:
        Response from the API
    """
    # Get Supabase URL and key from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
    
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
        print(f"Calling RPC function: {function_name}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        
        response = await client.post(
            rpc_endpoint,
            headers=headers,
            json=params
        )
        
        # Check for errors
        if response.status_code >= 400:
            print(f"Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        # Parse the response
        try:
            data = response.json()
            return data
        except json.JSONDecodeError:
            print(f"Error parsing response: {response.text}")
            return {"error": "JSON parse error"}

async def main():
    """
    Main function to call RPC functions based on command line arguments
    """
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <function_name> [params_json]")
        return
    
    function_name = sys.argv[1]
    params = {}
    
    if len(sys.argv) > 2:
        try:
            params = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON parameters: {sys.argv[2]}")
            return
    
    print(f"Calling {function_name} with parameters: {params}")
    result = await call_rpc_function(function_name, params)
    
    # Pretty print the result
    print("\nResult:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 