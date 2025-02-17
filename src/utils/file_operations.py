import json
import csv
from typing import Dict, List
import time
from pathlib import Path

def save_json_pretty(data: List[Dict], filename: str) -> None:
    """
    Save a JSON object to a file in a pretty-printed format, loading and merging with existing data if present.
    
    Args:
        data (List[Dict]): The data to save
        filename (str): The filename to save to
    """
    try:
        # Ensure output directory exists
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data if file exists
        existing_data = {}
        if filepath.exists():
            try:
                with filepath.open("r", encoding="utf-8") as file:
                    file_content = file.read()
                    if file_content.strip():
                        existing_data = json.loads(file_content)
                    print(f"Loaded existing data: {len(existing_data.get('value', [])) if existing_data else 0} records")
            except json.JSONDecodeError as e:
                print(f"Error reading existing file: {e}. Starting fresh.")
                existing_data = {}

        # Initialize the structure if it doesn't exist
        if not existing_data:
            existing_data = {
                "description": "A list of sales data grouped by manufacturer.",
                "name": "manufacturers",
                "reference": None,
                "value": []
            }

        # Create a dictionary of existing manufacturer records for easy lookup and update
        existing_records = {}
        for idx, mfr in enumerate(existing_data['value']):
            if all(key in mfr for key in ['manufacturer_name', 'month', 'year']):
                key = (mfr['manufacturer_name'], mfr['month'], mfr['year'])
                existing_records[key] = idx

        # Process new records
        for new_record in data:
            if isinstance(new_record, dict) and all(key in new_record for key in ['manufacturer_name', 'month', 'year']):
                key = (new_record['manufacturer_name'], new_record['month'], new_record['year'])
                if key in existing_records:
                    existing_idx = existing_records[key]
                    existing_data['value'][existing_idx].update(new_record)
                else:
                    existing_data['value'].append(new_record)
                    existing_records[key] = len(existing_data['value']) - 1

        # Sort the data by manufacturer code, then month code from URL
        existing_data['value'].sort(key=lambda x: (
            int(x['reference'].split('_')[0].split('/')[-1]),  # manufacturer code
            int(x['reference'].split('_')[-1].split('.')[0])   # month code
        ))

        print(f"Saving data with {len(existing_data['value'])} manufacturers to {filename}")
        with filepath.open("w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=4, sort_keys=True, ensure_ascii=False)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"An error occurred while saving: {str(e)}")
        print(f"Data type: {type(data)}")
        print(f"Data preview: {str(data)[:200]}")

def export_to_csv(json_file_path: str, csv_file_path: str) -> None:
    """
    Transform JSON sales data into CSV format.
    
    Args:
        json_file_path (str): Path to the JSON file
        csv_file_path (str): Path to save the CSV file
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        manufacturers = data.get('value', [])
        if not manufacturers:
            print("No data to export")
            return

        # Flatten the data structure
        rows = []
        for mfr in manufacturers:
            for model in mfr.get('models', []):
                row = {
                    'manufacturer_name': mfr.get('manufacturer_name'),
                    'month': mfr.get('month'),
                    'year': mfr.get('year'),
                    'total_units_sold': mfr.get('total_units_sold'),
                    'model_name': model.get('model_name'),
                    'model_units_sold': model.get('units_sold')
                }
                rows.append(row)

        # Write to CSV
        if rows:
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"Data exported to {csv_file_path}")
        else:
            print("No rows to export")

    except Exception as e:
        print(f"Error exporting to CSV: {e}") 