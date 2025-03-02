from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
import asyncio
import time
from pydantic import BaseModel

from ...models.sql_models import SQLQueryRequest, SQLQueryResponse
from ...db.sql_client import execute_sql_query

router = APIRouter()

@router.post("/execute", response_model=SQLQueryResponse)
async def execute_sql(request: SQLQueryRequest) -> SQLQueryResponse:
    """
    Execute a SQL query against the database
    
    This endpoint accepts a SQL query and executes it against the database
    using the exec_sql PostgreSQL function. For security reasons, only 
    SELECT queries are allowed.
    
    Returns:
        SQLQueryResponse: Query results including data, columns, and error information
    """
    start_time = time.time()
    
    # Execute the query directly using the exec_sql function
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
        total_rows_available=len(data) if len(data) < request.limit else None,
        execution_time_ms=round(execution_time, 2)
    )
    
    return response

# Example RPC endpoint implementation

class ManufacturerStatsRequest(BaseModel):
    manufacturer_name: str
    year: int

class ManufacturerStatsResponse(BaseModel):
    data: List[Dict[str, Any]]
    error: str = None
    execution_time_ms: float

@router.post("/manufacturer-stats", response_model=ManufacturerStatsResponse)
async def get_manufacturer_stats(request: ManufacturerStatsRequest) -> ManufacturerStatsResponse:
    """
    Get manufacturer statistics using a Supabase RPC function
    
    This endpoint demonstrates how to call a custom RPC function in Supabase.
    It retrieves statistics for a specific manufacturer and year.
    
    Returns:
        ManufacturerStatsResponse: Statistics data including total sales, peak month, etc.
    """
    start_time = time.time()
    
    # Call the RPC function using the method that uses the Supabase client
    data, error = await call_manufacturer_stats_rpc(
        manufacturer_name=request.manufacturer_name,
        year=request.year
    )
    
    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Build the response
    response = ManufacturerStatsResponse(
        data=data,
        error=error,
        execution_time_ms=round(execution_time, 2)
    )
    
    return response

@router.post("/call-rpc")
async def call_rpc_function(
    function_name: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generic endpoint to call any RPC function in Supabase
    
    This endpoint demonstrates how to call any RPC function using the
    direct HTTP request method.
    
    Args:
        function_name: Name of the RPC function to call
        params: Parameters to pass to the function
        
    Returns:
        Dict containing the response data and execution information
    """
    start_time = time.time()
    
    # Call the RPC function using the direct HTTP method
    data, error = await call_rpc_with_http(
        function_name=function_name,
        params=params
    )
    
    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Build the response
    response = {
        "data": data,
        "error": error,
        "execution_time_ms": round(execution_time, 2)
    }
    
    return response 