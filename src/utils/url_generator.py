import csv
from typing import List
from pathlib import Path

def find_first_valid_month_code(manufacturer_code: int, min_month_code: int) -> int:
    """Find the first valid month code for a manufacturer."""
    # Implementation here
    return min_month_code

def find_last_valid_month_code(manufacturer_code: int, max_month_code: int) -> int:
    """Find the last valid month code for a manufacturer."""
    # Implementation here
    return max_month_code

def generate_urls_from_codes(manufacturer_csv_path: str, month_csv_path: str) -> List[str]:
    """
    Generate URLs by combining manufacturer codes and month codes from CSV files.
    
    Args:
        manufacturer_csv_path (str): Path to CSV file containing manufacturer codes
        month_csv_path (str): Path to CSV file containing month codes
    
    Returns:
        List[str]: List of generated URLs
    """
    urls = []
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"

    try:
        # Read manufacturer codes
        with open(manufacturer_csv_path, 'r', encoding='utf-8') as f:
            manufacturer_reader = csv.DictReader(f)
            manufacturer_codes = [int(row['manufacturer_code']) for row in manufacturer_reader]

        # Read month codes
        with open(month_csv_path, 'r', encoding='utf-8') as f:
            month_reader = csv.DictReader(f)
            month_codes = [int(row['month_year_code']) for row in month_reader]

        # Generate URLs by combining codes
        for mfr_code in manufacturer_codes:
            if mfr_code in range(62,63):  # Adjust range as needed
                first_valid_month = find_first_valid_month_code(mfr_code, 1)
                last_valid_month = find_last_valid_month_code(mfr_code, max(month_codes))
                for month_code in range(85, last_valid_month + 1):
                    url = base_url.format(mfr_code, month_code)
                    urls.append(url)

        print(f"Generated {len(urls)} URLs")
        return urls

    except FileNotFoundError as e:
        print(f"Error: Could not find one of the CSV files - {e}")
        return []
    except Exception as e:
        print(f"Error while processing CSV files: {e}")
        return [] 