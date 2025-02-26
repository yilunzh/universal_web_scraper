#!/usr/bin/env python3
import pandas as pd
import argparse
import sys
from pathlib import Path
import json
import asyncio

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.db.supabase_client import get_supabase_client

async def compare_source_vs_db(csv_file_path):
    """Compare source data with database entries"""
    
    # Read the CSV file
    print(f"Reading CSV file: {csv_file_path}")
    source_df = pd.read_csv(csv_file_path)
    
    print(f"Source data total records: {len(source_df)}")
    
    # Create unique identifiers for source data
    source_df['identifier'] = source_df.apply(
        lambda row: f"{row['manufacturer_name']}_{row['year']}_{row['month']}_{row['model_name']}",
        axis=1
    )
    source_identifiers = set(source_df['identifier'].unique())
    
    # Query the database
    print("Querying database...")
    supabase = get_supabase_client()
    
    # Get all records from the database
    response = supabase.table("china_auto_sales").select("*").execute()
    
    if not response.data:
        print("No data found in database!")
        return
    
    db_df = pd.DataFrame(response.data)
    print(f"Database total records: {len(db_df)}")
    
    # Create identifiers for database records
    db_df['identifier'] = db_df.apply(
        lambda row: f"{row['manufacturer_name']}_{row['year']}_{row['month']}_{row['model_name']}",
        axis=1
    )
    db_identifiers = set(db_df['identifier'].unique())
    
    # Find missing records
    missing_in_db = source_identifiers - db_identifiers
    extra_in_db = db_identifiers - source_identifiers
    
    print(f"\nRecords in source but not in DB: {len(missing_in_db)}")
    print(f"Records in DB but not in source: {len(extra_in_db)}")
    
    # Analyze missing records by manufacturer
    if missing_in_db:
        missing_records = source_df[source_df['identifier'].isin(missing_in_db)]
        missing_by_manufacturer = missing_records.groupby('manufacturer_name').size().reset_index(name='count')
        missing_by_manufacturer = missing_by_manufacturer.sort_values(by='count', ascending=False)
        
        print("\nTop manufacturers with missing records:")
        for _, row in missing_by_manufacturer.head(10).iterrows():
            print(f"  {row['manufacturer_name']}: {row['count']} records")
        
        # Look at patterns in missing data
        print("\nAnalyzing patterns in missing data...")
        missing_by_year_month = missing_records.groupby(['year', 'month']).size().reset_index(name='count')
        missing_by_year_month = missing_by_year_month.sort_values(by=['year', 'month'])
        
        print("Missing records by year-month:")
        for _, row in missing_by_year_month.head(20).iterrows():
            print(f"  {row['year']}-{row['month']}: {row['count']} records")
    
    # Save detailed report
    output_file = Path("logs") / "db_comparison_report.json"
    output_file.parent.mkdir(exist_ok=True)
    
    report = {
        "source_records": len(source_df),
        "db_records": len(db_df),
        "missing_in_db": len(missing_in_db),
        "extra_in_db": len(extra_in_db),
        "missing_identifiers": list(missing_in_db)[:100],  # Limit to first 100
        "extra_identifiers": list(extra_in_db)[:100]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to {output_file}")

async def main():
    parser = argparse.ArgumentParser(description="Compare source data with database")
    parser.add_argument(
        "--csv-file", 
        required=True,
        help="Path to the CSV file to compare"
    )
    args = parser.parse_args()
    
    await compare_source_vs_db(args.csv_file)

if __name__ == "__main__":
    asyncio.run(main()) 