#!/usr/bin/env python3
"""
Example usage of the UFC Data Merger script
This script demonstrates various ways to use the UFC Data Merger
"""

import os
import sys
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime

def run_command(command):
    """Run a command and print its output"""
    print(f"\n> {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode

def create_sample_data():
    """Create sample data files for demonstration"""
    # Create a directory for sample data
    if not os.path.exists("sample_data"):
        os.makedirs("sample_data")
    
    # Sample fighter data
    fighters = [
        {"Name": "Jon Jones", "Division Title": "Heavyweight Division", "Wins": 27, "Losses": 1},
        {"Name": "Khabib Nurmagomedov", "Division Title": "Lightweight Division", "Wins": 29, "Losses": 0},
        {"Name": "Amanda Nunes", "Division Title": "Women's Bantamweight Division", "Wins": 22, "Losses": 5},
        {"Name": "Valentina Shevchenko", "Division Title": "Women's Flyweight Division", "Wins": 23, "Losses": 4},
        {"Name": "Israel Adesanya", "Division Title": "Middleweight Division", "Wins": 24, "Losses": 3}
    ]
    
    # Create initial living data (3 fighters)
    living_data = pd.DataFrame(fighters[:3])
    living_data.to_csv("sample_data/ground_data_living.csv", index=False)
    
    # Create latest data (all 5 fighters with some updates)
    latest_data = pd.DataFrame(fighters)
    # Update a stat for one fighter
    latest_data.loc[0, "Wins"] = 28  # Update Jon Jones' wins
    latest_data.to_csv("sample_data/ground_data_latest.csv", index=False)
    
    # Create second dataset
    clinch_data = pd.DataFrame([
        {"Name": "Dustin Poirier", "Division Title": "Lightweight Division", "Wins": 29, "Losses": 8},
        {"Name": "Charles Oliveira", "Division Title": "Lightweight Division", "Wins": 33, "Losses": 9},
        {"Name": "Max Holloway", "Division Title": "Featherweight Division", "Wins": 25, "Losses": 7}
    ])
    clinch_data.to_csv("sample_data/clinch_data_latest.csv", index=False)
    
    # Create sample with validation issues
    bad_data = pd.DataFrame([
        {"Name": "Alexander Volkanovski", "Division": "Featherweight", "Wins": 26, "Losses": 3},  # Missing Division Title
        {"Name": "Alexander Volkanovski", "Division Title": "Featherweight Division", "Wins": 26, "Losses": 3}  # Duplicate fighter
    ])
    bad_data.to_csv("sample_data/striking_data_latest.csv", index=False)
    
    print("Sample data created in ./sample_data/")
    print("* ground_data_living.csv - Existing living database with 3 fighters")
    print("* ground_data_latest.csv - Latest data with 5 fighters (2 new, 1 updated)")
    print("* clinch_data_latest.csv - Latest clinch data (no living file yet)")
    print("* striking_data_latest.csv - Data with validation issues")

def main():
    """Run example commands demonstrating UFC Data Merger usage"""
    print("UFC Data Merger - Example Usage")
    print("=" * 50)
    
    # Check if postscrapemerge.py exists
    if not os.path.exists("postscrapemerge.py"):
        print("Error: postscrapemerge.py not found in current directory")
        return 1
    
    # Create sample data
    create_sample_data()
    
    # Change to sample data directory
    os.chdir("sample_data")
    print("\nChanged directory to ./sample_data/")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 1: Basic usage - merge all available data")
    print("=" * 50)
    run_command("python ../postscrapemerge.py")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 2: Dry run mode - preview changes without modifying files")
    print("=" * 50)
    run_command("python ../postscrapemerge.py --dry-run")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 3: Process only specific data types")
    print("=" * 50)
    run_command("python ../postscrapemerge.py --types ground_data")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 4: Skip backup creation")
    print("=" * 50)
    run_command("python ../postscrapemerge.py --no-backup")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 5: Force merge even with validation issues")
    print("=" * 50)
    run_command("python ../postscrapemerge.py --types striking_data --force")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 6: Verbose mode for more detailed logs")
    print("=" * 50)
    run_command("python ../postscrapemerge.py --verbose")
    
    print("\n" + "=" * 50)
    print("EXAMPLE 7: Show help information")
    print("=" * 50)
    run_command("python ../postscrapemerge.py --help")
    
    # Go back to original directory
    os.chdir("..")
    
    print("\nExample run complete. Check the sample_data directory to see:")
    print("* Living data files (original and new)")
    print("* Backup files created during the process")
    print("* Log files generated with detailed information")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 