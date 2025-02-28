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
            
            # Check file size before loading
            file_size = os.path.getsize(csv_file_path) / (1024 * 1024)  # Size in MB
            print(f"JSON file size: {file_size:.2f} MB")
            
            try:
                with open(csv_file_path, 'r', encoding='utf-8') as f:
                    # Read first few characters to debug
                    first_chars = f.read(200)
                    print(f"First 200 characters of file: {repr(first_chars)}")
                    f.seek(0)  # Reset file pointer
                    
                    # Try to load the JSON
                    try:
                        json_data = json.load(f)
                        print(f"Successfully loaded JSON data")
                        
                        # Debug JSON structure
                        print(f"JSON type: {type(json_data)}")
                        if isinstance(json_data, dict):
                            print(f"Root keys: {list(json_data.keys())}")
                            # Try to find array data
                            for key, value in json_data.items():
                                if isinstance(value, list) and len(value) > 0:
                                    print(f"Found list in key '{key}' with {len(value)} items")
                                    json_data = value  # Use this as our data array
                                    break
                        elif isinstance(json_data, list):
                            print(f"JSON is a list with {len(json_data)} items")
                        
                    except json.JSONDecodeError as je:
                        print(f"JSON decode error: {str(je)}")
                        return {"status": "error", "message": f"Invalid JSON: {str(je)}"}
            except Exception as e:
                print(f"Error reading JSON file: {str(e)}")
                return {"status": "error", "message": str(e)}
            
            # Safeguard against invalid JSON structure
            if not isinstance(json_data, list):
                print("JSON data is not a list, cannot process")
                return {"status": "error", "message": "JSON data must be a list"}
            
            print(f"Processing {len(json_data)} JSON records")
            
            # Apply start_row and row_limit if specified - with safeguards
            try:
                if start_row > 0:
                    if start_row >= len(json_data):
                        return {"status": "error", "message": f"Start row {start_row} exceeds JSON length {len(json_data)}"}
                    json_data = json_data[start_row:]
                    
                if row_limit is not None:
                    json_data = json_data[:row_limit]
                    
                print(f"After applying limits: {len(json_data)} records to process")
            except Exception as e:
                print(f"Error during JSON slicing: {str(e)}")
                return {"status": "error", "message": f"Slicing error: {str(e)}"}
            
            # Create a list to hold the normalized data
            normalized_data = []
            record_count = 0
            
            # Process each record with better error handling
            try:
                for record in json_data:
                    record_count += 1
                    if record_count % 1000 == 0:
                        print(f"Processed {record_count} records...")
                        
                    if 'manufacturers' in record:
                        # Handle nested structure with manufacturers array
                        for mfr in record['manufacturers']:
                            manufacturer = mfr.get('manufacturer_name', '')
                            reference_url = mfr.get('reference', '')
                            models = mfr.get('models', [])
                            total_units = mfr.get('total_units_sold', 0)
                            
                            if models:
                                for model in models:
                                    model_name = model.get('model_name', '')
                                    model_units = model.get('units_sold', 0)
                                    
                                    normalized_data.append({
                                        'manufacturer_name': manufacturer,
                                        'month': record.get('month', 0),
                                        'year': record.get('year', 0),
                                        'total_units_sold': total_units,
                                        'model_name': model_name,
                                        'model_units_sold': model_units,
                                        'url': reference_url
                                    })
                            else:
                                normalized_data.append({
                                    'manufacturer_name': manufacturer,
                                    'month': record.get('month', 0),
                                    'year': record.get('year', 0),
                                    'total_units_sold': total_units,
                                    'model_name': '',
                                    'model_units_sold': 0,
                                    'url': reference_url
                                })
                    else:
                        # Handle flat structure
                        manufacturer = record.get('manufacturer_name', '')
                        month = record.get('month', 0)
                        year = record.get('year', 0)
                        total_units = record.get('total_units_sold', 0)
                        reference_url = record.get('reference', '')  # Get reference URL
                        
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
                                    'model_units_sold': model_units,
                                    'url': reference_url  # Save reference URL
                                })
                        else:
                            # Create a row with empty model data
                            normalized_data.append({
                                'manufacturer_name': manufacturer,
                                'month': month,
                                'year': year,
                                'total_units_sold': total_units,
                                'model_name': '',
                                'model_units_sold': 0,
                                'url': reference_url  # Save reference URL
                            })
            
                print(f"Successfully processed all {record_count} records")
                print(f"Generated {len(normalized_data)} normalized data records")
                
            except Exception as e:
                print(f"Error processing record {record_count}: {str(e)}")
                if record_count > 0:
                    print(f"Sample record data: {json.dumps(json_data[record_count-1], indent=2)[:500]}")
                return {"status": "error", "message": f"Record processing error: {str(e)}"}
            
            # Convert to DataFrame with error handling
            try:
                df = pd.DataFrame(normalized_data)
                print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
                print(f"Columns: {', '.join(df.columns.tolist())}")
            except Exception as e:
                print(f"Error creating DataFrame: {str(e)}")
                return {"status": "error", "message": f"DataFrame creation error: {str(e)}"}
            
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
        print(f"Columns in data: {', '.join(df.columns)}")
        
        # Save to CSV with URL included if this was a JSON file
        if csv_file_path.endswith('.json'):
            csv_output_path = csv_file_path.replace('.json', '.csv')
            print(f"Saving normalized data with URLs to {csv_output_path}")
            df.to_csv(csv_output_path, index=False)
        
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
                    
                    # Add URL if it exists in the record
                    if 'url' in record:
                        formatted_record["url"] = str(record.get("url", ""))
                    
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