import csv
from typing import Dict
from pathlib import Path

def validate_entry(entry: Dict, url: str) -> bool:
    """Validate manufacturer entry against expected values."""
    # Get the path to the input data directory
    input_dir = Path(__file__).parent.parent.parent / 'data' / 'input'
    manufacturer_csv = input_dir / 'manufacturer_code.csv'

    with open(manufacturer_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        manufacturer_lookup = {int(row[0]): row[1] for row in reader}

    url_parts = url.split('/')[-1].split('_')
    manufacturer_code = int(url_parts[0])
    expected_name = manufacturer_lookup.get(manufacturer_code)

    print(f"Validating entry for {url}")
    print(f"Entry: {entry}")
    print(f"Expected name: {expected_name}")
    print(f"Current name: {entry.get('manufacturer_name')}")

    if expected_name and entry.get("manufacturer_name") != expected_name:
        print(f"Mismatch found for {url}")
        print(f"Current: {entry.get('manufacturer_name')}")
        print(f"Expected: {expected_name}")
        return False
    return True 

def validate_auto_sales_record(record):
    """
    Validate auto sales record to ensure it meets data quality standards.
    
    Args:
        record (dict): The record to validate
        
    Returns:
        tuple: (is_valid, reason) - Boolean indicating if record is valid and reason if not
    """
    # 1. Check for summary rows
    if 'model_name' in record and any(summary_term in record['model_name'] for summary_term in ['合计', '总计', 'Total']):
        return False, "Summary row detected"
    
    # 2. Check for specific problematic models
    if 'model_name' in record and record['model_name'] in ['VGV', '长安佳程']:
        return False, f"Problematic model: {record['model_name']}"
    
    # 3. Check for missing URL
    if ('url' not in record or not record['url']) and ('reference' not in record or not record['reference']):
        return False, "Missing URL"
    
    # 4. Check for model_name = manufacturer_name (needs context check in the import process)
    if 'model_name' in record and 'manufacturer_name' in record and record['model_name'] == record['manufacturer_name']:
        # We flag this for further validation in the context of other records
        return True, "WARNING: model_name equals manufacturer_name"
    
    return True, "Valid"

def filter_valid_records(records, detailed_logs=False):
    """
    Filter a list of records to only include valid ones.
    
    Args:
        records (list): List of record dictionaries to validate
        detailed_logs (bool): Whether to print detailed validation logs
        
    Returns:
        tuple: (valid_records, stats) - List of valid records and statistics dict
    """
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
    
    # Track potential duplicates for model_name = manufacturer_name
    potential_duplicates = {}
    warnings = []
    
    # First pass - validate basic rules and identify potential duplicates
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
    
    # Second pass - handle duplicates where model_name = manufacturer_name
    records_to_remove = []
    for key, indices in potential_duplicates.items():
        if len(indices) > 1:
            # Keep the first one, mark the rest for removal
            for idx in indices[1:]:
                records_to_remove.append(idx)
                stats["reasons"]["duplicate"] += 1
                stats["invalid"] += 1
                stats["valid"] -= 1
                
                if detailed_logs:
                    print(f"Marking duplicate for removal: {records[idx]}")
    
    # Remove the duplicates from valid_records
    valid_records = [rec for i, rec in enumerate(valid_records) if i not in records_to_remove]
    
    return valid_records, stats 