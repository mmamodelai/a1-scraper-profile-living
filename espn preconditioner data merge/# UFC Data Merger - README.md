# UFC Data Merger

## Overview

This Python script maintains a comprehensive "living database" of UFC fighter statistics that grows with each new scrape while preserving historical data. It automatically merges new data from your latest scrapes into the living database, ensuring you never lose valuable fighter data.

## Key Features

- **Data Preservation**: Maintains historical fighter data even when ESPN purges records of fighters who leave the UFC
- **Non-destructive Merging**: Always preserves existing data while adding new information
- **Automated Backups**: Creates timestamped backups before any modifications
- **Data Validation**: Performs quality checks on all incoming data

## File Naming Convention

The script expects files to follow this naming pattern:
- `*_latest.csv`: Your most recent scrape results (e.g., `ground_data_latest.csv`)
- `*_living.csv`: Your comprehensive dataset that grows over time (e.g., `ground_data_living.csv`)

Backups are automatically created with the format:
- `*_living_YYYYMMDD.csv`: Automatic backups with timestamps

## Supported Data Types

The script processes three types of UFC data:
- `ground_data`: Ground fighting statistics
- `clinch_data`: Clinch statistics
- `striking_data`: Striking statistics

## Requirements

- Python 3.6+
- pandas (`pip install pandas`)

## Usage

### Quick Start with UFC Merge Runner

For convenience, you can use the included `ufc_merge_runner.py` script that handles renaming your raw scraped files before merging:

```bash
# If you have freshly scraped files named ground_data.csv, clinch_data.csv, striking_data.csv
python ufc_merge_runner.py
```

This will:
1. Automatically rename your raw scraped files to the *_latest.csv format
2. Run the merger to combine with existing data
3. Preserve data for fighters purged by ESPN

### Basic Usage

Run the script in the directory containing your data files:

```bash
python postscrapemerge.py
```

### Advanced Usage

The script supports various command-line arguments for enhanced control:

```bash
# Skip backup creation
python postscrapemerge.py --no-backup

# Process only specific data types
python postscrapemerge.py --types ground_data clinch_data

# Force merge even if validation fails
python postscrapemerge.py --force

# Perform a dry run without modifying files
python postscrapemerge.py --dry-run

# Enable verbose logging
python postscrapemerge.py --verbose
```

For full help on available options:

```bash
python postscrapemerge.py --help
```

### How It Works

1. **Data Validation**
   - Performs checks to ensure data quality
   - Verifies required columns exist
   - Checks for duplicate entries
   - Can be bypassed with `--force` if needed

2. **Backup Creation**
   - Before any modifications, creates a dated backup of existing living files
   - Format: `data_living_YYYYMMDD.csv`
   - Creates at most one backup per day
   - Can be disabled with `--no-backup`

3. **Purged Fighter Detection**
   - Identifies fighters present in previous datasets but missing from latest scrape
   - Preserves these "purged" fighters' data in the merged result
   - This ensures data for fighters who leave the UFC is not lost

4. **Data Processing**
   - Loads both living and latest datasets
   - Combines them while removing duplicates
   - Saves the updated dataset back to the living file
   - Provides detailed statistics about the merge

5. **Statistics Reporting**
   - Shows number of records in previous living dataset
   - Shows number of records in latest dataset
   - Shows number of purged fighters preserved
   - Shows number of new unique records added
   - Shows total unique records after merging

6. **Logging**
   - Provides comprehensive logs of all operations
   - Logs are output to both console and log file
   - Log files are saved with timestamps: `merge_log_YYYYMMDD.log`

## Understanding ESPN Data Purges

ESPN occasionally removes fighters' data from their platform when:
- A fighter leaves the UFC for another organization (like ONE FC, Bellator, etc.)
- A fighter retires
- A fighter's contract is terminated

This merger script specifically addresses this issue by:
1. Detecting fighters present in your historical data but missing in new scrapes
2. Preserving all statistical data for these fighters
3. Including them in your comprehensive living database

This ensures your dataset remains complete even as ESPN's data changes.

## Workflow Integration

### Recommended Workflow
1. Run UFC scrapers → save to `*.csv` files (e.g. `ground_data.csv`)
2. Run `ufc_merge_runner.py` → handles renaming and merging
3. The comprehensive dataset grows in the `*_living.csv` files
4. Run any post-processing scripts on the `*_living.csv` files

### File Flow
```
Scrapers → *.csv → ufc_merge_runner.py → *_living.csv → post-processing
```

## Error Handling

- If a living file doesn't exist, it will be created from the latest data
- If a latest file is missing, that data type will be skipped
- All errors are caught, logged, and reported without stopping the entire process
- Each data type is processed independently
- Validation errors can be bypassed with the `--force` flag

## New Features

- **ESPN Purge Protection**: Preserves data for fighters who leave the UFC
- **Enhanced Data Validation**: Performs checks on incoming data for quality assurance
- **Command-line Arguments**: Flexible control over script behavior
- **Dry Run Mode**: Preview changes without modifying files
- **Comprehensive Logging**: Detailed logs of all operations saved to file
- **Improved Error Handling**: Better detection and reporting of issues
- **Performance Tracking**: Reports processing time for large datasets
- **Detailed Statistics**: More information about data merging results

## Notes

- The script is non-destructive - it always creates backups before making changes
- Operations can be previewed with the `--dry-run` flag before committing changes
- The script will process any supported data type files it finds in the current directory
- Missing files are handled gracefully - the script will continue with available files
- Each run creates a detailed log file for record-keeping and troubleshooting