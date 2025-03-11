#!/usr/bin/env python3
"""
Utility script to create the exec_sql function in Supabase

This script creates a single PostgreSQL function in Supabase that allows
executing arbitrary SQL queries. This is a simpler alternative to creating
specific RPC functions for each query pattern.

Usage:
    python scripts/create_exec_sql.py

Requirements:
    - httpx
    - python-dotenv
"""

import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv('.env.local')  # Load .env.local which should override .env

async def create_exec_sql_function() -> dict:
    """
    Create the exec_sql function in Supabase
    
    Returns:
        Response from the API
    """
    # Get Supabase URL and key from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
    
    # Make a direct HTTP request to the Supabase SQL API
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # SQL endpoint URL
    sql_endpoint = f"{supabase_url}/rest/v1/rpc/rest"
    
    # SQL statement to create the exec_sql function
    function_sql = """
    CREATE OR REPLACE FUNCTION exec_sql(sql text)
    RETURNS jsonb
    LANGUAGE plpgsql
    SECURITY DEFINER -- Runs with the privileges of the function creator
    AS $$
    DECLARE
        result jsonb;
        normalized_sql text;
    BEGIN
        -- Convert to lowercase and remove extra whitespace for consistent checking
        normalized_sql := lower(regexp_replace(sql, E'\\s+', ' ', 'g'));
        
        -- Security check: Block any statements that could modify the database
        -- Check for keywords that modify data or database structure
        IF normalized_sql ~* '\\m(insert|update|delete|drop|alter|create|truncate|grant|revoke|vacuum|analyze|reindex|discard|lock|prepare|execute|deallocate|declare|explain\\s+analyze)\\M' THEN
            RAISE EXCEPTION 'Only read-only queries are allowed. Detected potential data modification keywords.';
        END IF;
        
        -- Execute the query and convert results to JSON
        EXECUTE 'SELECT jsonb_agg(row_to_json(t)) FROM (' || sql || ') t' INTO result;
        
        -- Handle NULL result (no rows)
        IF result IS NULL THEN
            result := '[]'::jsonb;
        END IF;
        
        RETURN result;
    EXCEPTION
        WHEN others THEN
            RETURN jsonb_build_object(
                'error', SQLERRM,
                'detail', SQLSTATE,
                'query', sql
            );
    END;
    $$;
    """
    
    # Make the request
    async with httpx.AsyncClient() as client:
        print(f"Creating exec_sql function...")
        response = await client.post(
            sql_endpoint,
            headers=headers,
            json={"sql": function_sql}
        )
        
        # Check for errors
        if response.status_code >= 400:
            print(f"Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        # Parse the response
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return data
        except json.JSONDecodeError:
            print(f"Error parsing response: {response.text}")
            return {"error": "JSON parse error"}

async def test_exec_sql_function() -> dict:
    """
    Test the exec_sql function
    
    Returns:
        Result of the test query
    """
    # Get Supabase URL and key from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
        
    # SQL query to test
    test_query = "SELECT manufacturer_name, COUNT(*) as model_count FROM china_auto_sales GROUP BY manufacturer_name LIMIT 5"
    
    # Make a direct HTTP request to the Supabase RPC API
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # RPC endpoint URL
    rpc_endpoint = f"{supabase_url}/rest/v1/rpc/exec_sql"
    
    # Make the request
    async with httpx.AsyncClient() as client:
        print(f"Testing exec_sql function with query: {test_query}")
        response = await client.post(
            rpc_endpoint,
            headers=headers,
            json={"sql": test_query}
        )
        
        # Check for errors
        if response.status_code >= 400:
            print(f"Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        # Parse the response
        try:
            data = response.json()
            print(f"Test query returned: {json.dumps(data, indent=2)}")
            return data
        except json.JSONDecodeError:
            print(f"Error parsing response: {response.text}")
            return {"error": "JSON parse error"}

async def main():
    """
    Main function to create and test the exec_sql function
    """
    # Create the exec_sql function
    creation_result = await create_exec_sql_function()
    
    if "error" in creation_result:
        print("Failed to create exec_sql function")
        return
        
    print("exec_sql function created successfully!")
    
    # Test the exec_sql function
    test_result = await test_exec_sql_function()
    
    if "error" in test_result:
        print("Failed to test exec_sql function")
        return
        
    print("exec_sql function tested successfully!")
    print(f"Number of results: {len(test_result)}")

if __name__ == "__main__":
    asyncio.run(main()) 