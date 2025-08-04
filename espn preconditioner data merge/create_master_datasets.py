#!/usr/bin/env python3
"""
Create Master UFC Datasets

This script creates master dataset files for all UFC data types:
- striking_data
- ground_data
- clinch_data

It compares all available files for each data type and creates 
comprehensive master datasets that contain all fighter data,
even for fighters who have been purged by ESPN.
"""

import os
import sys
import shutil
import argparse
import subprocess
import glob
from datetime import datetime

# UFC data file types
DATA_TYPES = ['striking_data', 'ground_data', 'clinch_data']

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import pandas
        import tabulate
    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("Please install required packages with:")
        print("  pip install pandas tabulate")
        return False
    return True

def check_files(data_type=None):
    """Check if comparison script exists and if we have data files"""
    if not os.path.exists("compare_datasets.py"):
        print("Error: compare_datasets.py not found in the current directory")
        return False
    
    # If no specific data type, check if any data files exist
    if data_type is None:
        found_any = False
        for dt in DATA_TYPES:
            if glob.glob(f"{dt}*.csv"):
                found_any = True
                break
        
        if not found_any:
            print("Error: No UFC data files found in the current directory")
            return False
        
        return True
    
    # Check for specific data type
    files = glob.glob(f"{data_type}*.csv")
    if not files:
        print(f"Error: No {data_type}*.csv files found in the current directory")
        return False
    
    print(f"Found {len(files)} {data_type} files to compare")
    return True

def create_backup(file_path):
    """Create a backup of the file if it exists"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_file = file_path.replace('.csv', f'_{timestamp}.csv')
        
        # Don't create duplicate backup in the same day
        if not os.path.exists(backup_file):
            shutil.copy(file_path, backup_file)
            print(f"Created backup: {backup_file}")
        return True
    return False

def create_master_dataset(data_type, verbose=False):
    """Create a master dataset for the specified data type"""
    print(f"\n{'='*50}")
    print(f"Creating master dataset for {data_type}")
    print(f"{'='*50}")
    
    # Create backup of existing living file if present
    living_file = f"{data_type}_living.csv"
    created_backup = create_backup(living_file)
    if created_backup:
        print(f"Backed up existing {living_file} file")
    
    # Check if we have files to compare
    if not check_files(data_type):
        print(f"Skipping {data_type} - no files found")
        return False
    
    # Run the comparison script to create a master file
    print(f"\nComparing all {data_type} files...")
    master_file = f"{data_type}_master.csv"
    cmd = ["python", "compare_datasets.py", "--pattern", f"{data_type}*.csv", "--create-master", "--output", master_file]
    
    if verbose:
        cmd.append("--verbose")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Failed to compare {data_type} files and create master file")
        return False
    
    # Check if master file was created
    if not os.path.exists(master_file):
        print(f"Error: Master file {master_file} was not created")
        return False
    
    # Rename the master file to *_living.csv
    print(f"\nRenaming master file to {living_file}...")
    try:
        shutil.copy(master_file, living_file)
        print(f"Successfully created {living_file}")
    except Exception as e:
        print(f"Error renaming file: {str(e)}")
        return False
    
    return True

def main():
    """Main function to run the master file creation process"""
    parser = argparse.ArgumentParser(description='Create Master UFC Datasets')
    parser.add_argument('--types', nargs='+', choices=DATA_TYPES, help='Specific data types to process (default: all)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    
    args = parser.parse_args()
    
    print("UFC Master Dataset Creator")
    print("="*50)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check files
    if not check_files():
        return 1
    
    # Determine which data types to process
    data_types_to_process = args.types if args.types else DATA_TYPES
    print(f"Processing data types: {', '.join(data_types_to_process)}")
    
    # Create master datasets for each type
    success_count = 0
    for data_type in data_types_to_process:
        if create_master_dataset(data_type, args.verbose):
            success_count += 1
    
    # Print summary
    print("\n" + "="*50)
    print("Process complete!")
    print("="*50)
    print(f"Successfully created {success_count} of {len(data_types_to_process)} master datasets")
    
    if success_count > 0:
        print("\nYour *_living.csv files now contain the most comprehensive")
        print("datasets with all fighters from all available sources.")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 