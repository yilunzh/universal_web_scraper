#!/usr/bin/env python3
import pandas as pd
import argparse
import sys
from pathlib import Path
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def analyze_csv_data(csv_file_path):
    """Analyze CSV data for completeness"""
    
    # Read the CSV file
    print(f"Reading CSV file: {csv_file_path}")
    df = pd.read_csv(csv_file_path)
    
    print(f"Total records: {len(df)}")
    print(f"Unique manufacturers: {len(df['manufacturer_name'].unique())}")
    
    # Get range of dates
    min_year = df['year'].min()
    max_year = df['year'].max()
    min_month = df[df['year'] == min_year]['month'].min()
    max_month = df[df['year'] == max_year]['month'].max()
    
    print(f"Date range: {min_year}-{min_month} to {max_year}-{max_month}")
    
    # Check if all manufacturers have all months
    manufacturers = df['manufacturer_name'].unique()
    
    # For each manufacturer
    manufacturer_stats = []
    for manufacturer in manufacturers:
        manufacturer_data = df[df['manufacturer_name'] == manufacturer]
        
        man_min_year = manufacturer_data['year'].min()
        man_max_year = manufacturer_data['year'].max()
        man_min_month = manufacturer_data[manufacturer_data['year'] == man_min_year]['month'].min()
        man_max_month = manufacturer_data[manufacturer_data['year'] == man_max_year]['month'].max()
        
        # Calculate how many months should be in the range
        total_months = (man_max_year - man_min_year) * 12 + (man_max_month - man_min_month + 1)
        
        # Get actual number of months
        actual_months = len(manufacturer_data.groupby(['year', 'month']))
        
        # Get list of unique models for this manufacturer
        unique_models = manufacturer_data['model_name'].unique().tolist()
        
        manufacturer_stats.append({
            "manufacturer": manufacturer,
            "date_range": f"{man_min_year}-{man_min_month} to {man_max_year}-{man_max_month}",
            "expected_months": total_months,
            "actual_months": actual_months,
            "completeness": round(actual_months / total_months * 100, 2),
            "unique_models": len(unique_models),
            "models": unique_models
        })
    
    # Sort by completeness (ascending)
    manufacturer_stats.sort(key=lambda x: x["completeness"])
    
    # Print manufacturers with incomplete data
    print("\nManufacturers with incomplete data:")
    incomplete = [m for m in manufacturer_stats if m["completeness"] < 100]
    
    for manufacturer in incomplete[:10]:  # Show only first 10
        print(f"  {manufacturer['manufacturer']}: {manufacturer['actual_months']}/{manufacturer['expected_months']} months " +
              f"({manufacturer['completeness']}% complete), {manufacturer['unique_models']} models")
    
    if len(incomplete) > 10:
        print(f"  ... and {len(incomplete) - 10} more manufacturers with incomplete data")
    
    # Save detailed report
    report = {
        "total_records": len(df),
        "unique_manufacturers": len(manufacturers),
        "date_range": f"{min_year}-{min_month} to {max_year}-{max_month}",
        "manufacturer_stats": manufacturer_stats
    }
    
    output_file = Path("logs") / "data_completeness_report.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to {output_file}")
    
    return report

def main():
    parser = argparse.ArgumentParser(description="Check completeness of auto sales data")
    parser.add_argument(
        "--csv-file", 
        required=True,
        help="Path to the CSV file to analyze"
    )
    args = parser.parse_args()
    
    analyze_csv_data(args.csv_file)

if __name__ == "__main__":
    main() 