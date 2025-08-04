#!/usr/bin/env python3
"""
Process Existing UFC Fighter Data
Processes existing HTML files to generate CSV files without web scraping.
"""

import pandas as pd
from ufc_fighter_pipeline import UFCFighterPipeline
import logging

def main():
    """Process existing HTML files and generate CSV files."""
    logging.info("Starting to process existing UFC fighter HTML files")
    
    # Create pipeline instance (no web scraping needed)
    pipeline = UFCFighterPipeline(
        output_dir='fighter_profiles',
        max_workers=1,  # Not needed for file processing
        rate_limit=0,   # Not needed for file processing
        max_retries=0,  # Not needed for file processing
        use_undetected=False  # Not needed for file processing
    )
    
    try:
        # Process existing HTML files
        pipeline.process_existing_html_files()
        
        # Save processed data
        pipeline.save_data()
        
        logging.info("Processing completed!")
        logging.info(f"Success: {pipeline.success_count}, Failures: {pipeline.failure_count}")
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        raise

if __name__ == "__main__":
    main() 