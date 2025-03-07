from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
import time

from ...models.sql_models import SQLQueryRequest, SQLQueryResponse, SchemaMetadataResponse
from ...db.sql_client import execute_sql_query

# Define column descriptions for tables
SCHEMA_METADATA = {
    "china_auto_sales": {
        "description": "Monthly auto sales data for manufacturers in China",
        "columns": {
            "id": "Unique identifier for each sales record",
            "year": "Year of the sales data (e.g., 2020, 2021, 2022)",
            "month": "Month of the sales data (1-12)",
            "manufacturer_name": "Name of the automobile manufacturer (e.g., '长安汽车', '上汽集团')",
            "model_name": "Name of the car model",
            "model_units_sold": "Number of units sold for this specific model in the given month",
            "total_units_sold": "Total units sold by this manufacturer in the given month",
            "url": "Source URL for the data",
            "created_at": "Timestamp when this record was created in the database"
        }
    }
    # Add other tables as needed
}

router = APIRouter()

@router.get("/schema", response_model=SchemaMetadataResponse)
async def get_schema_metadata(table_name: Optional[str] = None) -> SchemaMetadataResponse:
    """
    Get schema metadata including column descriptions for tables
    
    This endpoint provides metadata about database tables and columns that can be
    used as context for AI to better understand the schema when generating SQL.
    
    Args:
        table_name: Optional table name to get specific table metadata
        
    Returns:
        SchemaMetadataResponse: Schema metadata including tables and their column descriptions
    """
    if table_name and table_name not in SCHEMA_METADATA:
        return SchemaMetadataResponse(
            tables={},
            error=f"Table '{table_name}' not found in schema metadata"
        )
    
    if table_name:
        return SchemaMetadataResponse(
            tables={table_name: SCHEMA_METADATA[table_name]}
        )
    
    return SchemaMetadataResponse(tables=SCHEMA_METADATA)

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
    
    # Get schema metadata for any tables referenced in the query
    schema_context = {}
    
    # Simple parsing to find table names in the query (a basic approach)
    query_lower = request.query.lower()
    for table_name in SCHEMA_METADATA:
        if f"from {table_name}" in query_lower or f"join {table_name}" in query_lower:
            schema_context[table_name] = SCHEMA_METADATA[table_name]
    
    # Build the response
    response = SQLQueryResponse(
        data=data,
        columns=columns,
        column_order=columns,
        query=request.query,
        error=error,
        rows_returned=len(data),
        requested_limit=request.limit,
        total_rows_available=len(data) if len(data) < request.limit else None,
        execution_time_ms=round(execution_time, 2),
        schema_metadata=schema_context if schema_context else None
    )
    
    return response 