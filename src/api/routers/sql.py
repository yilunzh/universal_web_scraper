from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import time

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