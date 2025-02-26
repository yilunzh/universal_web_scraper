#!/usr/bin/env python3
import argparse
import asyncio
import sys
import json
import codecs
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.validate_data import validate_china_auto_sales

async def main():
    # Create logs directory if it doesn't exist
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Generate a default output path with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_output = logs_dir / f"validation_report_{timestamp}.json"
    
    parser = argparse.ArgumentParser(description="Validate china_auto_sales data in Supabase")
    parser.add_argument(
        "--output", 
        help="Output file path for validation report (JSON)",
        default=str(default_output)
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed validation results"
    )
    args = parser.parse_args()
    
    # Run the validation
    print("Running validation on china_auto_sales database...")
    results = await validate_china_auto_sales()
    
    # Save report
    output_path = Path(args.output)
    
    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with codecs.open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nValidation report saved to {output_path}")
    
    # Print summary
    print("\n=== Validation Results ===")
    if results['status'] == 'success':
        print(f"Total records: {results['total_records']}")
        print(f"Unique manufacturers: {results['unique_manufacturers']}")
        print(f"Date range: {results['date_range']['earliest']} to {results['date_range']['latest']}")
        
        if results['duplicates']['found']:
            print(f"\nFound {results['duplicates']['count']} duplicate entries")
            if args.verbose:
                for dup in results['duplicates']['details']:
                    # Ensure manufacturer name and model name are properly displayed
                    print(f"  {dup['manufacturer_name']}, {dup['year']}-{dup['month']}, Model: {dup['model_name']}: {dup['count']} entries")
        else:
            print("\nNo duplicates found ✓")
            
        if results['missing_months']['found']:
            print(f"\nFound {results['missing_months']['count']} manufacturers with missing months")
            if args.verbose:
                for missing in results['missing_months']['details']:
                    # Ensure manufacturer name is properly displayed
                    print(f"  {missing['manufacturer_name']}: {missing['missing_count']} missing entries")
                    # Print first 5 missing months as example
                    for month in missing['missing_months'][:5]:
                        print(f"    - {month['year']}-{month['month']}")
                    if len(missing['missing_months']) > 5:
                        print(f"    - ... and {len(missing['missing_months']) - 5} more")
        else:
            print("\nNo missing months found ✓")
            
        print(f"\nOverall validation result: {'PASSED ✓' if results['is_valid'] else 'FAILED ✗'}")
    else:
        print(f"Validation error: {results['message']}")
    
    # Return success or failure
    return 0 if results['is_valid'] else 1

if __name__ == "__main__":
    # Ensure console can display Chinese characters
    if sys.platform.startswith('win'):
        # For Windows
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetConsoleOutputCP(65001)
    
    # Ensure stdout is using UTF-8
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 