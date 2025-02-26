#!/usr/bin/env python3
import argparse
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.import_data import import_auto_sales_data_to_supabase

async def main():
    parser = argparse.ArgumentParser(description="Import auto sales data from CSV to Supabase")
    parser.add_argument(
        "--csv-file", 
        required=True,
        help="Path to the CSV file to import"
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
    args = parser.parse_args()
    
    # Run the import process with upsert by default
    result = await import_auto_sales_data_to_supabase(
        csv_file_path=args.csv_file, 
        upsert=not args.no_upsert,
        row_limit=args.limit,
        start_row=args.skip
    )
    
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

if __name__ == "__main__":
    asyncio.run(main()) 