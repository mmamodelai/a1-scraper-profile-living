import pandas as pd
import os
import shutil
from datetime import datetime

# UFC data file types
DATA_TYPES = ['ground_data', 'clinch_data', 'striking_data']

def merge_ufc_data(living_file, latest_file, backup=True):
    """
    Merge UFC data files non-destructively, preserving historical data.
    Updates the "living" file with new data from the "latest" file.
    
    Parameters:
    living_file (str): Path to the living UFC data CSV file (comprehensive dataset)
    latest_file (str): Path to the latest UFC data CSV file (new scrape)
    backup (bool): Whether to create a backup of the living file before modifying
    
    Returns:
    bool: True if successful
    """
    file_type = os.path.basename(living_file).replace('_living.csv', '')
    print(f"\n{'='*50}")
    print(f"Processing: {file_type}")
    print(f"{'='*50}")
    
    # Check if this is the first time (living file doesn't exist yet)
    if not os.path.exists(living_file):
        if not os.path.exists(latest_file):
            print(f"Error: Latest file not found - {latest_file}")
            return False
            
        print(f"Living file not found. Creating initial living file from latest data.")
        shutil.copy(latest_file, living_file)
        print(f"Created initial living file: {living_file}")
        return True
        
    # Create backup of living file if requested
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_file = living_file.replace('_living.csv', f'_living_{timestamp}.csv')
        shutil.copy(living_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    print(f"Loading living dataset from '{living_file}'...")
    living_data = pd.read_csv(living_file)
    
    print(f"Loading latest dataset from '{latest_file}'...")
    latest_data = pd.read_csv(latest_file)
    
    # Create composite keys for comparison
    print("Creating composite keys for comparison...")
    living_data['composite_key'] = living_data['Player'] + '|' + living_data['Date'].astype(str) + '|' + living_data['Opponent']
    latest_data['composite_key'] = latest_data['Player'] + '|' + latest_data['Date'].astype(str) + '|' + latest_data['Opponent']
    
    # Find records in both datasets
    living_keys = set(living_data['composite_key'])
    latest_keys = set(latest_data['composite_key'])
    common_keys = living_keys.intersection(latest_keys)
    
    # Records unique to each dataset
    only_in_living = living_keys - latest_keys
    only_in_latest = latest_keys - living_keys
    
    print(f"Total records in living data: {len(living_data)}")
    print(f"Total records in latest data: {len(latest_data)}")
    print(f"Records in both datasets: {len(common_keys)}")
    print(f"Records only in living dataset: {len(only_in_living)}")
    print(f"Records only in latest dataset: {len(only_in_latest)}")
    
    # Prepare for the merge
    # 1. Start with all records from living dataset
    print("Starting with living dataset as base...")
    merged_data = living_data.copy()
    
    # 2. Add records that only exist in the latest dataset
    print(f"Adding {len(only_in_latest)} new records from latest dataset...")
    records_to_add = latest_data[latest_data['composite_key'].isin(only_in_latest)]
    merged_data = pd.concat([merged_data, records_to_add], ignore_index=True)
    
    # 3. For records in both datasets, check if latest data has new information
    if len(common_keys) > 0:
        print("Updating common records with any new information...")
        
        # Data columns are all columns except player info
        key_columns = ['Player', 'Date', 'Opponent', 'Event', 'Result', 'composite_key']
        data_columns = [col for col in latest_data.columns if col not in key_columns]
        
        # Create a lookup dictionary for faster access to latest records
        latest_records_dict = {}
        for _, row in latest_data.iterrows():
            latest_records_dict[row['composite_key']] = row
        
        updated_count = 0
        
        # Process through common records in living dataset
        for index, living_row in merged_data[merged_data['composite_key'].isin(common_keys)].iterrows():
            key = living_row['composite_key']
            latest_row = latest_records_dict.get(key)
            
            if latest_row is not None:
                # Check each data column
                update_needed = False
                for col in data_columns:
                    if col in latest_row and col in living_row:
                        # If latest data has non-empty/non-zero value but living has empty
                        latest_value = str(latest_row[col]).strip()
                        living_value = str(living_row[col]).strip()
                        
                        # Update in two cases:
                        # 1. Living data has empty/zero but latest has actual data
                        # 2. Latest data has different non-empty value (could be an update/correction)
                        if ((living_value == '' or living_value == '0' or pd.isna(living_row[col])) and
                            (latest_value != '' and latest_value != '0' and not pd.isna(latest_row[col]))) or \
                           (latest_value != living_value and 
                            latest_value != '' and latest_value != '0' and not pd.isna(latest_row[col])):
                            # Use the latest data
                            merged_data.at[index, col] = latest_row[col]
                            update_needed = True
                
                if update_needed:
                    updated_count += 1
        
        print(f"Updated {updated_count} existing records with new information")
    
    # 4. Clean up - remove the composite key column
    merged_data = merged_data.drop('composite_key', axis=1)
    
    # 5. Sort the data for better organization
    merged_data = merged_data.sort_values(by=['Player', 'Date'], ascending=[True, False])
    
    # 6. Save the merged data
    print(f"Saving updated living data to '{living_file}'...")
    merged_data.to_csv(living_file, index=False)
    
    print(f"Update completed successfully. Total records in living dataset: {len(merged_data)}")
    return True


def batch_process_ufc_data(data_dir='.'):
    """
    Process all UFC data files in the given directory.
    For each data type (ground, clinch, striking), merges:
        data_latest.csv → updates data_living.csv
    
    Parameters:
    data_dir (str): Directory containing the UFC data files
    
    Returns:
    list: List of successfully processed data types
    """
    success_list = []
    
    for data_type in DATA_TYPES:
        latest_file = os.path.join(data_dir, f"{data_type}_latest.csv")
        living_file = os.path.join(data_dir, f"{data_type}_living.csv")
        
        # Check if latest file exists
        if os.path.exists(latest_file):
            success = merge_ufc_data(living_file, latest_file)
            if success:
                success_list.append(data_type)
        else:
            print(f"Warning: Latest file not found - {latest_file}")
    
    return success_list


def rename_current_to_latest(data_dir='.'):
    """
    Rename current data files to _latest format.
    This is useful when converting from old naming convention.
    """
    renamed = []
    
    for data_type in DATA_TYPES:
        current_file = os.path.join(data_dir, f"{data_type}.csv")
        latest_file = os.path.join(data_dir, f"{data_type}_latest.csv")
        
        if os.path.exists(current_file):
            if os.path.exists(latest_file):
                overwrite = input(f"{latest_file} already exists. Overwrite? (y/n): ").lower()
                if overwrite != 'y':
                    continue
                    
            shutil.copy(current_file, latest_file)
            renamed.append(data_type)
            print(f"Renamed: {current_file} → {latest_file}")
    
    return renamed


def rename_original_to_living(data_dir='.'):
    """
    Rename original data files to _living format.
    This is useful when converting from old naming convention.
    """
    renamed = []
    
    for data_type in DATA_TYPES:
        original_file = os.path.join(data_dir, f"{data_type}_original.csv")
        living_file = os.path.join(data_dir, f"{data_type}_living.csv")
        
        if os.path.exists(original_file):
            if os.path.exists(living_file):
                overwrite = input(f"{living_file} already exists. Overwrite? (y/n): ").lower()
                if overwrite != 'y':
                    continue
                    
            shutil.copy(original_file, living_file)
            renamed.append(data_type)
            print(f"Renamed: {original_file} → {living_file}")
    
    return renamed


if __name__ == "__main__":
    print("UFC Data Merger - Living Database Approach")
    print("="*60)
    print("This script maintains a 'living' database of UFC statistics")
    print("that grows with each new scrape while preserving historical data.")
    print("\nNaming convention:")
    print("- data_latest.csv: Your most recent scrape")
    print("- data_living.csv: Comprehensive dataset that grows over time")
    print("\nOptions:")
    print("1. Process all UFC data files (merge _latest into _living)")
    print("2. Convert from old naming convention to new")
    print("3. Quit")
    
    choice = input("\nSelect an option (1-3): ")
    
    if choice == '1':
        data_dir = input("Enter directory containing UFC data files (default: current): ")
        if not data_dir:
            data_dir = '.'
            
        if not os.path.exists(data_dir):
            print(f"Error: Directory not found: {data_dir}")
        else:
            success_list = batch_process_ufc_data(data_dir)
            
            if success_list:
                print("\nSuccessfully processed the following data types:")
                for data_type in success_list:
                    print(f" - {data_type}")
            else:
                print("\nNo data was processed. Make sure files exist in the specified directory.")
    
    elif choice == '2':
        data_dir = input("Enter directory containing UFC data files (default: current): ")
        if not data_dir:
            data_dir = '.'
            
        if not os.path.exists(data_dir):
            print(f"Error: Directory not found: {data_dir}")
        else:
            print("\nConversion options:")
            print("1. Rename 'data.csv' → 'data_latest.csv'")
            print("2. Rename 'data_original.csv' → 'data_living.csv'")
            print("3. Both")
            
            convert_choice = input("\nSelect conversion option (1-3): ")
            
            if convert_choice == '1' or convert_choice == '3':
                rename_current_to_latest(data_dir)
                
            if convert_choice == '2' or convert_choice == '3':
                rename_original_to_living(data_dir)
                
            print("\nConversion completed.")
    
    else:
        print("Exiting.")