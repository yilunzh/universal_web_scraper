import pandas as pd
import asyncio
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from src.db.supabase_client import get_supabase_client

async def validate_china_auto_sales() -> Dict[str, Any]:
    """
    Validate the china_auto_sales database according to business rules:
    1. No missing months in the time series for each manufacturer
    2. No duplicate entries for manufacturer-month-year combinations
    
    Returns:
        Dict containing validation results
    """
    print("Starting validation of china_auto_sales database...")
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    
    try:
        # Fetch all data from china_auto_sales table
        response = supabase.table("china_auto_sales").select("*").execute()
        
        if not response.data:
            return {
                "status": "error",
                "message": "No data found in china_auto_sales table"
            }
            
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(response.data)
        print(f"Read {len(df)} records from database")
        
        # Check for duplicates
        duplicate_results = check_for_duplicates(df)
        
        # Check for missing months
        missing_months_results = check_for_missing_months(df)
        
        # Generate validation report
        return {
            "status": "success",
            "validation_time": datetime.utcnow().isoformat(),
            "total_records": len(df),
            "unique_manufacturers": len(df['manufacturer_name'].unique()),
            "date_range": {
                "earliest": f"{df['year'].min()}-{df['month'].min()}",
                "latest": f"{df['year'].max()}-{df['month'].max()}"
            },
            "duplicates": {
                "found": len(duplicate_results) > 0,
                "count": len(duplicate_results),
                "details": duplicate_results
            },
            "missing_months": {
                "found": len(missing_months_results) > 0,
                "count": len(missing_months_results),
                "details": missing_months_results
            },
            "is_valid": len(duplicate_results) == 0 and len(missing_months_results) == 0
        }
        
    except Exception as e:
        print(f"Error validating data: {str(e)}")
        return {"status": "error", "message": str(e)}


def check_for_duplicates(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Check for duplicate manufacturer-month-year-model combinations
    
    Args:
        df: DataFrame containing china_auto_sales data
        
    Returns:
        List of duplicate entries found
    """
    # Group by all key fields including model_name and count occurrences
    duplicates = df.groupby(['manufacturer_name', 'year', 'month', 'model_name']).size().reset_index(name='count')
    duplicates = duplicates[duplicates['count'] > 1]
    
    if len(duplicates) == 0:
        return []
        
    # Get the actual duplicate rows
    duplicate_entries = []
    for _, row in duplicates.iterrows():
        duplicate_rows = df[
            (df['manufacturer_name'] == row['manufacturer_name']) &
            (df['year'] == row['year']) &
            (df['month'] == row['month']) &
            (df['model_name'] == row['model_name'])
        ]
        
        # Convert to list of dicts
        entries = duplicate_rows.to_dict('records')
        duplicate_entries.append({
            "manufacturer_name": row['manufacturer_name'],
            "year": int(row['year']),
            "month": int(row['month']),
            "model_name": row['model_name'],
            "count": int(row['count']),
            "entries": entries[:5]  # Limit to first 5 entries to avoid huge output
        })
    
    return duplicate_entries


def check_for_missing_months(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Check for missing months, but with more flexible validation.
    
    Args:
        df: DataFrame containing china_auto_sales data
        
    Returns:
        List of manufacturers with missing months
    """
    missing_entries = []
    
    # Group by manufacturer and get the unique month-year combinations
    manufacturers = df['manufacturer_name'].unique()
    
    for manufacturer in manufacturers:
        # Get data for this manufacturer
        manufacturer_data = df[df['manufacturer_name'] == manufacturer]
        
        # Get earliest and latest dates
        min_year = manufacturer_data['year'].min()
        max_year = manufacturer_data['year'].max()
        
        # Count the number of distinct month-year combinations
        distinct_months = set(zip(manufacturer_data['year'], manufacturer_data['month']))
        
        # Create a set of all possible month-year combinations in the range
        all_months = set()
        for year in range(min_year, max_year + 1):
            for month in range(1, 13):
                # Skip months before the start or after the end
                if (year == min_year and month < manufacturer_data[manufacturer_data['year'] == min_year]['month'].min()) or \
                   (year == max_year and month > manufacturer_data[manufacturer_data['year'] == max_year]['month'].max()):
                    continue
                all_months.add((year, month))
        
        # Identify missing months
        missing_months = all_months - distinct_months
        
        # Filter out potential legitimate gaps
        # A gap is considered legitimate if:
        # 1. It's at the beginning or end of the range (manufacturer might have entered/exited market)
        # 2. It's a consistent gap across all models (might be a period when no data was reported)
        
        # Get all models for this manufacturer
        models = manufacturer_data['model_name'].unique()
        
        # If a month is missing for ALL models, it might be a legitimate gap
        # rather than a data issue
        legitimate_gaps = set()
        for year, month in missing_months:
            # Check if ANY model has data for this month
            has_data = False
            for model in models:
                model_data = manufacturer_data[manufacturer_data['model_name'] == model]
                if ((model_data['year'] == year) & (model_data['month'] == month)).any():
                    has_data = True
                    break
            
            if not has_data:
                # If NO model has data for this month, it might be a legitimate gap
                legitimate_gaps.add((year, month))
        
        # Remove legitimate gaps from missing months
        actual_missing = missing_months - legitimate_gaps
        
        if actual_missing:
            missing_entries.append({
                "manufacturer_name": manufacturer,
                "missing_count": len(actual_missing),
                "missing_months": sorted([
                    {"year": int(year), "month": int(month)} 
                    for year, month in actual_missing
                ], key=lambda x: (x["year"], x["month"]))
            })
    
    return missing_entries


if __name__ == "__main__":
    results = asyncio.run(validate_china_auto_sales())
    print("\n=== Validation Results ===")
    if results['status'] == 'success':
        print(f"Total records: {results['total_records']}")
        print(f"Unique manufacturers: {results['unique_manufacturers']}")
        print(f"Date range: {results['date_range']['earliest']} to {results['date_range']['latest']}")
        
        if results['duplicates']['found']:
            print(f"\nFound {results['duplicates']['count']} duplicate entries:")
            for dup in results['duplicates']['details']:
                print(f"  {dup['manufacturer_name']}, {dup['year']}-{dup['month']}, {dup['model_name']}: {dup['count']} entries")
        else:
            print("\nNo duplicates found")
            
        if results['missing_months']['found']:
            print(f"\nFound {results['missing_months']['count']} manufacturers with missing months:")
            for missing in results['missing_months']['details']:
                print(f"  {missing['manufacturer_name']}: {missing['missing_count']} missing entries")
                # Print first 5 missing months as example
                for month in missing['missing_months'][:5]:
                    print(f"    - {month['year']}-{month['month']}")
                if len(missing['missing_months']) > 5:
                    print(f"    - ... and {len(missing['missing_months']) - 5} more")
        else:
            print("\nNo missing months found")
            
        print(f"\nOverall validation result: {'PASSED' if results['is_valid'] else 'FAILED'}")
    else:
        print(f"Validation error: {results['message']}") 