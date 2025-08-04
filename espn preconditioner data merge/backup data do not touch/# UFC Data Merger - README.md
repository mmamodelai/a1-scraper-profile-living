# UFC Data Merger - README

## Overview

This Python script maintains a comprehensive "living database" of UFC fighter statistics that grows with each new scrape while preserving historical data. It's designed to ensure you never lose valuable fighter data when fighters leave the UFC, which is crucial for calculating defensive statistics for current fighters.

## File Naming Convention

- `data_latest.csv`: Your most recent scrape results (e.g., `ground_data_latest.csv`)
- `data_living.csv`: Your comprehensive dataset that grows over time (e.g., `ground_data_living.csv`)
- `data_living_YYYYMMDD.csv`: Automatic backups with timestamps

## Supported Data Types

- `ground_data`: Ground fighting statistics
- `clinch_data`: Clinch statistics
- `striking_data`: Striking statistics

## Requirements

- Python 3.6+
- pandas (`pip install pandas`)

## Usage

### Basic Usage

```bash
python ufc_data_merger.py
```

This will present a menu with options:

1. **Process all UFC data files** - Merge `_latest.csv` files into `_living.csv` files
2. **Convert from old naming convention** - Helps you transition to the new naming system
3. **Quit**

### How It Works

#### Initial Setup
If you're transitioning from a different naming convention:
1. Choose option 2 from the main menu
2. Select the appropriate conversion option:
   - Rename `data.csv` → `data_latest.csv`
   - Rename `data_original.csv` → `data_living.csv`
   - Both

#### For Each New Scrape
1. Run your scrapers and save output to `data_latest.csv` files
2. Run this script and choose option 1
3. The script will:
   - Create a backup of the current `data_living.csv` files
   - Merge new data from `data_latest.csv` into `data_living.csv`
   - Preserve all historical records
   - Add new records
   - Update existing records with any new information

## Merging Logic

The script uses a smart, non-destructive merging approach:

1. **Preserves all historical records** in the living dataset
2. **Adds new records** from the latest scrape
3. **Updates existing records** with new information when available
4. Uses a **composite key** (Player, Date, Opponent) to uniquely identify fights

## For Cursor Agent

If you're using this with a Cursor Claude agent, here are some common commands:

```
# Process all UFC data files in the current directory
python ufc_data_merger.py
# Then select option 1

# Convert files from old naming to new naming convention
python ufc_data_merger.py
# Then select option 2

# Check if files exist in the expected format
ls *_latest.csv
ls *_living.csv
```

## Workflow Integration

### Recommended Workflow
1. Run UFC scrapers → output to `data_latest.csv` files
2. Run this merger script → updates `data_living.csv` files
3. Run post-processing scripts on the `data_living.csv` files
4. Generate fighter dossiers from the processed data

### File Flow
```
Scrapers → data_latest.csv → data_living.csv → post-processing → dossiers
```

## Troubleshooting

- If `data_living.csv` doesn't exist, the script will create it from `data_latest.csv`
- Each run creates a dated backup of living files before modifying them
- The script provides detailed reports of what changed during each merge

## Extending the Script

To add support for additional data types, modify the `DATA_TYPES` list at the top of the script:

```python
DATA_TYPES = ['ground_data', 'clinch_data', 'striking_data', 'your_new_type']
```