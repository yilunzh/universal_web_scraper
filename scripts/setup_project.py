#!/usr/bin/env python3
import os
from pathlib import Path
import shutil

def setup_project():
    """Set up the project directory structure and move files to their correct locations."""
    # Get project root directory
    project_root = Path(__file__).parent.parent
    
    # Create directory structure
    directories = [
        'data/input',
        'data/output',
        'logs'
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")
    
    # Move data files to input directory if they exist
    data_files = ['manufacturer_code.csv', 'month_code.csv']
    for file in data_files:
        source = project_root / file
        destination = project_root / 'data/input' / file
        
        if source.exists():
            shutil.move(str(source), str(destination))
            print(f"Moved {file} to data/input/")
        else:
            print(f"Warning: {file} not found in project root")
    
    print("\nProject setup complete!")
    print("\nDirectory structure created:")
    print("project_root/")
    print("├── data/")
    print("│   ├── input/")
    print("│   └── output/")
    print("├── logs/")
    print("├── src/")
    print("└── scripts/")

if __name__ == "__main__":
    setup_project() 