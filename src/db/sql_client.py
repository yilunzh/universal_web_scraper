import os
import traceback
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import asyncio
import httpx
import re
from postgrest.exceptions import APIError

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
    Execute a SQL query against the Supabase database
    
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
        # Format the query properly to avoid SQL parsing issues
        formatted_query = format_sql_query(query, limit)
        print(f"Executing formatted query: {formatted_query}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Check if this is a complex query with GROUP BY, ORDER BY, etc.
        is_complex_query = "group by" in cleaned_query or "order by" in cleaned_query
        
        # For complex queries, we'll try a different approach
        if is_complex_query:
            try:
                # First, try to directly execute the query using the SQL function
                response = await supabase.postgrest.rpc(
                    "exec_sql",
                    {"query": formatted_query}
                ).execute()
                
                data = response.data
                
                # Check if we got a proper result
                if data and isinstance(data, list) and len(data) > 0:
                    if all(isinstance(col, str) and "order by" in col.lower() for col in data[0].keys()):
                        # If column names contain SQL clauses, we need to try the fallback
                        raise Exception("Column names contain SQL clauses, using fallback")
                    else:
                        # We got a proper result, return it
                        columns = list(data[0].keys()) if data else []
                        print(f"Query returned {len(data)} rows")
                        return data, columns, None
                else:
                    # Empty result, try fallback for china_auto_sales queries
                    if "china_auto_sales" in query.lower():
                        print("Empty result from exec_sql, trying fallback query")
                        raise Exception("Empty result, using fallback")
                    else:
                        # If not china_auto_sales, just return empty result
                        return [], [], None
            except Exception as e:
                print(f"Complex query execution failed: {e}")
                # Fall through to the fallback for china_auto_sales queries
        else:
            # For simple queries, use the standard approach
            try:
                response = await supabase.postgrest.rpc(
                    "exec_sql",
                    {"query": formatted_query}
                ).execute()
                
                data = response.data
                
                # If we got a proper result, return it
                if data and isinstance(data, list) and len(data) > 0:
                    columns = list(data[0].keys()) if data else []
                    print(f"Query returned {len(data)} rows")
                    return data, columns, None
                else:
                    # Empty result, check if we should try fallback
                    if "china_auto_sales" in query.lower():
                        print("Empty result from exec_sql, trying fallback query")
                    else:
                        # If not china_auto_sales, just return empty result
                        return [], [], None
            except Exception as e:
                print(f"Standard query execution failed: {e}")
                # Fall through to the fallback for china_auto_sales queries
        
        # At this point, we're falling back to direct table query for china_auto_sales
        if "china_auto_sales" in query.lower():
            print("Trying direct table query as fallback...")
            
            # Try to parse manufacturer name from query for a more precise fallback
            manufacturer_match = re.search(r"manufacturer_name\s*=\s*['\"]([^'\"]+)['\"]", query, re.IGNORECASE)
            manufacturer = manufacturer_match.group(1) if manufacturer_match else None
            
            # Try to parse year from query
            year_match = re.search(r"year\s*=\s*(\d+)", query, re.IGNORECASE)
            year = year_match.group(1) if year_match else None
            
            # Extract limit from the query using our regex pattern
            limit_pattern = re.compile(r'\blimit\s+\d+\b', re.IGNORECASE)
            limit_match = limit_pattern.search(formatted_query)
            extracted_limit = int(limit_match.group().split()[1]) if limit_match else limit
            
            # Build a better fallback query with filters
            builder = supabase.table("china_auto_sales").select("*")
            
            if manufacturer:
                print(f"Filtering by manufacturer: {manufacturer}")
                builder = builder.eq("manufacturer_name", manufacturer)
            
            if year:
                print(f"Filtering by year: {year}")
                builder = builder.eq("year", int(year))
            
            # Apply the limit
            builder = builder.limit(extracted_limit)
            
            print(f"Executing fallback query with filters")
            response = builder.execute()
            data = response.data
            
            # If this is a GROUP BY query, we need to perform the aggregation manually
            if "group by" in query.lower():
                print("Handling GROUP BY aggregation manually")
                
                # Check if we have a SUM or COUNT aggregation
                has_sum = "sum" in query.lower()
                has_count = "count" in query.lower()
                
                # Try to determine the aggregation target column
                agg_target_col = "model_units_sold"  # Default
                if has_sum:
                    # Try to extract the column being summed
                    sum_match = re.search(r"sum\s*\(\s*([^\s\)]+)\s*\)", query, re.IGNORECASE)
                    if sum_match:
                        agg_target_col = sum_match.group(1).strip()
                
                # Extract the columns to group by
                group_by_match = re.search(r"group by\s+([^;]+?)(?:\s+order|\s*$)", query, re.IGNORECASE)
                if group_by_match:
                    group_cols_str = group_by_match.group(1)
                    group_columns = [col.strip() for col in group_cols_str.split(",")]
                    
                    # Create aggregated results
                    aggregated_data = {}
                    for row in data:
                        # Create a key based on group by columns
                        key_parts = []
                        for col in group_columns:
                            col = col.strip()
                            key_parts.append(str(row.get(col, "")))
                        
                        key = "|".join(key_parts)
                        
                        if key not in aggregated_data:
                            # Initialize with group columns
                            agg_row = {col: row.get(col) for col in group_columns}
                            
                            # Set the correct alias name based on the query
                            alias_match = re.search(r"as\s+([^\s,]+)", query, re.IGNORECASE)
                            agg_col_name = alias_match.group(1).strip() if alias_match else "total_sales"
                            
                            # Initialize the aggregation column
                            agg_row[agg_col_name] = row.get(agg_target_col, 0)
                            aggregated_data[key] = agg_row
                        else:
                            # Update existing aggregation
                            alias_match = re.search(r"as\s+([^\s,]+)", query, re.IGNORECASE)
                            agg_col_name = alias_match.group(1).strip() if alias_match else "total_sales"
                            aggregated_data[key][agg_col_name] += row.get(agg_target_col, 0)
                    
                    # Convert back to list
                    data = list(aggregated_data.values())
                    
                    # Handle ORDER BY if present
                    order_by_match = re.search(r"order by\s+([^;]+?)(?:\s+limit|\s*$)", query, re.IGNORECASE)
                    if order_by_match:
                        order_col = order_by_match.group(1).strip()
                        is_desc = "desc" in order_col.lower()
                        order_col = order_col.replace("desc", "").replace("asc", "").strip()
                        
                        # Sort the data
                        data.sort(
                            key=lambda x: x.get(order_col, 0) if order_col in x else 0, 
                            reverse=is_desc
                        )
                    
                    # Apply LIMIT
                    data = data[:extracted_limit]
            
            print(f"Fallback query returned {len(data)} rows")
            
            # Return the processed data
            if data and isinstance(data, list) and len(data) > 0:
                columns = list(data[0].keys()) if data else []
                return data, columns, None
            
            # If we made it here with no data, return empty result
            return [], [], None
        else:
            # Not a china_auto_sales query, return empty result or error
            return [], [], "Query execution failed and no fallback available"
    
    except APIError as e:
        error_message = f"Database error: {str(e)}"
        return [], [], error_message
    except Exception as e:
        error_message = f"Error executing query: {str(e)}\n{traceback.format_exc()}"
        return [], [], error_message

def format_sql_query(query: str, limit: int = 1000) -> str:
    """
    Format a SQL query to ensure proper syntax and add LIMIT if needed
    
    Args:
        query: The original SQL query
        limit: Maximum number of rows to return
        
    Returns:
        Properly formatted SQL query
    """
    # First, normalize the query by replacing all newlines with spaces
    # This prevents newlines from being interpreted as part of column names
    query = re.sub(r'\s+', ' ', query.strip())
    
    # Remove any trailing semicolons
    if query.endswith(';'):
        query = query[:-1].strip()
    
    # Parse the main parts of the query
    # The basic structure is: SELECT ... FROM ... WHERE ... GROUP BY ... ORDER BY ... LIMIT ...
    select_pattern = re.compile(r'(SELECT.*?FROM.*?)(?:\s+WHERE|\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)', re.IGNORECASE | re.DOTALL)
    where_pattern = re.compile(r'(WHERE.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)', re.IGNORECASE | re.DOTALL)
    group_by_pattern = re.compile(r'(GROUP\s+BY.*?)(?:\s+ORDER\s+BY|\s+LIMIT|$)', re.IGNORECASE | re.DOTALL)
    order_by_pattern = re.compile(r'(ORDER\s+BY.*?)(?:\s+LIMIT|$)', re.IGNORECASE | re.DOTALL)
    limit_pattern = re.compile(r'LIMIT\s+(\d+)', re.IGNORECASE)
    
    # Extract each part of the query
    select_match = select_pattern.search(query)
    select_clause = select_match.group(1).strip() if select_match else ""
    
    where_match = where_pattern.search(query)
    where_clause = where_match.group(1).strip() if where_match else ""
    
    group_by_match = group_by_pattern.search(query)
    group_by_clause = group_by_match.group(1).strip() if group_by_match else ""
    
    order_by_match = order_by_pattern.search(query)
    order_by_clause = order_by_match.group(1).strip() if order_by_match else ""
    
    # Check if a LIMIT clause exists
    limit_match = limit_pattern.search(query)
    has_limit = bool(limit_match)
    extracted_limit = int(limit_match.group(1)) if limit_match else limit
    
    # Reconstruct the query with proper spacing
    formatted_query = select_clause
    
    if where_clause:
        formatted_query += f" {where_clause}"
    
    if group_by_clause:
        formatted_query += f" {group_by_clause}"
    
    if order_by_clause:
        formatted_query += f" {order_by_clause}"
    
    # Add LIMIT if it doesn't exist
    if not has_limit:
        formatted_query += f" LIMIT {limit}"
    else:
        # Use the limit from the query
        formatted_query += f" LIMIT {extracted_limit}"
    
    # Add semicolon
    return f"{formatted_query};"

# Function to check if our SQL execution function is available
async def check_sql_function_exists() -> bool:
    """
    Check if the exec_sql function exists in the database
    Returns True if the function exists, False otherwise
    """
    try:
        supabase = get_supabase_client()
        # Query to check if the function exists
        response = await supabase.table("pg_proc") \
            .select("proname") \
            .eq("proname", "exec_sql") \
            .execute()
        
        return len(response.data) > 0
    except Exception:
        return False

# Create the SQL function if it doesn't exist
async def create_sql_function() -> bool:
    """
    Create the exec_sql function in the database if it doesn't exist
    Returns True if successful, False otherwise
    """
    try:
        # This requires superuser privileges, which the service role key should have
        supabase = get_supabase_client()
        
        # Create a SQL function that can execute arbitrary SQL and properly handle result sets
        # This version uses a more robust approach for query execution
        create_function_sql = """
        CREATE OR REPLACE FUNCTION exec_sql(query text)
        RETURNS JSONB
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            result_set refcursor;
            result_rows JSONB;
            result_record record;
            column_names text[];
            column_values jsonb[];
            final_result jsonb[];
            i integer;
        BEGIN
            -- Check if this is a SELECT query for security
            IF NOT (lower(query) ~ '^\\s*select') THEN
                RETURN jsonb_build_object('error', 'Only SELECT queries are allowed');
            END IF;
            
            -- Open a cursor to execute the query
            OPEN result_set FOR EXECUTE query;
            
            -- Get the column names
            SELECT array_agg(column_name::text)
            INTO column_names
            FROM (
                SELECT attname as column_name
                FROM pg_attribute
                WHERE attrelid = pg_backend_pid()::text::regclass
                AND attnum > 0
                AND NOT attisdropped
                ORDER BY attnum
            ) t;
            
            -- Initialize variables
            final_result := '[]'::jsonb;
            i := 0;
            
            -- Fetch each row and build the JSON result
            LOOP
                FETCH result_set INTO result_record;
                EXIT WHEN NOT FOUND;
                
                i := i + 1;
                
                -- Convert each record to JSON
                SELECT json_build_object(
                    column_names[1], result_record.column1,
                    column_names[2], result_record.column2
                )::jsonb
                INTO result_rows;
                
                -- Add to final result array
                final_result := final_result || result_rows;
                
                -- Limit to 1000 rows to prevent excessive results
                IF i >= 1000 THEN
                    EXIT;
                END IF;
            END LOOP;
            
            -- Close the cursor
            CLOSE result_set;
            
            -- Return the final JSON array
            RETURN final_result;
        EXCEPTION WHEN OTHERS THEN
            -- Close cursor if it's open
            IF result_set IS NOT NULL AND result_set IS OPEN THEN
                CLOSE result_set;
            END IF;
            
            -- Return the error
            RETURN jsonb_build_object(
                'error', SQLERRM,
                'detail', SQLSTATE
            );
        END;
        $$;
        """
        
        # Execute the SQL directly using the REST API
        response = await supabase.postgrest.rpc(
            "exec_sql",
            {"query": create_function_sql}
        ).execute()
        
        return True
    except Exception as e:
        print(f"Error creating SQL function: {e}")
        # Fall back to a simpler approach - let's modify our execute_sql_query function
        # to handle complex queries differently
        return False