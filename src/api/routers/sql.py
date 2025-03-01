from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
import asyncio
import time

from ...models.sql_models import SQLQueryRequest, SQLQueryResponse
from ...db.sql_client import execute_sql_query, check_sql_function_exists, create_sql_function

router = APIRouter()

@router.post("/execute", response_model=SQLQueryResponse)
async def execute_sql(request: SQLQueryRequest) -> SQLQueryResponse:
    """
    Execute a SQL query against the database
    
    This endpoint accepts a SQL query and executes it against the database.
    For security reasons, only SELECT queries are allowed.
    
    Returns:
        SQLQueryResponse: Query results including data, columns, and error information
    """
    start_time = time.time()
    
    # Execute the query
    data, columns, error = await execute_sql_query(
        query=request.query, 
        limit=request.limit
    )
    
    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Build the response
    response = SQLQueryResponse(
        data=data,
        columns=columns,
        query=request.query,
        error=error,
        rows_returned=len(data),
        requested_limit=request.limit,
        total_rows_available=len(data) if len(data) < request.limit else None,  # If we hit the limit, we don't know the total
        execution_time_ms=round(execution_time, 2)
    )
    
    return response

@router.get("/setup-check")
async def check_sql_setup() -> Dict[str, Any]:
    """
    Check if the SQL execution function exists in the database
    
    This endpoint checks if the exec_sql function exists and creates it if it doesn't.
    
    Returns:
        Dict with status of the SQL execution setup
    """
    function_exists = await check_sql_function_exists()
    
    if not function_exists:
        # Try to create the function
        created = await create_sql_function()
        if created:
            return {
                "status": "success",
                "message": "SQL execution function was created successfully",
                "function_exists": True
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create SQL execution function. Check server logs for details.",
                "function_exists": False
            }
    
    return {
        "status": "success",
        "message": "SQL execution function already exists",
        "function_exists": True
    } 