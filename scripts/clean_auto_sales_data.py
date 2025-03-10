#!/usr/bin/env python3
"""
Script to clean the auto sales data files (JSON and CSV) based on validation rules.
When manufacturer names don't match with manufacturer_code.csv, it identifies problematic
manufacturer/month combinations and provides commands to rescrape them using submit_manufacturer_job.py.
"""

import json
import pandas as pd
import os
import sys
import subprocess
from pathlib import Path
import argparse
from collections import defaultdict
import csv

# Get the project root
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def load_valid_manufacturers():
    """
    Load the list of valid manufacturer names from manufacturer_code.csv.
    
    Returns:
        dict: Mapping of manufacturer codes to names
        dict: Mapping of names to codes
        set: Set of valid manufacturer names
    """
    manufacturer_path = project_root / 'data/input/manufacturer_code.csv'
    if not os.path.exists(manufacturer_path):
        print(f"Warning: Manufacturer code file not found at {manufacturer_path}")
        return {}, {}, set()
        
    try:
        df = pd.read_csv(manufacturer_path)
        if 'manufacturer_name' in df.columns and 'manufacturer_code' in df.columns:
            code_to_name = dict(zip(df['manufacturer_code'].astype(str), df['manufacturer_name']))
            name_to_code = dict(zip(df['manufacturer_name'], df['manufacturer_code'].astype(str)))
            valid_manufacturers = set(df['manufacturer_name'].astype(str).str.strip())
            return code_to_name, name_to_code, valid_manufacturers
        else:
            print("Warning: Expected columns not found in manufacturer_code.csv")
            return {}, {}, set()
    except Exception as e:
        print(f"Error loading manufacturer codes: {e}")
        return {}, {}, set()

def get_manufacturer_code_from_url(url):
    """
    Extract the manufacturer code from a URL.
    
    Args:
        url: The reference URL
        
    Returns:
        str: The extracted manufacturer code or None if not found
    """
    try:
        # URLs typically have format: http://www.myhomeok.com/xiaoliang/changshang/MFR_CODE_MONTH_CODE.htm
        parts = url.split('/')
        if len(parts) >= 2:
            last_part = parts[-1]  # e.g., "1_1.htm"
            mfr_code = last_part.split('_')[0]
            return mfr_code
    except Exception as e:
        print(f"Error extracting manufacturer code from URL {url}: {e}")
    return None

def get_month_code_from_url(url):
    """
    Extract the month code from a URL.
    
    Args:
        url: The reference URL
        
    Returns:
        str: The extracted month code or None if not found
    """
    try:
        # URLs typically have format: http://www.myhomeok.com/xiaoliang/changshang/MFR_CODE_MONTH_CODE.htm
        parts = url.split('/')
        if len(parts) >= 2:
            last_part = parts[-1]  # e.g., "1_1.htm"
            parts = last_part.split('_')
            if len(parts) >= 2:
                month_code = parts[1].split('.')[0]
                return month_code
    except Exception as e:
        print(f"Error extracting month code from URL {url}: {e}")
    return None

def clean_json_data(json_file_path, output_file_path=None):
    """
    Clean the JSON data file by removing problematic entries.
    Identifies manufacturer/month combinations that need rescraping.
    
    Args:
        json_file_path: Path to the JSON file
        output_file_path: Optional path for the cleaned output file
    
    Returns:
        dict: Statistics about the cleaning process
        list: Manufacturer/month combinations that need rescraping
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
            return {"status": "error", "message": f"JSON decode error: {e}"}, []
    
    # Load valid manufacturers
    code_to_name, name_to_code, valid_manufacturers = load_valid_manufacturers()
    
    # Handle different JSON structures
    if isinstance(data, dict) and 'value' in data:
        records = data['value']
    elif isinstance(data, list):
        records = data
    else:
        print(f"Unexpected JSON structure. Expected list or dict with 'value' key.")
        return {"status": "error", "message": "Unexpected JSON structure"}, []
    
    initial_count = len(records)
    print(f"Found {initial_count} records")
    
    # Apply filters to clean the data
    filtered_records = []
    excluded_records = {
        "summary_rows": 0,
        "specific_models": 0,
        "missing_url": 0,
        "duplicates": 0,
        "problematic_manufacturer": 0,
        "unknown_manufacturer": 0
    }
    
    # Track unique manufacturer/month/year combinations to detect duplicates
    unique_combinations = {}
    
    # Collect manufacturer/month combinations that need rescraping
    rescrape_combos = []
    
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
            elif valid_manufacturers and mfr_name not in valid_manufacturers:
                # Extract manufacturer and month code from URL
                mfr_code = get_manufacturer_code_from_url(record.get('reference', ''))
                month_code = get_month_code_from_url(record.get('reference', ''))
                print(f"yilun output: {mfr_name} - {mfr_code}_{month_code}")
                
                if mfr_code and month_code:
                    # Add to rescrape list
                    combo = (mfr_code, month_code)
                    if combo not in rescrape_combos:
                        rescrape_combos.append(combo)
                    
                    print(f"Unknown manufacturer: '{mfr_name}' - Code: {mfr_code} - Month: {month_code} - URL: {record.get('reference')}")
                    
                    # If we know the correct name, we can fix it immediately
                    if mfr_code in code_to_name:
                        correct_name = code_to_name[mfr_code]
                        print(f"Fixing manufacturer name from '{mfr_name}' to '{correct_name}' (code: {mfr_code})")
                        record['manufacturer_name'] = correct_name
                        # Keep the record since we fixed it
                    else:
                        # Otherwise mark for exclusion
                        should_exclude = True
                        excluded_records["unknown_manufacturer"] += 1
                        exclusion_reason = f"Unknown manufacturer: {mfr_name} with code {mfr_code}"
                else:
                    # Cannot determine manufacturer code or month, exclude
                    excluded_records["unknown_manufacturer"] += 1
                    should_exclude = True
                    exclusion_reason = f"Unknown manufacturer: {mfr_name} (cannot determine code/month)"
        
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
    
    # Summarize manufacturer/month combinations that need rescraping
    if rescrape_combos:
        print(f"\nFound {len(rescrape_combos)} manufacturer/month combinations that need rescraping:")
        for mfr_code, month_code in rescrape_combos:
            print(f"  - Manufacturer {mfr_code}, Month {month_code}")
            
        print("\nTo rescrape these combinations, run the following commands:")
        for mfr_code, month_code in rescrape_combos:
            print(f"  python scripts/submit_manufacturer_job.py --manufacturer-codes {mfr_code} --start-month {month_code} --end-month {month_code}")
    
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
    }, rescrape_combos

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
    
    # Load valid manufacturers
    _, _, valid_manufacturers = load_valid_manufacturers()
    
    initial_count = len(df)
    print(f"Found {initial_count} records")
    
    # Apply filters to clean the data
    # 1. Remove summary rows
    summary_mask = df['model_name'].str.contains('合计|总计|Total', na=False)
    summary_count = summary_mask.sum()
    
    # 2. Remove specific problematic models
    specific_models_mask = df['model_name'].isin(['VGV', '长安佳程'])
    specific_models_count = specific_models_mask.sum()
    
    # 3. Remove entries with unknown manufacturers
    if valid_manufacturers:
        unknown_manufacturer_mask = ~df['manufacturer_name'].isin(valid_manufacturers)
        unknown_manufacturer_count = unknown_manufacturer_mask.sum()
    else:
        unknown_manufacturer_mask = pd.Series(False, index=df.index)
        unknown_manufacturer_count = 0
    
    # Check for URL column - it might be either 'url' or 'reference'
    url_column = 'url' if 'url' in df.columns else 'reference' if 'reference' in df.columns else None
    
    if url_column is None:
        print("Warning: No URL column found in CSV!")
        missing_url_mask = pd.Series(False, index=df.index)
        missing_url_count = 0
    else:
        # 4. Remove entries with missing URL
        missing_url_mask = df[url_column].isna() | (df[url_column] == '')
        missing_url_count = missing_url_mask.sum()
    
    # 5. Handle duplicates where model_name equals manufacturer_name
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
        ~unknown_manufacturer_mask &
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
    print(f"  - unknown_manufacturer: {unknown_manufacturer_count}")
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
            "unknown_manufacturer": int(unknown_manufacturer_count),
            "duplicates": duplicates_count
        }
    }

def rescrape_if_needed(rescrape_combos, auto=False):
    """
    Prompt user to run rescrape commands or run them automatically.
    
    Args:
        rescrape_combos: List of (manufacturer_code, month_code) tuples to rescrape
        auto: Whether to automatically run the commands without prompting
        
    Returns:
        bool: True if rescraping was initiated, False otherwise
    """
    if not rescrape_combos:
        return False
        
    print(f"\nFound {len(rescrape_combos)} manufacturer/month combinations that need rescraping.")
    
    if auto:
        print("Auto-rescraping enabled. Running commands...")
        for mfr_code, month_code in rescrape_combos:
            cmd = f"python scripts/submit_manufacturer_job.py --manufacturer-codes {mfr_code} --start-month {month_code} --end-month {month_code}"
            print(f"Running: {cmd}")
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error running command: {e}")
        return True
        
    response = input("Would you like to rescrape these combinations now? (y/n) ")
    if response.lower().startswith('y'):
        print("\nRunning rescrape commands...")
        for mfr_code, month_code in rescrape_combos:
            cmd = f"python scripts/submit_manufacturer_job.py --manufacturer-codes {mfr_code} --start-month {month_code} --end-month {month_code}"
            print(f"Running: {cmd}")
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error running command: {e}")
        return True
    else:
        print("\nSkipping rescraping. To rescrape later, run these commands:")
        for mfr_code, month_code in rescrape_combos:
            print(f"  python scripts/submit_manufacturer_job.py --manufacturer-codes {mfr_code} --start-month {month_code} --end-month {month_code}")
        return False

def export_json_to_csv(json_file_path, csv_file_path):
    """
    Export JSON data to CSV format, ensuring the reference URL is included.
    
    Args:
        json_file_path: Path to the JSON file
        csv_file_path: Path to the CSV file to create
    """
    print(f"Exporting JSON data from {json_file_path} to CSV at {csv_file_path}")
    
    try:
        # Read the JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, dict) and 'value' in data:
            manufacturers = data['value']
        elif isinstance(data, list):
            manufacturers = data
        else:
            print("Unexpected JSON structure. Expected list or dict with 'value' key.")
            return False
        
        # Flatten the data structure
        rows = []
        for mfr in manufacturers:
            # Check if it's a nested structure with a models array
            if 'models' in mfr and isinstance(mfr.get('models'), list):
                # Extract manufacturer data
                manufacturer_name = mfr.get('manufacturer_name', '')
                month = mfr.get('month', '')
                year = mfr.get('year', '')
                total_units_sold = mfr.get('total_units_sold', '')
                reference_url = mfr.get('reference', '')
                
                # Extract each model
                for model in mfr.get('models', []):
                    model_name = model.get('model_name', '')
                    units_sold = model.get('units_sold', 0)
                    
                    # Create a row for this model
                    row = {
                        'manufacturer_name': manufacturer_name,
                        'month': month,
                        'year': year,
                        'total_units_sold': total_units_sold,
                        'model_name': model_name,
                        'model_units_sold': units_sold,
                        'url': reference_url  # Make sure URL is included
                    }
                    rows.append(row)
            else:
                # It's a flat structure - just add the record as is
                row = {k: v for k, v in mfr.items()}
                
                # Make sure there's a URL field
                if 'reference' in mfr and 'url' not in row:
                    row['url'] = mfr['reference']
                
                rows.append(row)
        
        # Write to CSV
        if rows:
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
                # Determine fieldnames - make sure url is included
                all_fields = set()
                for row in rows:
                    all_fields.update(row.keys())
                
                # Ensure key fields are in a good order
                priority_fields = ['manufacturer_name', 'model_name', 'month', 'year', 
                                  'total_units_sold', 'model_units_sold', 'units_sold', 'url']
                
                # Create an ordered list of fields
                fieldnames = []
                for field in priority_fields:
                    if field in all_fields:
                        fieldnames.append(field)
                        all_fields.remove(field)
                
                # Add any remaining fields
                fieldnames.extend(sorted(all_fields))
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Successfully exported {len(rows)} records to {csv_file_path}")
            return True
        else:
            print("No data to export")
            return False
            
    except Exception as e:
        print(f"Error exporting JSON to CSV: {e}")
        return False

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
    parser.add_argument('--auto-rescrape', action='store_true',
                        help='Automatically run rescrape commands for problematic combinations')
    parser.add_argument('--no-rescrape', action='store_true',
                        help='Skip rescraping step entirely')
    parser.add_argument('--export-csv', action='store_true',
                        help='Export fresh CSV from JSON after cleaning to ensure URL is included')
    args = parser.parse_args()
    
    rescrape_combos = []
    
    if not args.csv_only:
        # Clean the JSON data
        json_result, combos = clean_json_data(args.json, args.output_json)
        rescrape_combos.extend(combos)
        print("JSON cleaning completed with status:", json_result["status"])
        
        # Export fresh CSV from the cleaned JSON if requested
        json_output = args.output_json or args.json
        csv_output = args.output_csv or args.csv
        
        if args.export_csv or args.json_only:  # Always export if only processing JSON
            print("\nExporting fresh CSV from the cleaned JSON data...")
            if export_json_to_csv(json_output, csv_output):
                print("CSV export completed successfully")
            else:
                print("CSV export failed")
    
    if not args.json_only and not args.export_csv:
        # Clean the CSV data directly
        csv_result = clean_csv_data(args.csv, args.output_csv)
        print("CSV cleaning completed with status:", csv_result["status"])
    
    # Handle rescraping if needed and not disabled
    if rescrape_combos and not args.no_rescrape:
        rescrape_if_needed(rescrape_combos, auto=args.auto_rescrape)
    
    print("Cleaning process complete")

if __name__ == "__main__":
    main() 