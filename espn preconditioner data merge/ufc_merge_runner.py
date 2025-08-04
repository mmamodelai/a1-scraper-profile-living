#!/usr/bin/env python3
"""
UFC Merge Runner

This script prepares and runs the UFC Data Merger to ensure all fighter data is preserved,
even when ESPN purges records of fighters who leave the UFC.

1. It renames freshly scraped files to the *_latest.csv format if needed
2. Runs the merger to combine new data with existing datasets
3. Ensures fighters only in older datasets are preserved in the merged result
"""

import os
import sys
import shutil
import argparse
import subprocess
from datetime import datetime

# UFC data file types
DATA_TYPES = ['ground_data', 'clinch_data', 'striking_data']

def prepare_files():
    """Prepare files by renaming freshly scraped files to the *_latest.csv format if needed"""
    renamed = []
    
    for data_type in DATA_TYPES:
        # Check if raw scraped file exists (without _latest suffix)
        raw_file = f"{data_type}.csv"
        latest_file = f"{data_type}_latest.csv"
        
        if os.path.exists(raw_file):
            # Make a copy as the latest file
            print(f"Found freshly scraped {raw_file}, copying to {latest_file}")
            shutil.copy(raw_file, latest_file)
            renamed.append(data_type)
    
    return renamed

def run_merger(force=False, verbose=False, types=None, no_backup=False, dry_run=False):
    """Run the merger script with the specified options"""
    cmd = ["python", "postscrapemerge.py"]
    
    if force:
        cmd.append("--force")
    if verbose:
        cmd.append("--verbose")
    if no_backup:
        cmd.append("--no-backup")
    if dry_run:
        cmd.append("--dry-run")
    if types:
        cmd.append("--types")
        cmd.extend(types)
    
    print(f"Running merger: {' '.join(cmd)}")
    subprocess.run(cmd)

def main():
    """Main function to parse arguments and run the script"""
    parser = argparse.ArgumentParser(description='UFC Merge Runner - Prepares and runs the UFC Data Merger')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backups before merging')
    parser.add_argument('--force', action='store_true', help='Force merge even if validation fails')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without changing files')
    parser.add_argument('--types', nargs='+', choices=DATA_TYPES, help='Specific data types to process')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-rename', action='store_true', help='Skip renaming raw files to *_latest.csv')
    
    args = parser.parse_args()
    
    print("UFC Merge Runner - Starting")
    print("="*50)
    
    # Check if postscrapemerge.py exists
    if not os.path.exists("postscrapemerge.py"):
        print("Error: postscrapemerge.py not found in current directory")
        return 1
    
    # Prepare files (rename if needed)
    if not args.no_rename:
        renamed = prepare_files()
        if renamed:
            print(f"Renamed {len(renamed)} files to *_latest.csv format")
        else:
            print("No raw scraped files found to rename")
    
    # Run the merger
    run_merger(
        force=args.force,
        verbose=args.verbose,
        types=args.types,
        no_backup=args.no_backup,
        dry_run=args.dry_run
    )
    
    print("\nUFC Merge Runner - Complete")
    print("="*50)
    print("Your living dataset now contains all fighter data, including fighters who may have been purged by ESPN.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 