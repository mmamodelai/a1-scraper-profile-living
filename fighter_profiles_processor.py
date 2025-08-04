#!/usr/bin/env python3
"""
UFC Fighter Profiles Processor
Dedicated script for processing HTML files and extracting comprehensive fighter data.
Creates fighter_profiles.csv with all extracted information.
"""

import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from typing import Dict, List, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fighter_profiles_processor.log'),
        logging.StreamHandler()
    ]
)

class FighterProfilesProcessor:
    """Process HTML files to extract comprehensive fighter profile data."""
    
    def __init__(self, html_dir: str = 'fighter_profiles'):
        self.html_dir = Path(html_dir)
        self.fighter_profiles = []
        self.success_count = 0
        self.failure_count = 0

    def process_html_files(self) -> None:
        """Process all HTML files to extract fighter data."""
        if not self.html_dir.exists():
            logging.warning(f"HTML directory {self.html_dir} not found")
            return
        
        logging.info(f"Processing HTML files from {self.html_dir}")
        
        html_files = list(self.html_dir.glob('*.html'))
        logging.info(f"Found {len(html_files)} HTML files to process")
        
        for html_file in tqdm(html_files, desc="Processing HTML files"):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract fighter name from filename
                fighter_name = html_file.stem.replace('_', ' ')
                
                # Extract comprehensive fighter data
                fighter_data = self._extract_fighter_data_from_html(soup, fighter_name)
                
                if fighter_data:
                    self.fighter_profiles.append(fighter_data)
                    self.success_count += 1
                    logging.info(f"Processed {fighter_name} from HTML file")
                else:
                    self.failure_count += 1
                    logging.warning(f"Failed to extract data from {fighter_name}")
                    
            except Exception as e:
                self.failure_count += 1
                logging.error(f"Error processing {html_file}: {e}")

    def _extract_fighter_data_from_html(self, soup: BeautifulSoup, fighter_name: str) -> Optional[Dict]:
        """Extract comprehensive fighter data from HTML content using A1 techniques."""
        fighter_data = {
            'Name': fighter_name,
            'Source': 'HTML File',
            'Processing_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Extract hero profile info
        hero_info_div = soup.find(class_='hero-profile__info')
        if hero_info_div:
            # Basic info
            try:
                name_elem = hero_info_div.find(class_='hero-profile__name')
                if name_elem:
                    fighter_data['Name'] = name_elem.text.strip()
            except AttributeError:
                pass
            
            # Division info
            try:
                division_elem = hero_info_div.find(class_='hero-profile__division-title')
                if division_elem:
                    fighter_data['Division_Title'] = division_elem.text.strip()
            except AttributeError:
                pass
            
            # Record info
            try:
                record_elem = hero_info_div.find(class_='hero-profile__division-body')
                if record_elem:
                    fighter_data['Division_Record'] = record_elem.text.strip()
            except AttributeError:
                pass
            
            # Extract basic stats from hero section
            stats = {}
            for stat in hero_info_div.find_all(class_='hero-profile__stat'):
                try:
                    stat_text = stat.find(class_='hero-profile__stat-text')
                    stat_numb = stat.find(class_='hero-profile__stat-numb')
                    if stat_text and stat_numb:
                        stats[stat_text.text.strip()] = stat_numb.text.strip()
                except AttributeError:
                    pass
            fighter_data.update(stats)
        
        # Extract percentages from title tags
        percentages = {}
        titles = soup.find_all('title')
        pattern = re.compile(r'\d+%')
        for title in titles:
            try:
                text = title.text.strip()
                match = pattern.search(text)
                if match:
                    key = text.split(match.group())[0].strip()
                    percentages[key] = match.group()
            except:
                pass
        fighter_data.update(percentages)
        
        # Extract carousel data (comprehensive stats)
        carousel_div = soup.find("div", class_="c-carousel--multiple__content carousel__multiple-items stats-records-inner-wrap")
        if carousel_div:
            # Basic carousel stats
            carousel_stats = {}
            stats_class = carousel_div.find_all(class_="c-overlap__stats")
            for stat in stats_class:
                try:
                    label = stat.find(class_="c-overlap__stats-text").text.strip()
                    value = stat.find(class_="c-overlap__stats-value").text.strip()
                    carousel_stats[label] = value
                except AttributeError:
                    pass
            fighter_data.update(carousel_stats)
            
            # Comparison stats
            compare_stats = {}
            stats_class = carousel_div.find_all(class_="c-stat-compare__group")
            for stat in stats_class:
                try:
                    number_element = stat.find(class_='c-stat-compare__number')
                    label_element = stat.find(class_='c-stat-compare__label')
                    percent_element = stat.find(class_='c-stat-compare__percent')
                    suffix_element = stat.find(class_='c-stat-compare__label-suffix')

                    if number_element and label_element:
                        number = number_element.get_text(strip=True)
                        label = label_element.get_text(strip=True)

                        if percent_element and '%' not in number:
                            percent = percent_element.get_text(strip=True)
                            number += ' ' + percent

                        if suffix_element:
                            suffix = suffix_element.get_text(strip=True)
                            label += ' ' + suffix

                        compare_stats[label] = number
                except AttributeError:
                    pass
            fighter_data.update(compare_stats)
            
            # 3-bar stats
            flat_bar_stats = {}
            c_stat_3bar = carousel_div.find_all(class_="c-stat-3bar")
            for element in c_stat_3bar:
                try:
                    title = element.find("h2", class_="c-stat-3bar__title").text.strip()
                    groups = element.find_all("div", class_="c-stat-3bar__group")
                    for group in groups:
                        label = group.find("div", class_="c-stat-3bar__label").text.strip()
                        value = group.find("div", class_="c-stat-3bar__value").text.strip()
                        flat_key = f'{title} - {label}'
                        flat_bar_stats[flat_key] = value
                except AttributeError:
                    pass
            fighter_data.update(flat_bar_stats)
            
            # Strike target data
            sig_strike_stats = {}
            title = soup.find("div", class_="c-stat-body__title")
            if title:
                try:
                    sig_str_target = title.find(class_="e-t5").text.strip()
                    head_stats = soup.find(id="e-stat-body_x5F__x5F_head-txt").find_all("text")
                    body_stats = soup.find(id="e-stat-body_x5F__x5F_body-txt").find_all("text")
                    leg_stats = soup.find(id="e-stat-body_x5F__x5F_leg-txt").find_all("text")

                    sig_strike_stats[f'{sig_str_target} - Head Strike Percentage'] = head_stats[0].text.strip()
                    sig_strike_stats[f'{sig_str_target} - Head Strike Count'] = head_stats[1].text.strip()
                    sig_strike_stats[f'{sig_str_target} - Body Strike Percentage'] = body_stats[0].text.strip()
                    sig_strike_stats[f'{sig_str_target} - Body Strike Count'] = body_stats[1].text.strip()
                    sig_strike_stats[f'{sig_str_target} - Leg Strike Percentage'] = leg_stats[0].text.strip()
                    sig_strike_stats[f'{sig_str_target} - Leg Strike Count'] = leg_stats[1].text.strip()
                except AttributeError:
                    pass
            fighter_data.update(sig_strike_stats)
            
            # Fight history/events
            events = soup.find_all('li', class_='l-listing__item')
            fight_details = {}
            event_count = 0

            for event in events:
                try:
                    headline_tag = event.find('h3', class_='c-card-event--athlete-results__headline')
                    date_tag = event.find('div', class_='c-card-event--athlete-results__date')
                    results_sections = event.find_all('div', class_='c-card-event--athlete-results__results')

                    headline = ' vs '.join([op.text.strip() for op in headline_tag.find_all('a')]) if headline_tag else 'Headline not found'
                    date = date_tag.text.strip() if date_tag else 'Date not found'

                    if headline != 'Headline not found' and date != 'Date not found':
                        event_count += 1
                        event_prefix = f'Event_{event_count}_'
                        fight_details[event_prefix + 'Headline'] = headline
                        fight_details[event_prefix + 'Date'] = date

                        for index, section in enumerate(results_sections):
                            result_texts = section.find_all('div', class_='c-card-event--athlete-results__result-text')
                            labels = ['Round', 'Time', 'Method']
                            for j, result_text in enumerate(result_texts):
                                if j < len(labels):
                                    fight_details[event_prefix + labels[j]] = result_text.text.strip()
                except AttributeError:
                    pass
            fighter_data.update(fight_details)
        
        # Bio data extraction
        fields = soup.find_all("div", class_="c-bio__field")
        bio_data = {}
        for field in fields:
            try:
                label = field.find("div", class_="c-bio__label").get_text(strip=True)
                text = field.find("div", class_="c-bio__text").get_text(strip=True)
                bio_data[label.replace(' ', '_')] = text
            except AttributeError:
                pass
        fighter_data.update(bio_data)
        
        return fighter_data

    def save_fighter_profiles(self, output_file: str = 'fighter_profiles.csv') -> None:
        """Save fighter profiles to CSV."""
        if not self.fighter_profiles:
            logging.warning("No fighter profiles to save")
            return
        
        logging.info("Saving fighter profiles to CSV...")
        
        df_profiles = pd.DataFrame(self.fighter_profiles)
        df_profiles.to_csv(output_file, index=False)
        
        logging.info(f"Saved {len(self.fighter_profiles)} fighter profiles to {output_file}")

    def run_processor(self) -> None:
        """Run the fighter profiles processor."""
        logging.info("Starting Fighter Profiles Processor")
        
        # Process HTML files
        self.process_html_files()
        
        # Save results
        self.save_fighter_profiles()
        
        # Print summary
        logging.info(f"Processor completed!")
        logging.info(f"Success: {self.success_count}, Failures: {self.failure_count}")
        logging.info(f"Total fighters processed: {len(self.fighter_profiles)}")

def main():
    """Main entry point for the fighter profiles processor."""
    # Create processor instance
    processor = FighterProfilesProcessor(html_dir='fighter_profiles')
    
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