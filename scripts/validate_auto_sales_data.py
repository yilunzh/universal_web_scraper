#!/usr/bin/env python3
"""
Script to validate that auto sales data is clean according to defined rules.
"""

import json
import pandas as pd
import os
from pathlib import Path
import argparse
from collections import defaultdict
import re

# Get the project root
project_root = Path(__file__).resolve().parent.parent

# Load valid manufacturer names from manufacturer_code.csv
def load_valid_manufacturers():
    """
    Load the list of valid manufacturer names from manufacturer_code.csv.
    
    Returns:
        set: Set of valid manufacturer names
    """
    manufacturer_path = project_root / 'data/input/manufacturer_code.csv'
    if not os.path.exists(manufacturer_path):
        print(f"Warning: Manufacturer code file not found at {manufacturer_path}")
        return set()
        
    try:
        df = pd.read_csv(manufacturer_path)
        if 'manufacturer_name' in df.columns:
            return set(df['manufacturer_name'].astype(str).str.strip())
        else:
            print("Warning: manufacturer_name column not found in manufacturer_code.csv")
            return set()
    except Exception as e:
        print(f"Error loading manufacturer codes: {e}")
        return set()

# Global variable to store valid manufacturers
VALID_MANUFACTURERS = load_valid_manufacturers()

def normalize_model_name(model_name, manufacturer_name):
    """
    Normalize model names to ensure consistent naming conventions.
    
    Args:
        model_name: The model name to normalize
        manufacturer_name: The manufacturer name to check against
        
    Returns:
        str: Normalized model name
    """
    if not model_name or not manufacturer_name:
        return model_name
    
    # Convert to strings
    model_str = str(model_name).strip()
    mfr_str = str(manufacturer_name).strip()
    
    # Remove manufacturer name from beginning if it's prefixed
    if model_str.lower().startswith(mfr_str.lower()):
        model_str = model_str[len(mfr_str):].strip()
    
    # Remove non-Latin characters at the beginning (e.g., "特斯拉")
    # This is a simplistic approach; a more robust solution would use proper character detection
    latin_start = 0
    for i, char in enumerate(model_str):
        if ord(char) < 0x3000:  # Basic check for Latin vs CJK characters
            latin_start = i
            break
    
    if latin_start > 0:
        model_str = model_str[latin_start:].strip()
    
    # Normalize spaces and fix common formatting issues
    model_str = re.sub(r'\s+', ' ', model_str)
    
    # Normalize common variant naming patterns (MODEL 3 -> Model 3, Model-3 -> Model 3)
    model_str = re.sub(r'(\w+)[- ](\d+)', r'\1 \2', model_str)
    
    # Remove redundant qualifiers
    redundant_terms = ["款", "型", "系列", "系", "纯电", "版"]
    for term in redundant_terms:
        model_str = model_str.replace(term, "").strip()
    
    return model_str.strip()

def check_model_name_consistency(records):
    """
    Check for inconsistent model naming conventions across months.
    
    Args:
        records: List of auto sales records
        
    Returns:
        tuple: (list of records with normalized model names, list of inconsistency warnings)
    """
    # Group models by manufacturer
    manufacturer_models = defaultdict(set)
    model_occurrences = defaultdict(list)
    
    # First pass: collect all model names for each manufacturer
    for i, record in enumerate(records):
        if 'manufacturer_name' in record and 'model_name' in record:
            mfr = str(record['manufacturer_name']).strip()
            model = str(record['model_name']).strip()
            
            manufacturer_models[mfr].add(model)
            model_occurrences[(mfr, model)].append(i)
        elif 'manufacturer_name' in record and 'models' in record and isinstance(record['models'], list):
            # Handle nested structure where models are in an array
            mfr = str(record['manufacturer_name']).strip()
            for model_data in record['models']:
                if 'model_name' in model_data:
                    model = str(model_data['model_name']).strip()
                    manufacturer_models[mfr].add(model)
                    # We can't update records for nested models using an index approach
                    # We'll just identify inconsistencies but not modify nested structures
    
    # Identify potential inconsistencies
    model_groups = defaultdict(list)
    for mfr, models in manufacturer_models.items():
        for model in models:
            normalized = normalize_model_name(model, mfr)
            if normalized:  # Skip empty strings
                model_groups[(mfr, normalized)].append(model)
    
    # Find groups with inconsistent naming
    inconsistencies = []
    normalized_records = list(records)  # Create a copy to modify
    
    for (mfr, norm_model), variants in model_groups.items():
        if len(variants) > 1:
            # We found inconsistent naming for this model
            inconsistencies.append({
                'manufacturer': mfr,
                'normalized_model': norm_model,
                'variants': variants
            })
            
            # Update records with normalized model names (only for flat structure)
            for variant in variants:
                for idx in model_occurrences[(mfr, variant)]:
                    if idx < len(normalized_records) and 'model_name' in normalized_records[idx]:
                        normalized_records[idx]['model_name'] = norm_model
                        normalized_records[idx]['original_model_name'] = variant
    
    return normalized_records, inconsistencies

def check_missing_months(records):
    """
    Check for missing month data where a manufacturer has 0 sales in a month,
    but has sales in both the previous and subsequent months.
    
    Args:
        records: List of auto sales records
        
    Returns:
        list: Warnings about potential missing month data
    """
    # Group sales by manufacturer, model, and month/year
    sales_by_mfr_model = defaultdict(dict)
    
    # Process flat records
    for record in records:
        if all(k in record for k in ('manufacturer_name', 'model_name', 'month', 'year')):
            mfr = str(record['manufacturer_name']).strip()
            model = str(record['model_name']).strip()
            month_year = (int(record['year']), int(record['month']))
            
            # Try to get sales from different possible fields
            sales = 0
            if 'sales' in record:
                sales = float(record['sales']) if record['sales'] else 0
            elif 'units_sold' in record:
                sales = float(record['units_sold']) if record['units_sold'] else 0
            
            sales_by_mfr_model[(mfr, model)][month_year] = sales
    
    # Process nested records (manufacturer with models array)
    for record in records:
        if 'manufacturer_name' in record and 'models' in record and isinstance(record['models'], list):
            mfr = str(record['manufacturer_name']).strip()
            
            # Only process if we have month/year at the manufacturer level
            if 'month' in record and 'year' in record:
                month_year = (int(record['year']), int(record['month']))
                
                for model_data in record['models']:
                    if 'model_name' in model_data:
                        model = str(model_data['model_name']).strip()
                        
                        # Try to get sales
                        sales = 0
                        if 'units_sold' in model_data:
                            sales = float(model_data['units_sold']) if model_data['units_sold'] else 0
                        elif 'sales' in model_data:
                            sales = float(model_data['sales']) if model_data['sales'] else 0
                        
                        sales_by_mfr_model[(mfr, model)][month_year] = sales
    
    # Check for missing months
    missing_month_warnings = []
    
    for (mfr, model), month_data in sales_by_mfr_model.items():
        # We need at least 3 months of data to detect missing months
        if len(month_data) < 3:
            continue
        
        # Sort month_year tuples
        sorted_months = sorted(month_data.keys())
        
        for i in range(1, len(sorted_months) - 1):
            curr_month = sorted_months[i]
            prev_month = sorted_months[i-1]
            next_month = sorted_months[i+1]
            
            # Check if current month has zero sales but adjacent months have sales
            if (month_data[curr_month] == 0 and 
                month_data[prev_month] > 0 and 
                month_data[next_month] > 0):
                
                # Only flag if the gap between months is reasonable (1-2 months)
                month_diff_prev = (curr_month[0] - prev_month[0]) * 12 + (curr_month[1] - prev_month[1])
                month_diff_next = (next_month[0] - curr_month[0]) * 12 + (next_month[1] - curr_month[1])
                
                if 1 <= month_diff_prev <= 2 and 1 <= month_diff_next <= 2:
                    missing_month_warnings.append({
                        'manufacturer': mfr,
                        'model': model,
                        'suspicious_month': f"{curr_month[1]}/{curr_month[0]}",
                        'previous_month': f"{prev_month[1]}/{prev_month[0]}",
                        'previous_sales': month_data[prev_month],
                        'next_month': f"{next_month[1]}/{next_month[0]}",
                        'next_sales': month_data[next_month]
                    })
    
    return missing_month_warnings

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
    
    # 4. Check if manufacturer name exists in the manufacturer_code.csv
    if 'manufacturer_name' in record:
        mfr_name = str(record['manufacturer_name']).strip()
        if VALID_MANUFACTURERS and mfr_name not in VALID_MANUFACTURERS:
            return False, f"Unknown manufacturer: {mfr_name}"
    
    # 5. Check for model_name = manufacturer_name
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
            "duplicate": 0,
            "inconsistent_model_naming": 0,
            "missing_month_data": 0,
            "unknown_manufacturer": 0
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
            elif "Unknown manufacturer" in reason:
                stats["reasons"]["unknown_manufacturer"] += 1
                
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
    
    # Check for inconsistent model naming
    normalized_records, model_inconsistencies = check_model_name_consistency(valid_records)
    if model_inconsistencies:
        stats["reasons"]["inconsistent_model_naming"] = len(model_inconsistencies)
        if detailed_logs:
            print("\nInconsistent model naming detected:")
            for inconsistency in model_inconsistencies:
                print(f"  Manufacturer: {inconsistency['manufacturer']}")
                print(f"  Model: {inconsistency['normalized_model']}")
                print(f"  Variants: {', '.join(inconsistency['variants'])}")
    
    # Check for missing month data
    missing_month_warnings = check_missing_months(normalized_records)
    if missing_month_warnings:
        stats["reasons"]["missing_month_data"] = len(missing_month_warnings)
        if detailed_logs:
            print("\nPotential missing month data detected:")
            for warning in missing_month_warnings:
                print(f"  Manufacturer: {warning['manufacturer']}")
                print(f"  Model: {warning['model']}")
                print(f"  Suspicious month with zero sales: {warning['suspicious_month']}")
                print(f"  Previous month: {warning['previous_month']} (Sales: {warning['previous_sales']})")
                print(f"  Next month: {warning['next_month']} (Sales: {warning['next_sales']})")
    
    return normalized_records, stats

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
        "inconsistent_model_naming": 0,
        "missing_month_data": 0,
        "unknown_manufacturer_problems": 0,
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
            
            # Check if manufacturer exists in manufacturer_code.csv
            if VALID_MANUFACTURERS and mfr_name not in VALID_MANUFACTURERS:
                problems.append(f"Unknown manufacturer: {mfr_name}")
                results["unknown_manufacturer_problems"] += 1
            
            # Check for specific problematic manufacturers
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
    
    # Check for inconsistent model naming
    normalized_records, model_inconsistencies = check_model_name_consistency(records)
    if model_inconsistencies:
        results["inconsistent_model_naming"] = len(model_inconsistencies)
        for inconsistency in model_inconsistencies:
            results["problems_found"] += 1
            results["problematic_records"].append({
                "type": "model_inconsistency",
                "manufacturer": inconsistency['manufacturer'],
                "normalized_model": inconsistency['normalized_model'],
                "variants": inconsistency['variants']
            })
    
    # Check for missing month data
    missing_month_warnings = check_missing_months(normalized_records)
    if missing_month_warnings:
        results["missing_month_data"] = len(missing_month_warnings)
        for warning in missing_month_warnings:
            results["problems_found"] += 1
            results["problematic_records"].append({
                "type": "missing_month",
                "manufacturer": warning['manufacturer'],
                "model": warning['model'],
                "suspicious_month": warning['suspicious_month'],
                "previous_month": warning['previous_month'],
                "next_month": warning['next_month']
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
                print(f"  - Unknown manufacturers: {json_results['unknown_manufacturer_problems']}")
                print(f"  - Model problems: {json_results['model_problems']}")
                print(f"  - Empty URL problems: {json_results['empty_url_problems']}")
                print(f"  - Summary row problems: {json_results['summary_row_problems']}")
                print(f"  - Duplicate problems: {json_results['duplicate_problems']}")
                print(f"  - Inconsistent model naming: {json_results['inconsistent_model_naming']}")
                print(f"  - Missing month data: {json_results['missing_month_data']}")
                
                print("\nDetailed problem report:")
                for record in json_results["problematic_records"]:
                    if "type" in record and record["type"] == "model_inconsistency":
                        print(f"  Model naming inconsistency for manufacturer {record['manufacturer']}:")
                        print(f"    Normalized model: {record['normalized_model']}")
                        print(f"    Variants found: {', '.join(record['variants'])}")
                    elif "type" in record and record["type"] == "missing_month":
                        print(f"  Potential missing data for {record['manufacturer']} {record['model']}:")
                        print(f"    Suspicious month with zero sales: {record['suspicious_month']}")
                        print(f"    Has sales in previous month {record['previous_month']} and next month {record['next_month']}")
                    else:
                        print(f"  Record {record.get('index', 'unknown')}: {record.get('record', {})}")
                        if 'problems' in record:
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

                # Print a sample of unknown manufacturers if any
                if csv_results["stats"]["reasons"].get("unknown_manufacturer", 0) > 0:
                    unknown_manufacturers = set()
                    for record in csv_results.get("problematic_records", []):
                        for problem in record.get("problems", []):
                            if "Unknown manufacturer" in problem:
                                unknown_manufacturers.add(problem.split(": ")[1])
                    
                    if unknown_manufacturers:
                        print("\nSample of unknown manufacturers:")
                        for mfr in list(unknown_manufacturers)[:10]:  # Show up to 10 examples
                            print(f"  - {mfr}")
                        if len(unknown_manufacturers) > 10:
                            print(f"  ... and {len(unknown_manufacturers) - 10} more")

if __name__ == "__main__":
    main() 