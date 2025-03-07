from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SQLQueryRequest(BaseModel):
    """Model for SQL query requests"""
    query: str = Field(..., description="SQL query to execute")
    limit: Optional[int] = Field(1000, description="Maximum number of rows to return")

class ColumnMetadata(BaseModel):
    """Model for column metadata"""
    description: str = Field(..., description="Description of the column's purpose and content")
    data_type: Optional[str] = Field(None, description="Data type of the column (e.g., integer, text)")
    
class TableMetadata(BaseModel):
    """Model for table metadata"""
    description: str = Field(..., description="Description of the table's purpose and content")
    columns: Dict[str, str] = Field(..., description="Mapping of column names to their descriptions")

class SchemaMetadataResponse(BaseModel):
    """Model for schema metadata response"""
    tables: Dict[str, TableMetadata] = Field(..., description="Mapping of table names to their metadata")
    error: Optional[str] = Field(None, description="Error message if schema retrieval failed")

class SQLQueryResponse(BaseModel):
    """Model for SQL query responses"""
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query results as a list of records")
    columns: List[str] = Field(default_factory=list, description="Column names from the query result")
    column_order: List[str] = Field(default_factory=list, description="Column names in the order they should be displayed")
    query: str = Field("", description="The executed SQL query")
    error: Optional[str] = Field(None, description="Error message if query execution failed")
    rows_returned: int = Field(0, description="Number of rows returned by the query")
    requested_limit: Optional[int] = Field(None, description="The limit that was requested")
    total_rows_available: Optional[int] = Field(None, description="Total number of rows available (may be approximate)")
    execution_time_ms: Optional[float] = Field(None, description="Query execution time in milliseconds")
    schema_metadata: Optional[Dict[str, TableMetadata]] = Field(None, description="Metadata about tables referenced in the query") 