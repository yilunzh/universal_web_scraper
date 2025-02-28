#!/usr/bin/env python3
"""
Script to validate that auto sales data is clean according to defined rules.
"""

import json
import pandas as pd
import os
from pathlib import Path
import argparse

# Get the project root
project_root = Path(__file__).resolve().parent.parent

# Define filter_valid_records function locally instead of importing it
def validate_auto_sales_record(record):
    """
    Validate auto sales record to ensure it meets data quality standards.
    """
    # 1. Check for summary rows - convert model_name to string first to handle floats
    if 'model_name' in record:
        # Convert to string to handle non-string types like floats
        model_name = str(record['model_name'])
        if any(summary_term in model_name for summary_term in ['合计', '总计', 'Total']):
            return False, "Summary row detected"
        
        # 2. Check for specific problematic models (also using string conversion)
        if model_name in ['VGV', '长安佳程']:
            return False, f"Problematic model: {model_name}"
    
    # 3. Check for missing URL
    if ('url' not in record or not record['url']) and ('reference' not in record or not record['reference']):
        return False, "Missing URL"
    
    # 4. Check for model_name = manufacturer_name
    if 'model_name' in record and 'manufacturer_name' in record:
        # Convert both to strings for comparison to handle type mismatches
        model_str = str(record['model_name']).strip()
        mfr_str = str(record['manufacturer_name']).strip()
        if model_str == mfr_str:
            # We flag this for further validation in the context of other records
            return True, "WARNING: model_name equals manufacturer_name"
    
    return True, "Valid"

def filter_valid_records(records, detailed_logs=False):
    """
    Filter a list of records to only include valid ones.
    """
    # Same implementation as in src.utils.validation
    valid_records = []
    stats = {
        "total": len(records),
        "valid": 0,
        "invalid": 0,
        "reasons": {
            "summary_row": 0,
            "problematic_model": 0,
            "missing_url": 0,
            "duplicate": 0
        }
    }
    
    # First pass - validate basic rules and identify potential duplicates
    potential_duplicates = {}
    warnings = []
    
    for i, record in enumerate(records):
        is_valid, reason = validate_auto_sales_record(record)
        
        if is_valid:
            # Check for potential duplicates
            if reason.startswith("WARNING:"):
                key = (record['manufacturer_name'], record['month'], record['year'])
                if key not in potential_duplicates:
                    potential_duplicates[key] = []
                potential_duplicates[key].append(i)
                warnings.append((i, reason))
            
            valid_records.append(record)
            stats["valid"] += 1
        else:
            stats["invalid"] += 1
            if "Summary row" in reason:
                stats["reasons"]["summary_row"] += 1
            elif "Problematic model" in reason:
                stats["reasons"]["problematic_model"] += 1
            elif "Missing URL" in reason:
                stats["reasons"]["missing_url"] += 1
                
            if detailed_logs:
                print(f"Invalid record: {reason}")
                print(f"Record data: {record}")
    
    # Second pass - handle duplicates
    records_to_remove = []
    for key, indices in potential_duplicates.items():
        if len(indices) > 1:
            # Keep the first one, mark the rest for removal
            for idx in indices[1:]:
                records_to_remove.append(idx)
                stats["reasons"]["duplicate"] += 1
                stats["invalid"] += 1
                stats["valid"] -= 1
    
    # Remove the duplicates from valid_records
    valid_records = [rec for i, rec in enumerate(valid_records) if i not in records_to_remove]
    
    return valid_records, stats

def validate_json_data(json_file_path):
    """
    Validate JSON data file to ensure it meets quality standards.
    
    Args:
        json_file_path: Path to the JSON file
    
    Returns:
        dict: Validation results
    """
    print(f"Validating JSON data from {json_file_path}")
    if not os.path.exists(json_file_path):
        return {"status": "error", "message": f"File not found: {json_file_path}"}
    
    # Load the JSON data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"JSON decode error: {e}"}
    
    # Handle different JSON structures
    if isinstance(data, dict) and 'value' in data:
        records = data['value']
    elif isinstance(data, list):
        records = data
    else:
        return {"status": "error", "message": "Unexpected JSON structure"}
    
    # Validation results
    results = {
        "total_records": len(records),
        "problems_found": 0,
        "manufacturer_problems": 0,
        "model_problems": 0,
        "empty_url_problems": 0,
        "summary_row_problems": 0,
        "duplicate_problems": 0,
        "problematic_records": []
    }
    
    # Track manufacturer/month/year combinations for duplicate detection
    unique_combinations = {}
    
    # Check each record
    for i, record in enumerate(records):
        problems = []
        
        # Check for missing URL
        if 'reference' not in record or not record['reference']:
            problems.append("Missing URL")
            results["empty_url_problems"] += 1
        
        # Check for problematic manufacturer name
        if 'manufacturer_name' in record:
            mfr_name = record['manufacturer_name']
            if any(problem_name in mfr_name for problem_name in ['VGV', '长安佳程']):
                problems.append(f"Problematic manufacturer name: {mfr_name}")
                results["manufacturer_problems"] += 1
        
        # Check for problematic models in the models array
        if 'models' in record and isinstance(record['models'], list):
            for model in record['models']:
                model_name = model.get('model_name', '')
                
                # Check for summary rows
                if any(summary_term in model_name for summary_term in ['合计', '总计', 'Total']):
                    problems.append(f"Summary model: {model_name}")
                    results["summary_row_problems"] += 1
                
                # Check for specific problematic models
                if model_name in ['VGV', '长安佳程']:
                    problems.append(f"Problematic model name: {model_name}")
                    results["model_problems"] += 1
        
        # Check for problematic model_name in flat structure
        if 'model_name' in record:
            model_name = record['model_name']
            
            # Check for summary rows
            if any(summary_term in model_name for summary_term in ['合计', '总计', 'Total']):
                problems.append(f"Summary model: {model_name}")
                results["summary_row_problems"] += 1
            
            # Check for specific problematic models
            if model_name in ['VGV', '长安佳程']:
                problems.append(f"Problematic model name: {model_name}")
                results["model_problems"] += 1
        
        # Check for duplicates where model_name equals manufacturer_name
        if 'manufacturer_name' in record and 'model_name' in record and 'month' in record and 'year' in record:
            if record['model_name'] == record['manufacturer_name']:
                key = (record['manufacturer_name'], record['month'], record['year'])
                if key in unique_combinations:
                    problems.append(f"Duplicate manufacturer/month/year: {key}")
                    results["duplicate_problems"] += 1
                else:
                    unique_combinations[key] = True
        
        # If any problems were found, add to results
        if problems:
            results["problems_found"] += 1
            results["problematic_records"].append({
                "index": i,
                "record": {k: record[k] for k in ['manufacturer_name', 'month', 'year'] if k in record},
                "problems": problems
            })
    
    results["is_valid"] = results["problems_found"] == 0
    results["status"] = "valid" if results["is_valid"] else "invalid"
    
    return results

def validate_csv_data(csv_file_path):
    """
    Validate CSV data file to ensure it meets quality standards.
    
    Args:
        csv_file_path: Path to the CSV file
        
    Returns:
        dict: Validation results
    """
    print(f"Validating CSV data from {csv_file_path}")
    if not os.path.exists(csv_file_path):
        return {"status": "error", "message": f"File not found: {csv_file_path}"}
    
    try:
        df = pd.read_csv(csv_file_path)
    except Exception as e:
        return {"status": "error", "message": f"CSV read error: {e}"}
    
    # Use the validation functions from src.utils.validation
    valid_records, stats = filter_valid_records(df.to_dict('records'), detailed_logs=True)
    
    # Check if any records were filtered out
    is_valid = len(valid_records) == len(df)
    
    return {
        "status": "valid" if is_valid else "invalid",
        "is_valid": is_valid,
        "total_records": len(df),
        "valid_records": len(valid_records),
        "invalid_records": len(df) - len(valid_records),
        "stats": stats
    }

def main():
    parser = argparse.ArgumentParser(description='Validate auto sales data files')
    parser.add_argument('--json', default=str(project_root / 'data/output/china_monthly_auto_sales_data_v2.json'),
                        help='Path to the JSON data file')
    parser.add_argument('--csv', default=str(project_root / 'data/output/china_monthly_auto_sales_data_v2.csv'),
                        help='Path to the CSV data file')
    parser.add_argument('--json-only', action='store_true',
                        help='Validate only the JSON file')
    parser.add_argument('--csv-only', action='store_true',
                        help='Validate only the CSV file')
    args = parser.parse_args()
    
    if not args.csv_only:
        json_results = validate_json_data(args.json)
        print("\n=== JSON Validation Results ===")
        if json_results["status"] == "error":
            print(f"Error: {json_results['message']}")
        else:
            print(f"Total records: {json_results['total_records']}")
            print(f"Problems found: {json_results['problems_found']}")
            print(f"Validation result: {'PASSED' if json_results['is_valid'] else 'FAILED'}")
            
            if json_results["problems_found"] > 0:
                print("\nProblem breakdown:")
                print(f"  - Manufacturer problems: {json_results['manufacturer_problems']}")
                print(f"  - Model problems: {json_results['model_problems']}")
                print(f"  - Empty URL problems: {json_results['empty_url_problems']}")
                print(f"  - Summary row problems: {json_results['summary_row_problems']}")
                print(f"  - Duplicate problems: {json_results['duplicate_problems']}")
                
                print("\nDetailed problem report:")
                for record in json_results["problematic_records"]:
                    print(f"  Record {record['index']}: {record['record']}")
                    for problem in record['problems']:
                        print(f"    - {problem}")
    
    if not args.json_only:
        csv_results = validate_csv_data(args.csv)
        print("\n=== CSV Validation Results ===")
        if csv_results["status"] == "error":
            print(f"Error: {csv_results['message']}")
        else:
            print(f"Total records: {csv_results['total_records']}")
            print(f"Valid records: {csv_results['valid_records']}")
            print(f"Invalid records: {csv_results['invalid_records']}")
            print(f"Validation result: {'PASSED' if csv_results['is_valid'] else 'FAILED'}")
            
            if not csv_results["is_valid"]:
                print("\nProblem breakdown:")
                for reason, count in csv_results["stats"]["reasons"].items():
                    if count > 0:
                        print(f"  - {reason}: {count}")

if __name__ == "__main__":
    main() 