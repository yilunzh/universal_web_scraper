#!/usr/bin/env python3
"""
Script to clean the auto sales data files (JSON and CSV) based on validation rules.
"""

import json
import pandas as pd
import os
from pathlib import Path
import argparse

# Get the project root
project_root = Path(__file__).resolve().parent.parent

def clean_json_data(json_file_path, output_file_path=None):
    """
    Clean the JSON data file by removing problematic entries.
    
    Args:
        json_file_path: Path to the JSON file
        output_file_path: Optional path for the cleaned output file
    
    Returns:
        dict: Statistics about the cleaning process
    """
    print(f"Cleaning JSON data from {json_file_path}")
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"File not found: {json_file_path}")
    
    # If no output path specified, create a backup and overwrite original
    if output_file_path is None:
        backup_path = json_file_path.replace('.json', '_backup.json')
        os.system(f"cp {json_file_path} {backup_path}")
        print(f"Created backup at {backup_path}")
        output_file_path = json_file_path
    
    # Load the JSON data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return {"status": "error", "message": f"JSON decode error: {e}"}
    
    # Handle different JSON structures
    if isinstance(data, dict) and 'value' in data:
        records = data['value']
    elif isinstance(data, list):
        records = data
    else:
        print(f"Unexpected JSON structure. Expected list or dict with 'value' key.")
        return {"status": "error", "message": "Unexpected JSON structure"}
    
    initial_count = len(records)
    print(f"Found {initial_count} records")
    
    # Apply filters to clean the data
    filtered_records = []
    excluded_records = {
        "summary_rows": 0,
        "specific_models": 0,
        "missing_url": 0,
        "duplicates": 0,
        "problematic_manufacturer": 0
    }
    
    # Track unique manufacturer/month/year combinations to detect duplicates
    unique_combinations = {}
    
    for record in records:
        should_exclude = False
        exclusion_reason = None
        
        # Skip records with missing URL
        if 'reference' not in record or not record['reference']:
            excluded_records["missing_url"] += 1
            continue
        
        # Check for problematic manufacturer name
        if 'manufacturer_name' in record:
            mfr_name = record['manufacturer_name']
            if any(problem_name in mfr_name for problem_name in ['VGV', '长安佳程']):
                excluded_records["problematic_manufacturer"] += 1
                should_exclude = True
                exclusion_reason = f"Problematic manufacturer name: {mfr_name}"
        
        # Check for problematic models in the models array
        if not should_exclude and 'models' in record and isinstance(record['models'], list):
            for model in record['models']:
                model_name = model.get('model_name', '')
                
                # Check for summary rows
                if any(summary_term in model_name for summary_term in ['合计', '总计', 'Total']):
                    excluded_records["summary_rows"] += 1
                    should_exclude = True
                    exclusion_reason = f"Summary model found: {model_name}"
                    break
                
                # Check for specific problematic models
                if model_name in ['VGV', '长安佳程']:
                    excluded_records["specific_models"] += 1
                    should_exclude = True
                    exclusion_reason = f"Problematic model found: {model_name}"
                    break
        
        # Check for problematic model_name in flat structure
        if not should_exclude and 'model_name' in record:
            model_name = record['model_name']
            
            # Check for summary rows
            if any(summary_term in model_name for summary_term in ['合计', '总计', 'Total']):
                excluded_records["summary_rows"] += 1
                should_exclude = True
                exclusion_reason = f"Summary model found: {model_name}"
            
            # Check for specific problematic models
            elif model_name in ['VGV', '长安佳程']:
                excluded_records["specific_models"] += 1
                should_exclude = True
                exclusion_reason = f"Problematic model found: {model_name}"
        
        # Check for duplicates where model_name equals manufacturer_name
        if not should_exclude and 'manufacturer_name' in record and 'model_name' in record and 'month' in record and 'year' in record:
            if record['model_name'] == record['manufacturer_name']:
                key = (record['manufacturer_name'], record['month'], record['year'])
                if key in unique_combinations:
                    excluded_records["duplicates"] += 1
                    should_exclude = True
                    exclusion_reason = f"Duplicate record for {key}"
                else:
                    unique_combinations[key] = True
        
        # If the record has any issues, log it and skip it
        if should_exclude:
            print(f"Excluding record: {exclusion_reason}")
            if 'manufacturer_name' in record:
                print(f"  Manufacturer: {record['manufacturer_name']}")
            if 'month' in record and 'year' in record:
                print(f"  Period: {record['month']}/{record['year']}")
            continue
        
        # Record passed all checks, keep it
        filtered_records.append(record)
    
    # Create output structure matching the input
    if isinstance(data, dict) and 'value' in data:
        output_data = data.copy()
        output_data['value'] = filtered_records
    else:
        output_data = filtered_records
    
    # Write the cleaned data
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    removed_count = initial_count - len(filtered_records)
    print(f"Cleaned JSON data: removed {removed_count} of {initial_count} records")
    print(f"Breakdown of removed records:")
    for category, count in excluded_records.items():
        if count > 0:
            print(f"  - {category}: {count}")
    
    return {
        "status": "success",
        "initial_count": initial_count,
        "final_count": len(filtered_records),
        "removed_count": removed_count,
        "excluded_breakdown": excluded_records
    }

def clean_csv_data(csv_file_path, output_file_path=None):
    """
    Clean the CSV data file by removing problematic entries.
    
    Args:
        csv_file_path: Path to the CSV file
        output_file_path: Optional path for the cleaned output file
    
    Returns:
        dict: Statistics about the cleaning process
    """
    print(f"Cleaning CSV data from {csv_file_path}")
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"File not found: {csv_file_path}")
    
    # If no output path specified, create a backup and overwrite original
    if output_file_path is None:
        backup_path = csv_file_path.replace('.csv', '_backup.csv')
        os.system(f"cp {csv_file_path} {backup_path}")
        print(f"Created backup at {backup_path}")
        output_file_path = csv_file_path
    
    # Load the CSV data
    try:
        df = pd.read_csv(csv_file_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return {"status": "error", "message": f"CSV read error: {e}"}
    
    initial_count = len(df)
    print(f"Found {initial_count} records")
    
    # Apply filters to clean the data
    # 1. Remove summary rows
    summary_mask = df['model_name'].str.contains('合计|总计|Total', na=False)
    summary_count = summary_mask.sum()
    
    # 2. Remove specific problematic models
    specific_models_mask = df['model_name'].isin(['VGV', '长安佳程'])
    specific_models_count = specific_models_mask.sum()
    
    # Check for URL column - it might be either 'url' or 'reference'
    url_column = 'url' if 'url' in df.columns else 'reference' if 'reference' in df.columns else None
    
    if url_column is None:
        print("Warning: No URL column found in CSV!")
        missing_url_mask = pd.Series(False, index=df.index)
        missing_url_count = 0
    else:
        # 3. Remove entries with missing URL
        missing_url_mask = df[url_column].isna() | (df[url_column] == '')
        missing_url_count = missing_url_mask.sum()
    
    # 4. Handle duplicates where model_name equals manufacturer_name
    duplicate_mask = (df['model_name'] == df['manufacturer_name'])
    # For these, we need to check if there are duplicates for the mfr/month/year combo
    duplicate_combos = df[duplicate_mask].groupby(['manufacturer_name', 'month', 'year']).size()
    duplicate_combos = duplicate_combos[duplicate_combos > 1].reset_index()
    
    # Create a mask for these duplicate combinations
    dup_records_to_remove = pd.DataFrame(columns=df.columns)
    for _, row in duplicate_combos.iterrows():
        matching_records = df[
            (df['manufacturer_name'] == row['manufacturer_name']) &
            (df['month'] == row['month']) &
            (df['year'] == row['year']) &
            (df['model_name'] == df['manufacturer_name'])
        ]
        dup_records_to_remove = pd.concat([dup_records_to_remove, matching_records])
    
    duplicates_count = len(dup_records_to_remove)
    
    # Apply all filters
    clean_df = df[
        ~summary_mask & 
        ~specific_models_mask & 
        ~missing_url_mask & 
        ~df.index.isin(dup_records_to_remove.index)
    ]
    
    # Write the cleaned data
    clean_df.to_csv(output_file_path, index=False)
    
    removed_count = initial_count - len(clean_df)
    print(f"Cleaned CSV data: removed {removed_count} of {initial_count} records")
    print(f"Breakdown of removed records:")
    print(f"  - summary_rows: {summary_count}")
    print(f"  - specific_models: {specific_models_count}")
    print(f"  - missing_url: {missing_url_count}")
    print(f"  - duplicates: {duplicates_count}")
    
    return {
        "status": "success",
        "initial_count": initial_count,
        "final_count": len(clean_df),
        "removed_count": removed_count,
        "excluded_breakdown": {
            "summary_rows": int(summary_count),
            "specific_models": int(specific_models_count),
            "missing_url": int(missing_url_count),
            "duplicates": duplicates_count
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Clean auto sales data files')
    parser.add_argument('--json', default=str(project_root / 'data/output/china_monthly_auto_sales_data_v2.json'),
                        help='Path to the JSON data file')
    parser.add_argument('--csv', default=str(project_root / 'data/output/china_monthly_auto_sales_data_v2.csv'),
                        help='Path to the CSV data file')
    parser.add_argument('--output-json', default=None,
                        help='Path for cleaned JSON output (default: overwrite original)')
    parser.add_argument('--output-csv', default=None,
                        help='Path for cleaned CSV output (default: overwrite original)')
    parser.add_argument('--json-only', action='store_true',
                        help='Clean only the JSON file')
    parser.add_argument('--csv-only', action='store_true',
                        help='Clean only the CSV file')
    args = parser.parse_args()
    
    if not args.csv_only:
        json_result = clean_json_data(args.json, args.output_json)
        print("JSON cleaning completed with status:", json_result["status"])
    
    if not args.json_only:
        csv_result = clean_csv_data(args.csv, args.output_csv)
        print("CSV cleaning completed with status:", csv_result["status"])
    
    print("Cleaning process complete")

if __name__ == "__main__":
    main() 