#!/usr/bin/env python3
"""
Compare UFC Datasets

This script compares multiple UFC dataset files and identifies which should be
considered the master version. It analyzes fighter count, column count,
and unique fighters across all datasets.

Usage:
    python compare_datasets.py --pattern "striking_*.csv" [options]

Options:
    --pattern PATTERN     File pattern to match (e.g., "striking_*.csv")
    --create-master       Create a master file combining all datasets
    --output FILE         Output file for master dataset (default: [datatype]_master.csv)
    --verbose             Show detailed information
"""

import os
import sys
import glob
import argparse
from datetime import datetime
import pandas as pd
from tabulate import tabulate

def load_datasets(file_pattern):
    """
    Load all datasets matching the specified pattern.
    
    Args:
        file_pattern: Glob pattern to match files
        
    Returns:
        Dictionary mapping filenames to DataFrames
    """
    datasets = {}
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"Error: No files found matching pattern '{file_pattern}'")
        return datasets
        
    for file in files:
        try:
            df = pd.read_csv(file)
            
            # Check if the dataset has a 'Player' column (UFC data uses 'Player' not 'Name')
            if 'Player' not in df.columns:
                print(f"Warning: '{file}' does not have a 'Player' column. Skipping.")
                continue
                
            datasets[file] = df
            
        except Exception as e:
            print(f"Error loading '{file}': {str(e)}")
    
    return datasets

def find_unique_fighters(datasets):
    """
    Find all unique fighters across all datasets.
    
    Args:
        datasets: Dictionary of dataframes
        
    Returns:
        Set of unique fighter names
    """
    all_fighters = set()
    for df in datasets.values():
        all_fighters.update(df['Player'].unique())
    return all_fighters

def analyze_datasets(datasets):
    """
    Analyze datasets and calculate completeness scores.
    
    Args:
        datasets: Dictionary of dataframes
        
    Returns:
        Dictionary with analysis results
    """
    if not datasets:
        return {}
        
    results = {}
    all_fighters = find_unique_fighters(datasets)
    
    # Calculate statistics for each dataset
    for filename, df in datasets.items():
        file_fighters = set(df['Player'].unique())
        missing_fighters = all_fighters - file_fighters
        
        # Calculate completion score (higher is better)
        # Score = fighters * columns * records
        score = len(file_fighters) * len(df.columns) * len(df)
        
        results[filename] = {
            'file_size': os.path.getsize(filename),
            'timestamp': datetime.fromtimestamp(os.path.getmtime(filename)),
            'fighter_count': len(file_fighters),
            'column_count': len(df.columns),
            'record_count': len(df),
            'missing_fighters': missing_fighters,
            'missing_fighter_count': len(missing_fighters),
            'completeness_score': score
        }
    
    return results

def print_comparison(results, all_fighters, verbose=False):
    """
    Print comparison results in a table format.
    
    Args:
        results: Dictionary with analysis results
        all_fighters: Set of all unique fighter names
        verbose: Whether to show detailed information
        
    Returns:
        Filename of the recommended master file
    """
    if not results:
        return None
        
    # Prepare table data
    table_data = []
    
    # Sort files by completeness score (higher is better)
    sorted_results = sorted(
        results.items(), 
        key=lambda x: (x[1]['completeness_score'], x[1]['timestamp']), 
        reverse=True
    )
    
    recommended = sorted_results[0][0]
    
    for filename, stats in sorted_results:
        is_recommended = "✓" if filename == recommended else ""
        
        row = [
            os.path.basename(filename),
            stats['fighter_count'],
            f"{stats['fighter_count'] / len(all_fighters) * 100:.1f}%",
            stats['column_count'],
            stats['record_count'],
            stats['missing_fighter_count'],
            stats['timestamp'].strftime("%Y-%m-%d %H:%M"),
            is_recommended
        ]
        table_data.append(row)
    
    # Print table
    headers = ["Filename", "Fighters", "Coverage", "Columns", "Records", 
               "Missing", "Modified", "Master?"]
    
    print("\nDataset Comparison:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Print recommendation
    print(f"\nRecommended master file: {recommended}")
    print(f"This file has {results[recommended]['fighter_count']} fighters "
          f"and {results[recommended]['column_count']} columns.")
    
    # Print missing fighters details if verbose
    if verbose:
        print("\nMissing fighter details:")
        for filename, stats in sorted_results:
            missing = stats['missing_fighter_count']
            if missing > 0:
                print(f"\n{os.path.basename(filename)} is missing {missing} fighters:")
                if verbose:
                    for i, fighter in enumerate(sorted(stats['missing_fighters'])):
                        print(f"  - {fighter}")
                        if i >= 9 and len(stats['missing_fighters']) > 10:
                            print(f"  ... and {len(stats['missing_fighters']) - 10} more")
                            break
    
    return recommended

def create_master_file(datasets, results, all_fighters, output_file=None):
    """
    Create a master file combining all datasets.
    
    Args:
        datasets: Dictionary of dataframes
        results: Dictionary with analysis results
        all_fighters: Set of all unique fighter names
        output_file: Output file path
        
    Returns:
        Path to the created master file
    """
    if not datasets or not results:
        return None
    
    # Start with the most complete dataset
    sorted_results = sorted(
        results.items(), 
        key=lambda x: (x[1]['completeness_score'], x[1]['timestamp']), 
        reverse=True
    )
    
    base_file = sorted_results[0][0]
    master_df = datasets[base_file].copy()
    
    # Extract data type from base filename (e.g., "striking" from "striking_data.csv")
    data_type = os.path.basename(base_file).split('_')[0]
    
    # Set default output filename if not provided
    if not output_file:
        output_file = f"{data_type}_data_master.csv"
    
    # Add fighters from other datasets that are missing from the base dataset
    base_fighters = set(master_df['Player'].unique())
    missing_fighters = all_fighters - base_fighters
    
    if missing_fighters:
        print(f"\nAdding {len(missing_fighters)} fighters missing from the base file...")
        
        # For each missing fighter, find them in other datasets and add their records
        for fighter in missing_fighters:
            for filename, df in datasets.items():
                if filename == base_file:
                    continue
                    
                fighter_records = df[df['Player'] == fighter]
                if not fighter_records.empty:
                    # Add these records to the master dataframe
                    master_df = pd.concat([master_df, fighter_records], ignore_index=True)
                    print(f"  - Added {fighter} (found in {os.path.basename(filename)})")
                    break
    
    # Save the master file
    master_df.to_csv(output_file, index=False)
    print(f"\nCreated master file: {output_file}")
    print(f"The master file contains {len(master_df['Player'].unique())} unique fighters "
          f"and {len(master_df.columns)} columns.")
    
    return output_file

def main():
    """Main function to run the dataset comparison"""
    parser = argparse.ArgumentParser(description='Compare UFC Datasets')
    parser.add_argument('--pattern', required=True, help='File pattern to match (e.g., "striking_*.csv")')
    parser.add_argument('--create-master', action='store_true', help='Create a master file')
    parser.add_argument('--output', help='Output file for master dataset')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    
    args = parser.parse_args()
    
    print("UFC Dataset Comparison Tool")
    print("=" * 50)
    
    # Load datasets
    print(f"Loading datasets matching '{args.pattern}'...")
    datasets = load_datasets(args.pattern)
    
    if not datasets:
        print("No valid datasets found. Exiting.")
        return 1
    
    print(f"Found {len(datasets)} datasets to compare.")
    
    # Find all unique fighters
    all_fighters = find_unique_fighters(datasets)
    print(f"Found {len(all_fighters)} unique fighters across all datasets.")
    
    # Analyze datasets
    results = analyze_datasets(datasets)
    
    # Print comparison results
    recommended = print_comparison(results, all_fighters, args.verbose)
    
    # Create master file if requested
    if args.create_master and recommended:
        create_master_file(datasets, results, all_fighters, args.output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 