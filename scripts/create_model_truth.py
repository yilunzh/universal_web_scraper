#!/usr/bin/env python3
"""
Script to extract auto model names and manufacturers for deduplication via ChatGPT.
It reads auto sales data and creates a formatted list for submission to an LLM.
"""

import json
import csv
import pandas as pd
import os
from pathlib import Path
import re
from collections import defaultdict
import unicodedata

# Get the project root
project_root = Path(__file__).resolve().parent.parent

def extract_models_for_llm():
    """
    Extract model names and their manufacturers from the sales data
    and format them for submission to an LLM like ChatGPT.
    
    Returns:
        str: Formatted text with model information
    """
    # Define file paths
    json_path = project_root / 'data/output/china_monthly_auto_sales_data_v2.json'
    manufacturer_code_path = project_root / 'data/input/manufacturer_code.csv'
    output_path = project_root / 'data/input/models_for_llm.txt'
    
    print(f"Reading auto sales data from {json_path}")
    
    # Read the manufacturer codes
    manufacturer_df = pd.read_csv(manufacturer_code_path)
    manufacturer_codes = dict(zip(manufacturer_df['manufacturer_name'], manufacturer_df['manufacturer_code']))
    
    # Read and parse the JSON data
    unique_models = set()
    
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            # Attempt to read as JSON array or object
            data = json.load(f)
            
            # For the specific nested structure in this file
            if 'value' in data and isinstance(data['value'], list):
                manufacturers = data['value']
                
                for manufacturer_data in manufacturers:
                    if 'manufacturer_name' in manufacturer_data and 'models' in manufacturer_data:
                        manufacturer_name = str(manufacturer_data['manufacturer_name']).strip()
                        
                        # Skip problematic manufacturers
                        if manufacturer_name in ['VGV', '长安佳程']:
                            continue
                        
                        # Process each model in the manufacturer's models array
                        for model_data in manufacturer_data['models']:
                            if 'model_name' in model_data:
                                model_name = str(model_data['model_name']).strip()
                                
                                # Skip summary rows and problematic models
                                if any(summary_term in model_name for summary_term in ['合计', '总计', 'Total']):
                                    continue
                                if not model_name or model_name == manufacturer_name:
                                    continue
                                
                                unique_models.add((manufacturer_name, model_name))
                                
            else:
                # Fallback to the flat structure handling
                if isinstance(data, list):
                    records = data
                else:
                    print("Unexpected JSON structure")
                    return ""
                
                # Extract unique model and manufacturer combinations from flat structure
                for record in records:
                    if 'model_name' in record and 'manufacturer_name' in record:
                        model = str(record['model_name']).strip()
                        manufacturer = str(record['manufacturer_name']).strip()
                        
                        # Skip summary rows and problematic models
                        if any(summary_term in model for summary_term in ['合计', '总计', 'Total']):
                            continue
                        if model in ['VGV', '长安佳程'] or not model:
                            continue
                        
                        unique_models.add((manufacturer, model))
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return ""
    
    print(f"Found {len(unique_models)} unique model-manufacturer combinations")
    
    # Group models by manufacturer
    models_by_manufacturer = defaultdict(list)
    for manufacturer, model in unique_models:
        models_by_manufacturer[manufacturer].append(model)
    
    # Format the prompt for ChatGPT
    llm_prompt = "# Auto Model Deduplication Task\n\n"
    llm_prompt += "I have a list of auto models grouped by manufacturer. Many models have different naming variations.\n"
    llm_prompt += "Please deduplicate the model names by identifying variants of the same model and create a standardized naming convention.\n\n"
    llm_prompt += "For example, 'Tesla Model 3', 'Model 3', and '特斯拉Model 3' all refer to the same model and should be standardized.\n\n"
    llm_prompt += "Please output a CSV-formatted list with these columns:\n"
    llm_prompt += "model_id,model_name,manufacturer_name,manufacturer_code,variants\n\n"
    llm_prompt += "Where:\n"
    llm_prompt += "- model_id is a sequential number starting at 1\n"
    llm_prompt += "- model_name is the standardized model name (without manufacturer prefix)\n"
    llm_prompt += "- manufacturer_name is the company name\n"
    llm_prompt += "- manufacturer_code is provided in the data\n"
    llm_prompt += "- variants is a comma-separated list of all original naming variations\n\n"
    llm_prompt += "Here's the model data by manufacturer:\n\n"
    
    # Sort manufacturers for consistent output
    for manufacturer in sorted(models_by_manufacturer.keys()):
        mfr_code = manufacturer_codes.get(manufacturer, "")
        models = sorted(models_by_manufacturer[manufacturer])
        
        llm_prompt += f"## {manufacturer} (Manufacturer Code: {mfr_code})\n"
        for model in models:
            llm_prompt += f"- {model}\n"
        llm_prompt += "\n"
    
    # Write the formatted model data to a file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(llm_prompt)
    
    print(f"Extracted model data saved to {output_path}")
    print("You can now copy this file's content and submit it to ChatGPT for deduplication.")
    
    return llm_prompt

def process_llm_response(llm_response, output_file=None):
    """
    Process the response from ChatGPT and convert it into a model_code.csv file.
    
    Args:
        llm_response: The text response from ChatGPT
        output_file: Path to save the processed CSV (default: data/input/model_code.csv)
    """
    if not output_file:
        output_file = project_root / 'data/input/model_code.csv'
    
    # Extract the CSV part from the response
    csv_content = ""
    in_csv_section = False
    
    for line in llm_response.split('\n'):
        # Check if we've reached the CSV header
        if "model_id,model_name,manufacturer_name,manufacturer_code,variants" in line:
            in_csv_section = True
            csv_content += line + "\n"
            continue
        
        # If we're in the CSV section, add the line
        if in_csv_section:
            # Skip empty lines or markdown formatting
            if line.strip() and not line.startswith('```'):
                csv_content += line + "\n"
    
    # If no CSV content was found, try to extract data from markdown table format
    if not csv_content:
        print("No CSV format found, attempting to parse markdown table...")
        # This would require more complex parsing logic that depends on the exact format
        # of the LLM response, which can vary
    
    # Save the CSV content to file
    if csv_content:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        print(f"Model code file created at {output_file}")
    else:
        print("Failed to extract CSV content from the LLM response")

def main():
    """
    Main function to extract model data for LLM processing.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Process auto model data for deduplication')
    parser.add_argument('--extract', action='store_true', 
                        help='Extract model data for submission to LLM')
    parser.add_argument('--process', type=str, metavar='FILE',
                        help='Process LLM response from file')
    parser.add_argument('--response', type=str, 
                        help='Process direct LLM response text (paste between quotes)')
    parser.add_argument('--output', type=str, metavar='FILE',
                        help='Output file path for processed model codes')
    
    args = parser.parse_args()
    
    # Default behavior is to extract
    if not (args.extract or args.process or args.response):
        args.extract = True
    
    if args.extract:
        extract_models_for_llm()
    
    if args.process:
        try:
            with open(args.process, 'r', encoding='utf-8') as f:
                llm_response = f.read()
            process_llm_response(llm_response, args.output)
        except Exception as e:
            print(f"Error processing LLM response file: {e}")
    
    if args.response:
        process_llm_response(args.response, args.output)

if __name__ == "__main__":
    main() 