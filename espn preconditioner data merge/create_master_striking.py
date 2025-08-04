#!/usr/bin/env python3
"""
Create Master Striking Data File

This script is a simple wrapper around compare_datasets.py that:
1. Compares all striking_*.csv files in the current directory
2. Creates a master striking data file with all fighter data combined
3. Renames the master file to striking_data_living.csv

It ensures you have the most comprehensive dataset with all fighters, 
even those who have been purged by ESPN.
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime

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

def check_files():
    """Check if comparison script exists and if we have striking data files"""
    if not os.path.exists("compare_datasets.py"):
        print("Error: compare_datasets.py not found in the current directory")
        return False
    
    import glob
    files = glob.glob("striking_*.csv")
    if not files:
        print("Error: No striking_*.csv files found in the current directory")
        return False
    
    print(f"Found {len(files)} striking data files to compare")
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

def main():
    """Main function to run the master file creation process"""
    print("UFC Master Striking Data Creator")
    print("="*50)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check files
    if not check_files():
        return 1
    
    # Create a backup of the existing living file if present
    created_backup = create_backup("striking_data_living.csv")
    if created_backup:
        print("Backed up existing striking_data_living.csv file")
    
    # Run the comparison script to create a master file
    print("\nComparing all striking data files...")
    cmd = ["python", "compare_datasets.py", "--pattern", "striking_*.csv", "--create-master", "--output", "striking_data_master.csv"]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("Error: Failed to compare datasets and create master file")
        return 1
    
    # Check if master file was created
    if not os.path.exists("striking_data_master.csv"):
        print("Error: Master file was not created")
        return 1
    
    # Rename the master file to striking_data_living.csv
    print("\nRenaming master file to striking_data_living.csv...")
    try:
        shutil.copy("striking_data_master.csv", "striking_data_living.csv")
        print("Successfully created striking_data_living.csv")
    except Exception as e:
        print(f"Error renaming file: {str(e)}")
        return 1
    
    print("\n" + "="*50)
    print("Process complete!")
    print("="*50)
    print("Your striking_data_living.csv file now contains the most comprehensive")
    print("dataset with all fighters from all available sources.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 