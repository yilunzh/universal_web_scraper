#!/usr/bin/env python3
import argparse
import asyncio
import sys
from pathlib import Path
import pandas as pd
import os

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.import_data import import_auto_sales_data_to_supabase

async def main():
    parser = argparse.ArgumentParser(description="Import auto sales data from CSV to Supabase")
    parser.add_argument(
        "--csv-file", 
        required=False,
        help="Path to the CSV file to import (required for Supabase import)"
    )
    parser.add_argument(
        "--no-upsert",
        action="store_true",
        help="Use insert instead of upsert (may create duplicates)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of rows to import (default: import all rows)"
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Number of rows to skip from the beginning (default: 0)"
    )
    parser.add_argument(
        "--month-codes",
        nargs='+',
        help="Specific month codes to import/update (e.g., '86 87 88' or '86,87,88'). If not provided, all months will be processed."
    )
    parser.add_argument(
        "--input-file",
        default="data/output/china_monthly_auto_sales_data_v2.csv",
        help="Input file containing scraped data (default: data/output/china_monthly_auto_sales_data_v2.csv)"
    )
    parser.add_argument(
        "--output-file",
        default="data/output/china_monthly_auto_sales_data_v2.csv",
        help="Output file for processed data (default: data/output/china_monthly_auto_sales_data_v2.csv)"
    )
    parser.add_argument(
        "--process-local",
        action="store_true",
        help="Process local CSV files (filtering and upsert)"
    )
    args = parser.parse_args()
    
    # Process month codes if provided
    month_codes = []
    if args.month_codes:
        # Process the list of month codes
        for code_arg in args.month_codes:
            # Handle comma-separated values
            if ',' in code_arg:
                month_codes.extend([code.strip() for code in code_arg.split(',') if code.strip()])
            else:
                if code_arg.strip():
                    month_codes.append(code_arg.strip())
        print(f"Processing specified month codes: {', '.join(month_codes)}")
        
        # Load month code mapping from CSV
        month_mapping_file = Path(project_root) / "data/input/month_code.csv"
        print(f"Reading month code mapping from {month_mapping_file}")
        month_mapping = pd.read_csv(month_mapping_file)
        
        # Add debugging information
        print(f"Month mapping columns: {month_mapping.columns.tolist()}")
        print(f"First few rows of month mapping:")
        print(month_mapping.head())
        print(f"Data types: {month_mapping.dtypes}")

        # Check if the month codes exist in any format
        print("Checking if month codes exist in any column...")
        for col in month_mapping.columns:
            for code in month_codes:
                matches = month_mapping[month_mapping[col].astype(str) == code]
                if not matches.empty:
                    print(f"Found code {code} in column '{col}': {len(matches)} matches")

        # If the expected column doesn't exist, try to find an alternative
        if 'month_year_code' not in month_mapping.columns:
            print("Column 'month_year_code' not found! Available columns:", month_mapping.columns.tolist())
            
            # Try to identify the correct column name for month codes
            likely_columns = []
            for col in month_mapping.columns:
                if "code" in col.lower() or "id" in col.lower():
                    likely_columns.append(col)
            
            if likely_columns:
                print(f"Possible month code columns: {likely_columns}")
                print("Using column:", likely_columns[0])
                month_mapping_column = likely_columns[0]
            else:
                # If we can't find a likely column, use the first column
                print("No likely month code column found, using first column:", month_mapping.columns[0])
                month_mapping_column = month_mapping.columns[0]
        else:
            month_mapping_column = 'month_year_code'
        
        # Filter the mapping to get only the requested month codes
        relevant_months = month_mapping[month_mapping[month_mapping_column].astype(str).isin(month_codes)]
        
        if len(relevant_months) == 0:
            print(f"Error: No matching months found for codes {', '.join(month_codes)}")
            return
            
        print(f"Found {len(relevant_months)} matching month entries:")
        for _, row in relevant_months.iterrows():
            print(f"  Code {row[month_mapping_column]}: {row['month']}/{row['year']}")
    
    # Supabase import (if --csv-file is provided)
    if args.csv_file:
        # Read the CSV file into a DataFrame
        input_data = pd.read_csv(args.csv_file)
        print(f"Read {len(input_data)} records from {args.csv_file}")
        
        # Check column names
        print(f"Available columns: {input_data.columns.tolist()}")
        
        # Filter by month codes if specified
        if month_codes and len(relevant_months) > 0:
            print(f"Filtering data for month codes: {', '.join(month_codes)}")
            
            # Try different strategies to filter
            # Strategy 1: If month_year_code exists directly
            if 'month_year_code' in input_data.columns:
                filtered_data = input_data[input_data['month_year_code'].astype(str).isin(month_codes)]
            # Strategy 2: If separate month and year columns exist
            elif 'month' in input_data.columns and 'year' in input_data.columns:
                # Create a list of (month, year) tuples from the relevant_months
                month_year_pairs = list(zip(relevant_months['month'], relevant_months['year']))
                
                # Create a mask for matching rows
                mask = False
                for month, year in month_year_pairs:
                    mask = mask | ((input_data['month'] == month) & (input_data['year'] == year))
                
                filtered_data = input_data[mask]
            else:
                print("Could not find appropriate columns for filtering")
                return
                
            print(f"After filtering: {len(filtered_data)} records")
            
            # Save filtered data to a temporary file for Supabase import
            temp_file = f"{args.csv_file}.filtered.csv"
            filtered_data.to_csv(temp_file, index=False)
            print(f"Saved filtered data to {temp_file} for import")
            
            # Use the filtered file for Supabase import
            csv_file_path = temp_file
        else:
            # Use the original file if no filtering
            csv_file_path = args.csv_file
        
        # Run the import process with upsert by default
        print(f"Importing data to Supabase...")
        result = await import_auto_sales_data_to_supabase(
            csv_file_path=csv_file_path, 
            upsert=not args.no_upsert,
            row_limit=args.limit,
            start_row=args.skip
        )
        
        # Clean up temporary file if it was created
        if month_codes and os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Removed temporary file {temp_file}")
        
        # Print results
        if result["status"] == "success":
            print("\n✅ Import completed successfully!")
            print(f"Total records processed: {result['total_records']}")
            print(f"Records imported: {result['successful_imports']}")
            print(f"Operation used: {result['operation']}")
            if args.skip > 0:
                print(f"Skipped first {args.skip} rows")
        elif result["status"] == "partial":
            print("\n⚠️ Import completed with some failures")
            print(f"Total records: {result['total_records']}")
            print(f"Successfully imported: {result['successful_imports']}")
            print(f"Failed to import: {result['failed_imports']}")
            print(f"Operation used: {result['operation']}")
            if args.skip > 0:
                print(f"Skipped first {args.skip} rows")
        else:
            print(f"\n❌ Import failed: {result['message']}")
    
    # Local file processing (only if --process-local flag is set)
    if args.process_local:
        # Check if input file exists before processing
        input_file = Path(project_root) / args.input_file
        if not input_file.exists():
            print(f"Error: Input file not found: {input_file}")
            print("Skipping local file processing. Use --input-file to specify a different file.")
            return
            
        print(f"Reading data from {input_file}")
        input_data = pd.read_csv(input_file)
        
        # Filter by month codes if specified
        if month_codes:
            print(f"Filtering data for month codes: {', '.join(month_codes)}")
            input_data = input_data[input_data['month_code'].astype(str).isin(month_codes)]
            if len(input_data) == 0:
                print("No data found for specified month codes")
                return
            print(f"Found {len(input_data)} records for specified month codes")
        
        # Read existing output data if file exists
        output_file = Path(project_root) / args.output_file
        if output_file.exists():
            print(f"Reading existing data from {output_file}")
            existing_data = pd.read_csv(output_file)
            
            # Identify primary key columns for the upsert
            # This depends on your data schema - adjust as needed
            key_columns = ['manufacturer_code', 'month_code']
            
            # Perform upsert operation
            print("Performing upsert operation...")
            
            # Create a copy of existing data
            updated_data = existing_data.copy()
            
            # Identify records to update (exist in both dataframes)
            for _, new_row in input_data.iterrows():
                # Create a filter for matching keys
                match_filter = True
                for key in key_columns:
                    match_filter = match_filter & (existing_data[key] == new_row[key])
                
                # If match found, update the record
                if match_filter.any():
                    # Get the index in the existing data
                    idx = existing_data[match_filter].index[0]
                    # Update all columns with new values
                    for col in new_row.index:
                        updated_data.at[idx, col] = new_row[col]
                else:
                    # If no match, append the new record
                    updated_data = pd.concat([updated_data, pd.DataFrame([new_row])], ignore_index=True)
                
            # Sort the data (adjust columns as needed)
            if 'month_code' in updated_data.columns:
                updated_data = updated_data.sort_values(['manufacturer_code', 'month_code'])
        else:
            print(f"No existing data found at {output_file}, creating new file")
            updated_data = input_data
        
        # Save the updated data
        print(f"Saving {len(updated_data)} records to {output_file}")
        updated_data.to_csv(output_file, index=False)
        print("Import completed successfully")

if __name__ == "__main__":
    asyncio.run(main()) 