#!/usr/bin/env python3
"""
UFC Position Stats Processor
Dedicated script for processing fighter data and creating specialized CSV files:
- striking_data.csv (striking statistics by position)
- ground_data.csv (takedown and submission data)
- clinch_data.csv (clinch statistics)
"""

import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('position_stats_processor.log'),
        logging.StreamHandler()
    ]
)

class PositionStatsProcessor:
    """Process fighter data to create specialized position statistics CSV files."""
    
    def __init__(self, fighter_profiles_file: str = 'fighter_profiles.csv'):
        self.fighter_profiles_file = fighter_profiles_file
        self.striking_records = []
        self.ground_records = []
        self.clinch_records = []
        self.success_count = 0
        self.failure_count = 0

    def load_fighter_data(self) -> Optional[pd.DataFrame]:
        """Load fighter profiles data from CSV."""
        try:
            if not Path(self.fighter_profiles_file).exists():
                logging.error(f"Fighter profiles file {self.fighter_profiles_file} not found")
                return None
            
            df = pd.read_csv(self.fighter_profiles_file)
            logging.info(f"Loaded {len(df)} fighter profiles from {self.fighter_profiles_file}")
            return df
        except Exception as e:
            logging.error(f"Error loading fighter profiles: {e}")
            return None

    def process_fighter_data(self, fighter_data: Dict) -> Tuple[Dict, Dict, Dict]:
        """Process a single fighter's data into specialized records."""
        # Extract striking data
        striking_record = {
            'Player': fighter_data.get('Name', ''),
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Opponent': 'N/A',
            'Event': 'N/A',
            'Result': 'N/A',
            'SDBL/A': fighter_data.get('Sig. Str. By Position - Standing', '0/0'),
            'SDHL/A': fighter_data.get('Sig. Str. By Position - Clinch', '0/0'),
            'SDLL/A': fighter_data.get('Sig. Str. By Position - Ground', '0/0'),
            'SL': fighter_data.get('Sig. Str. Landed', '0'),
            'SA': fighter_data.get('Sig. Str. Attempted', '0'),
            'TSL': fighter_data.get('Total Str. Landed', '0'),
            'TSA': fighter_data.get('Total Str. Attempted', '0'),
            'TSL-TSA': f"{fighter_data.get('Striking accuracy', '0%')}",
            'SLpM': fighter_data.get('SLpM', '0.00'),
            'SApM': fighter_data.get('SApM', '0%'),
            'Str. Def': fighter_data.get('Str. Def', '0%'),
            'TD Avg.': fighter_data.get('TD Avg.', '0%'),
            'TD Acc.': fighter_data.get('TD Acc.', '0%')
        }
        
        # Extract ground data
        ground_record = {
            'Player': fighter_data.get('Name', ''),
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Opponent': 'N/A',
            'Event': 'N/A',
            'Result': 'N/A',
            'TDL': fighter_data.get('Takedowns Landed', '0'),
            'TDA': fighter_data.get('Takedowns Attempted', '0'),
            'TD Acc.': fighter_data.get('TD Acc.', '0%'),
            'TD Def.': fighter_data.get('TD Def.', '0%'),
            'Sub. Avg.': fighter_data.get('Sub. Avg.', '0.0'),
            'Sub. Attempts': fighter_data.get('Sub. Attempts', '0'),
            'Sub. Success Rate': fighter_data.get('Sub. Success Rate', '0%'),
            'Control Time': fighter_data.get('Control Time', '0'),
            'Ground Control %': fighter_data.get('Ground Control %', '0%'),
            'Reversals': fighter_data.get('Reversals', '0'),
            'Sweeps': fighter_data.get('Sweeps', '0')
        }
        
        # Extract clinch data
        clinch_record = {
            'Player': fighter_data.get('Name', ''),
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Opponent': 'N/A',
            'Event': 'N/A',
            'Result': 'N/A',
            'Clinch_Strikes_Landed': str(fighter_data.get('Sig. Str. By Position - Clinch', '0/0')).split('/')[0] if '/' in str(fighter_data.get('Sig. Str. By Position - Clinch', '0/0')) else '0',
            'Clinch_Strikes_Attempted': str(fighter_data.get('Sig. Str. By Position - Clinch', '0/0')).split('/')[1] if '/' in str(fighter_data.get('Sig. Str. By Position - Clinch', '0/0')) else '0',
            'Clinch_Accuracy': fighter_data.get('Sig. Str. By Position - Clinch', '0/0'),
            'Clinch_Time_Control': fighter_data.get('Control Time', '0'),
            'Clinch_Takedowns': fighter_data.get('Takedowns Landed', '0'),
            'Clinch_Defense': fighter_data.get('TD Def.', '0%'),
            'Clinch_Strikes_Per_Min': fighter_data.get('SLpM', '0.00'),
            'Clinch_Position_Control': fighter_data.get('Ground Control %', '0%')
        }
        
        return striking_record, ground_record, clinch_record

    def process_all_fighters(self) -> None:
        """Process all fighter data into specialized records."""
        df = self.load_fighter_data()
        if df is None:
            return
        
        logging.info("Processing fighter data into specialized records...")
        
        for _, fighter_row in tqdm(df.iterrows(), total=len(df), desc="Processing fighters"):
            try:
                fighter_data = fighter_row.to_dict()
                
                # Process fighter data into specialized records
                striking_record, ground_record, clinch_record = self.process_fighter_data(fighter_data)
                
                # Add to respective lists
                self.striking_records.append(striking_record)
                self.ground_records.append(ground_record)
                self.clinch_records.append(clinch_record)
                
                self.success_count += 1
                
            except Exception as e:
                self.failure_count += 1
                fighter_name = fighter_row.get('Name', 'Unknown')
                logging.error(f"Error processing {fighter_name}: {e}")

    def save_striking_data(self, output_file: str = 'striking_data.csv') -> None:
        """Save striking data to CSV."""
        if not self.striking_records:
            logging.warning("No striking records to save")
            return
        
        logging.info("Saving striking data to CSV...")
        
        df_striking = pd.DataFrame(self.striking_records)
        df_striking.to_csv(output_file, index=False)
        
        logging.info(f"Saved {len(self.striking_records)} striking records to {output_file}")

    def save_ground_data(self, output_file: str = 'ground_data.csv') -> None:
        """Save ground data to CSV."""
        if not self.ground_records:
            logging.warning("No ground records to save")
            return
        
        logging.info("Saving ground data to CSV...")
        
        df_ground = pd.DataFrame(self.ground_records)
        df_ground.to_csv(output_file, index=False)
        
        logging.info(f"Saved {len(self.ground_records)} ground records to {output_file}")

    def save_clinch_data(self, output_file: str = 'clinch_data.csv') -> None:
        """Save clinch data to CSV."""
        if not self.clinch_records:
            logging.warning("No clinch records to save")
            return
        
        logging.info("Saving clinch data to CSV...")
        
        df_clinch = pd.DataFrame(self.clinch_records)
        df_clinch.to_csv(output_file, index=False)
        
        logging.info(f"Saved {len(self.clinch_records)} clinch records to {output_file}")

    def run_processor(self) -> None:
        """Run the position stats processor."""
        logging.info("Starting Position Stats Processor")
        
        # Process all fighter data
        self.process_all_fighters()
        
        # Save all specialized CSV files
        self.save_striking_data()
        self.save_ground_data()
        self.save_clinch_data()
        
        # Print summary
        logging.info(f"Position Stats Processor completed!")
        logging.info(f"Success: {self.success_count}, Failures: {self.failure_count}")
        logging.info(f"Striking records: {len(self.striking_records)}")
        logging.info(f"Ground records: {len(self.ground_records)}")
        logging.info(f"Clinch records: {len(self.clinch_records)}")

def main():
    """Main entry point for the position stats processor."""
    # Create processor instance
    processor = PositionStatsProcessor(fighter_profiles_file='fighter_profiles.csv')
    
    try:
        # Run the processor
        processor.run_processor()
    except KeyboardInterrupt:
        logging.info("Processor interrupted by user")
    except Exception as e:
        logging.error(f"Processor failed: {e}")
        raise

if __name__ == "__main__":
    main() 