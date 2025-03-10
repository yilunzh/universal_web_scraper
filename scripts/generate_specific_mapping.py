#!/usr/bin/env python3
"""
Script to generate model mappings specifically for three manufacturers (Nio, Tesla, Volvo)
with bilingual model names, while keeping all other model names unchanged.
"""

import json
import csv
import pandas as pd
import os
import sys
import re
from pathlib import Path
from collections import defaultdict
import argparse

# Get the project root
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def load_manufacturers():
    """
    Load the list of manufacturers with their codes.
    
    Returns:
        dict: Mapping of manufacturer names to codes
        dict: Mapping of codes to manufacturer names
        dict: Mapping of normalized manufacturer names to codes
    """
    manufacturer_path = project_root / 'data/input/manufacturer_code.csv'
    if not os.path.exists(manufacturer_path):
        print(f"Warning: Manufacturer code file not found at {manufacturer_path}")
        return {}, {}, {}
        
    try:
        df = pd.read_csv(manufacturer_path)
        if 'manufacturer_name' in df.columns and 'manufacturer_code' in df.columns:
            name_to_code = dict(zip(df['manufacturer_name'], df['manufacturer_code'].astype(str)))
            code_to_name = dict(zip(df['manufacturer_code'].astype(str), df['manufacturer_name']))
            
            # Create normalized name to code mapping for fuzzy matching
            normalized_to_code = {}
            for name, code in name_to_code.items():
                normalized_name = name.lower().replace(' ', '')
                normalized_to_code[normalized_name] = code
            
            return name_to_code, code_to_name, normalized_to_code
        else:
            print("Warning: Expected columns not found in manufacturer_code.csv")
            return {}, {}, {}
    except Exception as e:
        print(f"Error loading manufacturer codes: {e}")
        return {}, {}, {}

def get_manufacturer_code(manufacturer_name, name_to_code, normalized_to_code):
    """
    Get the manufacturer code for a given manufacturer name.
    
    Args:
        manufacturer_name: The manufacturer name
        name_to_code: Mapping of manufacturer names to codes
        normalized_to_code: Mapping of normalized manufacturer names to codes
        
    Returns:
        str: Manufacturer code if found, None otherwise
    """
    # Direct lookup
    if manufacturer_name in name_to_code:
        return name_to_code[manufacturer_name]
    
    # Normalized lookup
    normalized_name = manufacturer_name.lower().replace(' ', '')
    if normalized_name in normalized_to_code:
        return normalized_to_code[normalized_name]
    
    # Partial match
    for name, code in name_to_code.items():
        if name.lower() in manufacturer_name.lower() or manufacturer_name.lower() in name.lower():
            return code
    
    # Check manufacturer code in URL pattern (common in the dataset)
    if 'reference' in manufacturer_name:
        try:
            url = manufacturer_name
            return url.split('/')[-1].split('_')[0]
        except:
            pass
    
    return None

def extract_model_names(json_file_path):
    """
    Extract all model names from the JSON data file.
    
    Args:
        json_file_path: Path to the JSON data file
        
    Returns:
        dict: Manufacturer name to list of models mapping
        dict: Model to reference URL mapping (for finding manufacturer codes)
    """
    if not os.path.exists(json_file_path):
        print(f"Error: File not found: {json_file_path}")
        return {}, {}
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict) and 'value' in data:
            manufacturers = data['value']
        elif isinstance(data, list):
            manufacturers = data
        else:
            print("Unexpected JSON structure")
            return {}, {}
        
        model_data = defaultdict(set)
        model_references = {}
        
        for mfr in manufacturers:
            manufacturer_name = mfr.get('manufacturer_name', '')
            reference_url = mfr.get('reference', '')
            
            if 'models' in mfr and isinstance(mfr['models'], list):
                for model in mfr['models']:
                    model_name = model.get('model_name', '')
                    
                    # Skip summary rows
                    if any(term in model_name for term in ['合计', '总计', 'Total']):
                        continue
                    
                    if model_name:
                        model_data[manufacturer_name].add(model_name)
                        # Store reference URL for this model
                        model_references[(manufacturer_name, model_name)] = reference_url
        
        return model_data, model_references
    
    except Exception as e:
        print(f"Error extracting model names: {e}")
        return {}, {}

def create_fixed_mappings():
    """
    Create fixed mappings for Nio, Tesla, and Volvo models based on known patterns.
    
    Returns:
        dict: Mapping rules for the three manufacturers
    """
    # Define the manufacturers we're targeting
    target_manufacturers = {
        'Nio': ['蔚来', 'Nio', 'NIO', '蔚来汽车'],
        'Tesla': ['特斯拉', 'Tesla', 'TESLA', '特斯拉中国'],
        'Volvo': ['沃尔沃', 'Volvo', 'VOLVO', '沃尔沃亚太']
    }
    
    # Define the mapping rules with Chinese brand names
    mapping_rules = {
        'Nio': {
            # Map English prefix to Chinese prefix
            'NIO ': '蔚来',
            # Specific model patterns with Chinese brand included
            '蔚来EC6': ['NIO EC6', '蔚来EC6'],
            '蔚来EC7': ['NIO EC7', '蔚来EC7'],
            '蔚来ES6': ['NIO ES6', '蔚来ES6'],
            '蔚来ES7': ['NIO ES7', '蔚来ES7'],
            '蔚来ES8': ['NIO ES8', '蔚来ES8'],
            '蔚来ET5': ['NIO ET5', '蔚来ET5'],
            '蔚来ET5T': ['NIO ET5T', '蔚来ET5T'],
            '蔚来ET7': ['NIO ET7', '蔚来ET7']
        },
        'Tesla': {
            # Map patterns with Chinese brand included
            '特斯拉Model 3': ['Model 3', 'Tesla Model 3', '特斯拉Model 3'],
            '特斯拉Model Y': ['Model Y', 'Tesla Model Y', '特斯拉Model Y']
        },
        'Volvo': {
            # Map English prefix to Chinese prefix
            'Volvo ': '沃尔沃',
            # Specific model patterns with Chinese brand included
            '沃尔沃S60': ['Volvo S60', '沃尔沃S60'],
            '沃尔沃S60 PHEV': ['Volvo S60 PHEV', '沃尔沃S60 PHEV'],
            '沃尔沃S90': ['Volvo S90', '沃尔沃S90'],
            '沃尔沃S90 PHEV': ['Volvo S90 PHEV', '沃尔沃S90 PHEV'],
            '沃尔沃XC40': ['Volvo XC40', '沃尔沃XC40'],
            '沃尔沃XC40 EV': ['Volvo XC40 EV', '沃尔沃XC40 EV'],
            '沃尔沃XC60': ['Volvo XC60', '沃尔沃XC60'],
            '沃尔沃XC60 PHEV': ['Volvo XC60 PHEV', '沃尔沃XC60 PHEV'],
            '沃尔沃C40 EV': ['Volvo C40 EV', '沃尔沃C40 EV'],
            '沃尔沃EM90': ['Volvo EM90', '沃尔沃EM90'],
            '沃尔沃EX30': ['Volvo EX30', '沃尔沃EX30']
        }
    }
    
    # Define Chinese brand names for each manufacturer
    chinese_brand_names = {
        'Nio': '蔚来',
        'Tesla': '特斯拉',
        'Volvo': '沃尔沃'
    }
    
    return target_manufacturers, mapping_rules, chinese_brand_names

def apply_fixed_mappings(model_data, model_references):
    """
    Apply fixed mappings to the model data.
    
    Args:
        model_data: Dictionary of manufacturer name to set of models
        model_references: Dictionary of (manufacturer, model) to reference URL
        
    Returns:
        dict: Mapping of model_id to canonical model and variants
    """
    target_manufacturers, mapping_rules, chinese_brand_names = create_fixed_mappings()
    
    # Load manufacturer codes
    name_to_code, code_to_name, normalized_to_code = load_manufacturers()
    
    # Create mapping of manufacturer names to canonical names
    mfr_name_map = {}
    for canonical, variants in target_manufacturers.items():
        for variant in variants:
            mfr_name_map[variant] = canonical
    
    # Create the mappings
    model_mappings = []
    model_id = 1
    
    # Hard-coded manufacturer codes for our three target manufacturers
    target_manufacturer_codes = {
        'Nio': '67',    # 蔚来汽车
        'Tesla': '104',  # 特斯拉中国
        'Volvo': '68'    # 沃尔沃亚太
    }
    
    # Process all manufacturers
    for mfr_name, models in model_data.items():
        # Check if this is one of our special target manufacturers
        is_target = False
        canonical_mfr = None
        
        for variant, canonical in mfr_name_map.items():
            if variant.lower() in mfr_name.lower() or mfr_name.lower() in variant.lower():
                is_target = True
                canonical_mfr = canonical
                break
        
        # Get manufacturer code
        mfr_code = None
        
        # For target manufacturers, use our hardcoded codes
        if is_target:
            mfr_code = target_manufacturer_codes.get(canonical_mfr)
        else:
            # For other manufacturers, try to find the code
            mfr_code = get_manufacturer_code(mfr_name, name_to_code, normalized_to_code)
            
            # If still no code, try to extract from URL
            if not mfr_code:
                # Find a reference URL for this manufacturer
                reference_url = None
                for model in models:
                    if (mfr_name, model) in model_references:
                        reference_url = model_references[(mfr_name, model)]
                        break
                
                if reference_url:
                    try:
                        mfr_code = reference_url.split('/')[-1].split('_')[0]
                    except:
                        pass
        
        # Process models for this manufacturer
        if is_target:
            # For target manufacturers, apply special rules
            process_target_manufacturer(
                canonical_mfr, 
                mfr_name, 
                models, 
                model_references,
                mapping_rules[canonical_mfr],
                chinese_brand_names[canonical_mfr],
                mfr_code,
                model_mappings,
                model_id
            )
            # Update model_id based on number of mappings created
            model_id = len(model_mappings) + 1
        else:
            # For other manufacturers, just list each model separately without grouping
            new_model_id = process_generic_manufacturer(
                mfr_name,
                models,
                mfr_code,
                model_mappings,
                model_id
            )
            # Update model_id
            model_id = new_model_id
    
    return model_mappings

def create_mapping_file(model_mappings, output_file):
    """
    Create a mapping CSV file from the model mappings.
    
    Args:
        model_mappings: List of model mapping dictionaries
        output_file: Path to save the CSV mapping
        
    Returns:
        DataFrame: The mapping data
    """
    # Convert to DataFrame
    df = pd.DataFrame(model_mappings)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Model mapping saved to {output_file} with {len(df)} entries")
    
    # Print some stats
    print(f"Mapping contains {len(df['manufacturer_name'].unique())} unique manufacturers")
    print(f"Mapping contains {df['variants'].str.count(',').sum() + len(df)} total model variants")
    
    return df

def apply_mapping_to_json(json_file_path, mapping_df, output_file_path):
    """
    Apply the model mapping to standardize model names in the JSON data.
    
    Args:
        json_file_path: Path to the JSON data file
        mapping_df: DataFrame with model mapping
        output_file_path: Path to save the standardized JSON
    """
    if not os.path.exists(json_file_path):
        print(f"Error: File not found: {json_file_path}")
        return
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create lookup dictionaries for efficient mapping
        model_map = {}
        for _, row in mapping_df.iterrows():
            manufacturer = row['manufacturer_name']
            canonical_name = row['canonical_model_name']
            variants = row['variants'].split(', ')
            
            for variant in variants:
                model_map[(manufacturer, variant)] = canonical_name
        
        # Process the data
        if isinstance(data, dict) and 'value' in data:
            manufacturers = data['value']
            
            # Standardize model names
            for mfr in manufacturers:
                manufacturer_name = mfr.get('manufacturer_name', '')
                
                if 'models' in mfr and isinstance(mfr['models'], list):
                    for model in mfr['models']:
                        original_name = model.get('model_name', '')
                        
                        # Look up canonical name
                        canonical_name = model_map.get((manufacturer_name, original_name))
                        
                        if canonical_name and original_name != canonical_name:
                            # Add original name as a field for reference
                            model['original_model_name'] = original_name
                            model['model_name'] = canonical_name
        
        # Save standardized data
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Standardized data saved to {output_file_path}")
    
    except Exception as e:
        print(f"Error applying model mapping: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate model mappings for all manufacturers')
    parser.add_argument('--json', default=str(project_root / 'data/output/china_monthly_auto_sales_data_v2.json'),
                       help='Path to input JSON file')
    parser.add_argument('--output-mapping', default=str(project_root / 'data/input/specific_model_mapping.csv'),
                       help='Path to save the model mapping CSV')
    parser.add_argument('--output-json', default=None,
                       help='Path to save the standardized JSON with canonical model names')
    args = parser.parse_args()
    
    # Extract model names - get all models from the JSON file
    print(f"Extracting all model names from {args.json}")
    model_data, model_references = extract_model_names(args.json)
    print(f"Extracted models for {len(model_data)} manufacturers")
    
    # Load manufacturer codes for reference
    name_to_code, code_to_name, _ = load_manufacturers()
    print(f"Loaded {len(name_to_code)} manufacturer codes from reference file")
    
    # Apply mappings to create a comprehensive model list
    print("Generating complete model mapping for all manufacturers")
    model_mappings = apply_fixed_mappings(model_data, model_references)
    
    # Count models by manufacturer
    mfr_counts = defaultdict(int)
    for mapping in model_mappings:
        mfr_counts[mapping['manufacturer_name']] += 1
    
    # Print summary of mappings created
    print(f"Created mapping with {len(model_mappings)} model entries across {len(mfr_counts)} manufacturers")
    print("Top manufacturers by model count:")
    for mfr, count in sorted(mfr_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {mfr}: {count} models")
    
    # Create mapping file
    if model_mappings:
        output_path = args.output_mapping
        # Make sure the path ends with specific_model_mapping.csv
        if not output_path.endswith('specific_model_mapping.csv'):
            base_dir = os.path.dirname(output_path)
            output_path = os.path.join(base_dir, 'specific_model_mapping.csv')
        
        df = create_mapping_file(model_mappings, output_path)
        print(f"Complete model mapping saved to: {output_path}")
        
        # Apply mapping if requested
        if args.output_json:
            print(f"Applying model mapping to standardize {args.json}")
            apply_mapping_to_json(args.json, df, args.output_json)
    else:
        print("No mappings were generated. Check your data or rules.")

def process_generic_manufacturer(mfr_name, models, mfr_code, model_mappings, start_model_id):
    """
    Process models for a generic manufacturer (not Nio, Tesla, Volvo).
    Simply list each model without grouping or modification.
    
    Args:
        mfr_name: Manufacturer name
        models: Set of models for this manufacturer
        mfr_code: Manufacturer code
        model_mappings: List to append mappings to
        start_model_id: Starting model ID for new mappings
    """
    model_id = start_model_id
    
    # Simply create one entry per model, no grouping
    for model in sorted(models):
        model_mappings.append({
            'model_id': model_id,
            'manufacturer_name': mfr_name,
            'manufacturer_code': mfr_code,
            'canonical_model_name': model,  # No modification to model name
            'variants': model  # Just the model itself as the only variant
        })
        model_id += 1
        
    return model_id

def process_target_manufacturer(canonical_mfr, mfr_name, models, model_references, 
                               rules, chinese_brand, mfr_code, model_mappings, start_model_id):
    """
    Process models for a target manufacturer (Nio, Tesla, Volvo) with special rules.
    
    Args:
        canonical_mfr: Canonical manufacturer name (Nio, Tesla, Volvo)
        mfr_name: Original manufacturer name from the data
        models: Set of models for this manufacturer
        model_references: Dictionary of (manufacturer, model) to reference URL
        rules: Mapping rules for this manufacturer
        chinese_brand: Chinese brand name for this manufacturer
        mfr_code: Manufacturer code
        model_mappings: List to append mappings to
        start_model_id: Starting model ID for new mappings
    """
    # First, identify all unique models
    all_models = set(models)
    
    # Group models based on rules
    model_groups = defaultdict(list)
    processed_models = set()
    
    # Check for specific model matches
    for model in models:
        matched = False
        
        # Try exact matches from rules
        for canonical_model, variants in rules.items():
            if isinstance(variants, list) and model in variants:
                model_groups[canonical_model].append((mfr_name, model))
                processed_models.add(model)
                matched = True
                break
        
        # If no match, try prefix substitution
        if not matched:
            for prefix, replacement in rules.items():
                if not isinstance(replacement, list) and model.startswith(prefix):
                    # Replace prefix and check if it matches another model
                    normalized = replacement + model[len(prefix):]
                    
                    # See if this normalized form matches any other model
                    for other_model in models:
                        if other_model == normalized and other_model != model:
                            model_groups[normalized].append((mfr_name, model))
                            model_groups[normalized].append((mfr_name, other_model))
                            processed_models.add(model)
                            processed_models.add(other_model)
                            matched = True
                            break
                    
                    if matched:
                        break
    
    # Add unprocessed models as 1:1 mappings
    for model in models:
        if model not in processed_models:
            # Generate a canonical name that includes the Chinese brand
            if canonical_mfr == 'Nio' and not model.startswith('蔚来'):
                if model.startswith('NIO '):
                    canonical_model = f"蔚来{model[4:]}"
                else:
                    canonical_model = f"蔚来{model}"
            elif canonical_mfr == 'Tesla' and not model.startswith('特斯拉'):
                if model.startswith('Tesla '):
                    canonical_model = f"特斯拉{model[6:]}"
                else:
                    canonical_model = f"特斯拉{model}"
            elif canonical_mfr == 'Volvo' and not model.startswith('沃尔沃'):
                if model.startswith('Volvo '):
                    canonical_model = f"沃尔沃{model[6:]}"
                else:
                    canonical_model = f"沃尔沃{model}"
            else:
                canonical_model = model
            
            model_groups[canonical_model].append((mfr_name, model))
    
    # Create mapping entries for this manufacturer
    model_id = start_model_id
    for canonical_model, variants in model_groups.items():
        variant_names = [model for _, model in variants]
        unique_variant_names = list(set(variant_names))
        
        model_mappings.append({
            'model_id': model_id,
            'manufacturer_name': mfr_name,
            'manufacturer_code': mfr_code,
            'canonical_model_name': canonical_model,
            'variants': ', '.join(sorted(unique_variant_names))
        })
        model_id += 1

if __name__ == "__main__":
    main() 