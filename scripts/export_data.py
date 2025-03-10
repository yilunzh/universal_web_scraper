#!/usr/bin/env python3
"""
Script to export china_monthly_auto_sales_data_v2.json to CSV format.
Ensures data is exported to the /data/output directory with the specified column headers.
"""

import sys
import os
import json
import csv
from pathlib import Path

# Get the project root and add it to the path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def export_json_to_csv(json_file_path, csv_file_path):
    """
    Exports JSON data to CSV format with specific headings.
    
    Args:
        json_file_path: Path to the JSON file
        csv_file_path: Path to save the CSV file
    """
    print(f"Exporting data from {json_file_path} to {csv_file_path}...")
    
    try:
        # Read the JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        manufacturers = data.get('value', [])
        if not manufacturers:
            print("No data to export")
            return
            
        # Create CSV with the exact headers requested
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            # Define exact header names as requested
            fieldnames = [
                'manufacturer_name', 
                'month', 
                'year', 
                'total_units_sold', 
                'model_name', 
                'model_units_sold', 
                'url'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write each model's data
            for mfr in manufacturers:
                manufacturer_name = mfr.get('manufacturer_name')
                month = mfr.get('month')
                year = mfr.get('year')
                total_units_sold = mfr.get('total_units_sold')
                reference = mfr.get('reference')  # URL
                
                for model in mfr.get('models', []):
                    writer.writerow({
                        'manufacturer_name': manufacturer_name,
                        'month': month,
                        'year': year,
                        'total_units_sold': total_units_sold,
                        'model_name': model.get('model_name'),
                        'model_units_sold': model.get('units_sold'),
                        'url': reference
                    })
        
        print(f"Successfully exported data to {csv_file_path} with the following headers:")
        print(", ".join(fieldnames))
            
    except Exception as e:
        print(f"Error exporting data to CSV: {e}")

def main():
    """Export the latest auto sales data to CSV format."""
    
    # Ensure output directory exists
    output_dir = project_root / "data/output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Default file paths in the data/output directory
    json_file = output_dir / "china_monthly_auto_sales_data_v2.json"
    csv_file = output_dir / "china_monthly_auto_sales_data_v2.csv"
    
    # Allow custom paths via command line arguments
    if len(sys.argv) > 1:
        json_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        csv_file = Path(sys.argv[2])
        
        # If a custom CSV path is provided, ensure it's in the data/output directory
        if not str(csv_file).startswith(str(output_dir)):
            csv_file = output_dir / csv_file.name
            print(f"Redirecting output to data/output directory: {csv_file}")
    
    # Check if JSON file exists
    if not os.path.exists(json_file):
        print(f"Error: JSON file not found at {json_file}")
        sys.exit(1)
    
    try:
        # Export the data
        export_json_to_csv(json_file, csv_file)
        
        # Verify the output file exists in the data/output directory
        if os.path.exists(csv_file):
            print(f"✅ CSV file successfully created in the data/output directory:")
            print(f"   {csv_file}")
        else:
            print("❌ Failed to create the CSV file")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error exporting data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 