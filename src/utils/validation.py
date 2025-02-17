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