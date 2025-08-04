import pandas as pd
import os
import shutil
import argparse
import logging
from datetime import datetime
import sys
import time

# UFC data file types
DATA_TYPES = ['ground_data', 'clinch_data', 'striking_data']

# Set up logging
def setup_logging(log_level=logging.INFO):
    """Configure logging for the application"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"merge_log_{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    return logging.getLogger(__name__)

def validate_data(df, data_type):
    """
    Perform basic validation on data frames to ensure data quality
    
    Parameters:
    df (DataFrame): Pandas DataFrame to validate
    data_type (str): Type of data being validated
    
    Returns:
    tuple: (is_valid, message)
    """
    # Check if DataFrame is empty
    if df.empty:
        return False, f"Error: {data_type} DataFrame is empty"
        
    # Check for minimum required columns based on data type
    required_columns = ['Name', 'Division Title']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Error: {data_type} missing required columns: {missing_columns}"
    
    # Check for duplicate fighters (same Name and Division Title)
    duplicate_mask = df.duplicated(subset=['Name', 'Division Title'], keep=False)
    if duplicate_mask.any():
        duplicates = df[duplicate_mask]['Name'].unique().tolist()
        return False, f"Warning: {data_type} contains {len(duplicates)} fighters with duplicated entries"
    
    return True, f"{data_type} data validation passed"

def merge_ufc_data(living_file, latest_file, backup=True, force=False, dry_run=False):
    """
    Merge UFC data files non-destructively, preserving historical data.
    Updates the "living" file with new data from the "latest" file.
    
    Parameters:
    living_file (str): Path to the living UFC data CSV file (comprehensive dataset)
    latest_file (str): Path to the latest UFC data CSV file (new scrape)
    backup (bool): Whether to create a backup of the living file before modifying
    force (bool): Whether to proceed even if validation fails
    dry_run (bool): If True, performs all operations except actual file writing
    
    Returns:
    dict: Statistics and information about the operation
    """
    file_type = os.path.basename(living_file).replace('_living.csv', '')
    
    logger.info(f"{'='*50}")
    logger.info(f"Processing: {file_type}")
    logger.info(f"{'='*50}")
    
    result_stats = {
        'file_type': file_type,
        'status': 'failed',
        'previous_records': 0,
        'new_records': 0,
        'total_records': 0,
        'new_unique_records': 0,
        'preserved_records': 0,
        'error': None,
        'backup_created': None,
        'dry_run': dry_run
    }
    
    # Check if this is the first time (living file doesn't exist yet)
    if not os.path.exists(living_file):
        if not os.path.exists(latest_file):
            logger.error(f"Error: Latest file not found - {latest_file}")
            result_stats['error'] = f"Latest file not found - {latest_file}"
            return result_stats
            
        logger.info(f"Living file not found. Creating initial living file from latest data.")
        
        if not dry_run:
            shutil.copy(latest_file, living_file)
            logger.info(f"Created initial living file: {living_file}")
        else:
            logger.info(f"DRY RUN: Would create initial living file: {living_file}")
        
        result_stats['status'] = 'success'
        result_stats['new_records'] = len(pd.read_csv(latest_file))
        result_stats['total_records'] = result_stats['new_records']
        result_stats['new_unique_records'] = result_stats['new_records']
        return result_stats
        
    # Create backup of living file if requested
    if backup and not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_file = living_file.replace('_living.csv', f'_living_{timestamp}.csv')
        
        # Don't create duplicate backup in the same day
        if not os.path.exists(backup_file):
            shutil.copy(living_file, backup_file)
            logger.info(f"Created backup: {backup_file}")
            result_stats['backup_created'] = backup_file
    elif backup and dry_run:
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_file = living_file.replace('_living.csv', f'_living_{timestamp}.csv')
        logger.info(f"DRY RUN: Would create backup: {backup_file}")
        result_stats['backup_created'] = f"Would create: {backup_file}"
    
    try:
        logger.info(f"Loading living dataset from '{living_file}'...")
        living_data = pd.read_csv(living_file)
        result_stats['previous_records'] = len(living_data)
        
        # Validate living data
        is_valid, message = validate_data(living_data, f"{file_type} (living)")
        if not is_valid and not force:
            logger.error(message)
            result_stats['error'] = message
            return result_stats
        elif not is_valid:
            logger.warning(f"{message} - continuing due to --force flag")
        
        if not os.path.exists(latest_file):
            logger.warning(f"Latest file not found - {latest_file}. Using existing living data.")
            result_stats['status'] = 'skipped'
            result_stats['error'] = f"Latest file not found - {latest_file}"
            return result_stats
            
        logger.info(f"Loading latest dataset from '{latest_file}'...")
        latest_data = pd.read_csv(latest_file)
        result_stats['new_records'] = len(latest_data)
        
        # Validate latest data
        is_valid, message = validate_data(latest_data, f"{file_type} (latest)")
        if not is_valid and not force:
            logger.error(message)
            result_stats['error'] = message
            return result_stats
        elif not is_valid:
            logger.warning(f"{message} - continuing due to --force flag")
        
        # Identify fighters present in living data but not in latest data (purged fighters)
        living_fighters = set(living_data['Name'].unique())
        latest_fighters = set(latest_data['Name'].unique())
        purged_fighters = living_fighters - latest_fighters
        
        if purged_fighters:
            logger.info(f"Found {len(purged_fighters)} fighters in living data not present in latest data")
            logger.info(f"These fighters will be preserved (they may have been purged by ESPN)")
            
            # Extract purged fighter data
            purged_data = living_data[living_data['Name'].isin(purged_fighters)]
            result_stats['preserved_records'] = len(purged_data)
            
            # Log some of the preserved fighters (up to 5) for verification
            sample_fighters = list(purged_fighters)[:5]
            if sample_fighters:
                logger.info(f"Sample preserved fighters: {', '.join(sample_fighters)}")
        else:
            logger.info("No purged fighters found - all fighters in living data are also in latest data")
            purged_data = pd.DataFrame()
            result_stats['preserved_records'] = 0
        
        # Check for data overlaps (fighters in both datasets)
        overlap_count = len(living_fighters & latest_fighters)
        logger.info(f"Found {overlap_count} fighters in both datasets")
        
        # Combine datasets and drop duplicates
        start_time = time.time()
        
        # Concatenate latest data with purged data (if any)
        if not purged_data.empty:
            combined_data = pd.concat([latest_data, purged_data])
        else:
            combined_data = latest_data.copy()
        
        # Get count of records before deduplication
        before_count = len(combined_data)
        
        # Drop duplicates
        combined_data = combined_data.drop_duplicates()
        
        # Get count after deduplication
        after_count = len(combined_data)
        new_unique = max(0, after_count - len(living_data))  # Ensure non-negative
        
        logger.info(f"Removed {before_count - after_count} duplicate entries")
        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f} seconds")
        
        # Save updated dataset
        if not dry_run:
            combined_data.to_csv(living_file, index=False)
            logger.info(f"Successfully updated {living_file}")
        else:
            logger.info(f"DRY RUN: Would update {living_file} with {after_count} records")
        
        # Update result statistics
        result_stats['status'] = 'success'
        result_stats['total_records'] = after_count
        result_stats['new_unique_records'] = new_unique
        
        # Print statistics
        logger.info(f"\nStatistics:")
        logger.info(f"Previous records in living dataset: {len(living_data)}")
        logger.info(f"Records in latest dataset: {len(latest_data)}")
        logger.info(f"Fighters preserved (purged by ESPN): {len(purged_fighters)}")
        logger.info(f"Records preserved: {result_stats['preserved_records']}")
        logger.info(f"New unique records added: {new_unique}")
        logger.info(f"Total unique records: {after_count}")
        
        return result_stats
        
    except Exception as e:
        logger.error(f"Error processing {file_type}: {str(e)}", exc_info=True)
        result_stats['error'] = str(e)
        return result_stats

def process_all_files(backup=True, force=False, dry_run=False, types=None):
    """
    Process all UFC data files in the current directory
    
    Parameters:
    backup (bool): Whether to create backups before modifying files
    force (bool): Whether to proceed even if validation fails
    dry_run (bool): If True, performs all operations except actual file writing
    types (list): List of data types to process, defaults to all
    
    Returns:
    dict: Summary of operations
    """
    data_types_to_process = types if types else DATA_TYPES
    logger.info(f"Processing the following data types: {', '.join(data_types_to_process)}")
    
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'stats': {}
    }
    
    for data_type in data_types_to_process:
        living_file = f"{data_type}_living.csv"
        latest_file = f"{data_type}_latest.csv"
        
        if os.path.exists(latest_file):
            result = merge_ufc_data(living_file, latest_file, backup, force, dry_run)
            results['stats'][data_type] = result
            
            if result['status'] == 'success':
                results['success'].append(data_type)
            elif result['status'] == 'skipped':
                results['skipped'].append(data_type)
            else:
                results['failed'].append(data_type)
        else:
            logger.warning(f"Skipping {data_type}: Latest file not found")
            results['skipped'].append(data_type)
            results['stats'][data_type] = {
                'file_type': data_type,
                'status': 'skipped',
                'error': 'Latest file not found'
            }
    
    return results

def print_summary(results):
    """Print a summary of the operations"""
    logger.info("\n" + "="*50)
    logger.info("UFC Data Merger - Summary")
    logger.info("="*50)
    
    logger.info(f"Operation completed at: {results['timestamp']}")
    
    if results['success']:
        logger.info("\nSuccessfully processed the following data types:")
        for data_type in results['success']:
            stats = results['stats'][data_type]
            preserved = stats.get('preserved_records', 0)
            preserved_str = f" (preserved {preserved} records)" if preserved > 0 else ""
            logger.info(f" - {data_type}: +{stats['new_unique_records']} new records{preserved_str}, now {stats['total_records']} total")
    
    if results['skipped']:
        logger.info("\nSkipped the following data types:")
        for data_type in results['skipped']:
            logger.info(f" - {data_type}: {results['stats'][data_type].get('error', 'No reason provided')}")
    
    if results['failed']:
        logger.info("\nFailed to process the following data types:")
        for data_type in results['failed']:
            logger.info(f" - {data_type}: {results['stats'][data_type].get('error', 'Unknown error')}")
    
    if not results['success'] and not results['failed'] and not results['skipped']:
        logger.info("\nNo data was processed. Make sure files exist in the current directory.")

def main():
    """Main function to parse arguments and run the script"""
    parser = argparse.ArgumentParser(description='UFC Data Merger - Merges latest scraped data with living database')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backups before merging')
    parser.add_argument('--force', action='store_true', help='Force merge even if validation fails')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without changing files')
    parser.add_argument('--types', nargs='+', choices=DATA_TYPES, help='Specific data types to process')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging level based on arguments
    global logger
    logger = setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    
    logger.info("UFC Data Merger - Starting Process")
    logger.info("="*50)
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No files will be modified")
    
    # Process files
    results = process_all_files(
        backup=not args.no_backup,
        force=args.force,
        dry_run=args.dry_run,
        types=args.types
    )
    
    # Print summary
    print_summary(results)
    
    # Return a success code if at least one file was processed successfully
    return 0 if results['success'] else 1

if __name__ == "__main__":
    sys.exit(main())