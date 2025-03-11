#!/usr/bin/env python3
"""
Utility script to create RPC functions in Supabase

This script demonstrates how to create RPC functions in a Supabase database
using direct HTTP requests.

Usage:
    python scripts/create_rpc_functions.py

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

async def create_rpc_function(function_sql: str) -> dict:
    """
    Create an RPC function in Supabase using a SQL statement
    
    Args:
        function_sql: SQL statement to create the function
        
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
    
    # Make the request
    async with httpx.AsyncClient() as client:
        print(f"Executing SQL: {function_sql}")
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

async def main():
    """
    Main function to create RPC functions
    """
    print("Creating RPC functions in Supabase...")
    
    # Example 1: Create a function to get manufacturer statistics
    manufacturer_stats_sql = """
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
    """
    
    await create_rpc_function(manufacturer_stats_sql)
    
    # Example 2: Create a function to get top models by sales
    top_models_sql = """
    CREATE OR REPLACE FUNCTION get_top_models(p_year integer, p_limit integer DEFAULT 10)
    RETURNS TABLE (
        model_name text,
        manufacturer_name text,
        total_sales bigint
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        SELECT 
            model_name,
            manufacturer_name,
            SUM(model_units_sold) as total_sales
        FROM china_auto_sales
        WHERE year = p_year
        GROUP BY model_name, manufacturer_name
        ORDER BY total_sales DESC
        LIMIT p_limit;
    END;
    $$;
    """
    
    await create_rpc_function(top_models_sql)
    
    # Example 3: Create a function to create the exec_sql function
    # This is a powerful function that allows executing arbitrary SQL queries
    # IMPORTANT: In production, you should add additional security checks
    exec_sql_function = """
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
    
    await create_rpc_function(exec_sql_function)
    
    print("RPC functions created successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 