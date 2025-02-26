import pandas as pd
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
import json
from src.db.supabase_client import get_supabase_client

async def import_auto_sales_data_to_supabase(
    csv_file_path: str, 
    upsert: bool = True, 
    row_limit: Optional[int] = None,
    start_row: int = 0
) -> Dict[str, Any]:
    """
    Import auto sales data from CSV file to Supabase.
    Uses upsert to avoid duplicates for manufacturer_name + year + month + model_name combinations.
    
    Args:
        csv_file_path: Path to the CSV file
        upsert: Whether to use upsert (True) or insert (False)
        row_limit: Maximum number of rows to import (None means import all)
        start_row: Starting row index (0-based) to begin import from
        
    Returns:
        Dict containing import stats
    """
    print(f"Importing data from {csv_file_path}")
    if row_limit:
        print(f"Limiting import to {row_limit} rows")
    if start_row > 0:
        print(f"Starting from row {start_row}")
    
    # Check if file exists
    if not os.path.exists(csv_file_path):
        return {"status": "error", "message": f"File not found: {csv_file_path}"}
    
    try:
        # Determine file type
        if csv_file_path.endswith('.json'):
            # If JSON file, read it and convert to normalized format
            print("Processing JSON file")
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            # Apply start_row and row_limit if specified
            end_row = None if row_limit is None else start_row + row_limit
            json_data = json_data[start_row:end_row]
            
            # Create a list to hold the normalized data
            normalized_data = []
            
            # Process each record
            for record in json_data:
                manufacturer = record.get('manufacturer_name', '')
                month = record.get('month', 0)
                year = record.get('year', 0)
                total_units = record.get('total_units_sold', 0)
                
                # Check if models data exists
                models = record.get('models', [])
                
                if models:
                    # Create a row for each model
                    for model in models:
                        model_name = model.get('model_name', '')
                        model_units = model.get('units_sold', 0)
                        
                        normalized_data.append({
                            'manufacturer_name': manufacturer,
                            'month': month,
                            'year': year,
                            'total_units_sold': total_units,
                            'model_name': model_name,
                            'model_units_sold': model_units
                        })
                else:
                    # Create a row with empty model data
                    normalized_data.append({
                        'manufacturer_name': manufacturer,
                        'month': month,
                        'year': year,
                        'total_units_sold': total_units,
                        'model_name': '',
                        'model_units_sold': 0
                    })
            
            # Convert to DataFrame
            df = pd.DataFrame(normalized_data)
            
        else:
            # If CSV file, read directly
            print("Processing CSV file")
            if start_row > 0 or row_limit is not None:
                # Apply start_row and row_limit
                if row_limit is None:
                    df = pd.read_csv(csv_file_path, skiprows=start_row)
                else:
                    df = pd.read_csv(csv_file_path, skiprows=start_row, nrows=row_limit)
            else:
                df = pd.read_csv(csv_file_path)
        
        print(f"Read {len(df)} rows from file")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Process data in chunks to avoid timeout issues
        CHUNK_SIZE = 100
        total_records = len(df)
        successful_imports = 0
        failed_imports = 0
        
        # Import records in chunks
        for i in range(0, total_records, CHUNK_SIZE):
            chunk = df.iloc[i:min(i+CHUNK_SIZE, total_records)]
            print(f"Processing chunk {i//CHUNK_SIZE + 1}/{(total_records + CHUNK_SIZE - 1)//CHUNK_SIZE}")
            
            # Convert chunk to list of dictionaries
            records = chunk.to_dict('records')
            
            try:
                # Format the data for Supabase
                formatted_records = []
                for record in records:
                    # Prepare record with the exact structure needed
                    formatted_record = {
                        "manufacturer_name": str(record.get("manufacturer_name", "")),
                        "month": int(record.get("month", 0)),
                        "year": int(record.get("year", 0)),
                        "total_units_sold": int(record.get("total_units_sold", 0)),
                        "model_name": str(record.get("model_name", "")),
                        "model_units_sold": int(record.get("model_units_sold", 0))
                    }
                    
                    formatted_records.append(formatted_record)
                
                if upsert:
                    # Use upsert to avoid duplicates
                    # This will update existing records with matching keys or insert new ones
                    response = supabase.table("china_auto_sales").upsert(
                        formatted_records, 
                        on_conflict="manufacturer_name,year,month,model_name"
                    ).execute()
                    print("Used upsert operation for this chunk")
                else:
                    # Use insert (original behavior)
                    response = supabase.table("china_auto_sales").insert(formatted_records).execute()
                    print("Used insert operation for this chunk")
                
                # Check response and update counts
                if response.data:
                    successful_imports += len(formatted_records)
                    print(f"Successfully imported {len(formatted_records)} records")
                else:
                    failed_imports += len(formatted_records)
                    print(f"Failed to import {len(formatted_records)} records")
                    
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_imports += len(records)
                print(f"Error importing chunk: {str(e)}")
        
        # Return import stats
        return {
            "status": "success" if failed_imports == 0 else "partial",
            "total_records": total_records,
            "successful_imports": successful_imports,
            "failed_imports": failed_imports,
            "operation": "upsert" if upsert else "insert",
            "row_limit_applied": row_limit is not None,
            "start_row": start_row
        }
        
    except Exception as e:
        print(f"Error importing data: {str(e)}")
        return {"status": "error", "message": str(e)}

# Command-line execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python import_data.py <csv_file_path>")
        sys.exit(1)
        
    csv_file = sys.argv[1]
    asyncio.run(import_auto_sales_data_to_supabase(csv_file)) 