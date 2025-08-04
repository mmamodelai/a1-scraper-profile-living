#!/usr/bin/env python3
"""
UFC Fighter Stats Pipeline - Enhanced with Cloudflare Bypass
A comprehensive scraper that extracts fighter data from UFC.com and ESPN,
then processes it into specialized CSV files for striking, ground, and clinch data.
Uses advanced techniques to bypass Cloudflare protection.
"""

import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import os
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional, Tuple
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import random
from datetime import datetime
import urllib.parse
import re
import csv

# Advanced scraping imports for Cloudflare bypass
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    logging.warning("undetected-chromedriver not available, falling back to requests")

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    logging.warning("cloudscraper not available, falling back to requests")

from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ufc_scraper.log'),
        logging.StreamHandler()
    ]
)

class UFCFighterPipeline:
    """Unified UFC fighter data scraping and processing pipeline with Cloudflare bypass."""
    
    def __init__(self, output_dir: str = 'fighter_profiles', max_workers: int = 3, 
                 rate_limit: float = 2.0, max_retries: int = 5, use_undetected: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        
        # Initialize user agent generator
        try:
            self.ua = UserAgent()
        except:
            self.ua = None
        
        # Initialize sessions
        self.session = self._create_session()
        self.cloudscraper_session = self._create_cloudscraper_session() if CLOUDSCRAPER_AVAILABLE else None
        self.driver = None
        
        # Statistics tracking
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0
        self.requests_this_minute = 0
        self.minute_start = datetime.now()
        
        # Data storage
        self.fighter_profiles = []
        self.striking_data = []
        self.ground_data = []
        self.clinch_data = []

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy and headers."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Use fake user agent if available
        if self.ua:
            user_agent = self.ua.random
        else:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        return session

    def _create_cloudscraper_session(self) -> cloudscraper.CloudScraper:
        """Create a cloudscraper session for bypassing Cloudflare."""
        if not CLOUDSCRAPER_AVAILABLE:
            return None
        
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        if self.ua:
            scraper.headers['User-Agent'] = self.ua.random
        
        return scraper

    def _init_undetected_driver(self):
        """Initialize undetected Chrome driver for bypassing Cloudflare."""
        if not self.use_undetected or not UNDETECTED_AVAILABLE:
            return None
        
        try:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--disable-javascript')  # We'll enable if needed
            
            if self.ua:
                options.add_argument(f'--user-agent={self.ua.random}')
            
            driver = uc.Chrome(options=options, version_main=None)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logging.warning(f"Failed to initialize undetected driver: {e}")
            return None

    def _rotate_user_agent(self):
        """Rotate user agent to avoid detection."""
        if self.ua:
            new_ua = self.ua.random
            self.session.headers['User-Agent'] = new_ua
            if self.cloudscraper_session:
                self.cloudscraper_session.headers['User-Agent'] = new_ua

    def _rate_limit_wait(self):
        """Implement rate limiting to respect server limits."""
        current_time = datetime.now()
        
        if (current_time - self.minute_start).total_seconds() >= 60:
            self.requests_this_minute = 0
            self.minute_start = current_time
        
        if self.requests_this_minute >= 25:
            sleep_time = 60 - (current_time - self.minute_start).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
                self.minute_start = datetime.now()
                self.requests_this_minute = 0
        
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        
        self.last_request_time = time.time()
        self.requests_this_minute += 1

    def _make_request(self, url: str, retries: int = 0) -> Optional[requests.Response]:
        """Make HTTP request with rate limiting and retry logic, with Cloudflare bypass."""
        try:
            self._rate_limit_wait()
            self._rotate_user_agent()
            
            # Try regular requests first
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logging.warning(f"Regular request failed for {url}: {e}")
                
                # Try cloudscraper if available
                if self.cloudscraper_session:
                    try:
                        logging.info(f"Attempting cloudscraper for {url}")
                        response = self.cloudscraper_session.get(url, timeout=20)
                        response.raise_for_status()
                        return response
                    except Exception as e2:
                        logging.warning(f"Cloudscraper failed for {url}: {e2}")
                
                # Try undetected driver as last resort
                if self.use_undetected and UNDETECTED_AVAILABLE:
                    try:
                        logging.info(f"Attempting undetected driver for {url}")
                        return self._make_request_with_driver(url)
                    except Exception as e3:
                        logging.warning(f"Undetected driver failed for {url}: {e3}")
                
                raise e
            
        except requests.exceptions.RequestException as e:
            if retries < self.max_retries:
                logging.warning(f"Request failed for {url}, retrying ({retries + 1}/{self.max_retries}): {e}")
                time.sleep(2 ** retries)  # Exponential backoff
                return self._make_request(url, retries + 1)
            else:
                logging.error(f"Failed to fetch {url} after {self.max_retries} retries: {e}")
                return None

    def _make_request_with_driver(self, url: str) -> Optional[requests.Response]:
        """Make request using undetected Chrome driver."""
        if not self.driver:
            self.driver = self._init_undetected_driver()
            if not self.driver:
                return None
        
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source
            page_source = self.driver.page_source
            
            # Create a mock response object
            class MockResponse:
                def __init__(self, text, status_code=200):
                    self.text = text
                    self.status_code = status_code
                
                def raise_for_status(self):
                    if self.status_code >= 400:
                        raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")
            
            return MockResponse(page_source)
            
        except Exception as e:
            logging.error(f"Driver request failed for {url}: {e}")
            return None

    def scrape_ufc_profile(self, fighter_name: str) -> Optional[Dict]:
        """Scrape comprehensive fighter data from UFC.com using A1 techniques."""
        try:
            # Format fighter name for URL
            formatted_name = urllib.parse.quote(fighter_name.lower().replace(' ', '-'))
            url = f"https://www.ufc.com/athlete/{formatted_name}"
            
            response = self._make_request(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Use the same comprehensive extraction as HTML processing
            fighter_data = self._extract_fighter_data_from_html(soup, fighter_name)
            if fighter_data:
                fighter_data['Source'] = 'UFC.com'  # Override source
            
            # Save HTML for later processing
            html_file = self.output_dir / f"{fighter_name.replace(' ', '_')}_ufc.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return fighter_data
            
        except Exception as e:
            logging.error(f"Error scraping UFC profile for {fighter_name}: {e}")
            return None

    def scrape_espn_profile(self, fighter_name: str) -> Optional[Dict]:
        """Scrape fighter data from ESPN."""
        try:
            # ESPN URL format (this would need to be adjusted based on ESPN's actual URL structure)
            formatted_name = urllib.parse.quote(fighter_name.lower().replace(' ', '-'))
            url = f"https://www.espn.com/mma/fighter/_/name/{formatted_name}"
            
            response = self._make_request(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            fighter_data = {
                'Name': fighter_name,
                'Source': 'ESPN'
            }
            
            # Extract ESPN-specific data
            # This would need to be customized based on ESPN's HTML structure
            
            # Save HTML for later processing
            html_file = self.output_dir / f"{fighter_name.replace(' ', '_')}_espn.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return fighter_data
            
        except Exception as e:
            logging.error(f"Error scraping ESPN profile for {fighter_name}: {e}")
            return None

    def process_fighter_data(self, fighter_data: Dict) -> Tuple[Dict, List, List, List]:
        """Process raw fighter data into specialized datasets."""
        profile = fighter_data.copy()
        
        # Extract striking data
        striking_record = {
            'Player': fighter_data.get('Name', ''),
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Opponent': 'N/A',
            'Event': 'N/A',
            'Result': 'N/A',
            'SDBL/A': fighter_data.get('Strikes by Position - Standing', '0/0'),
            'SDHL/A': fighter_data.get('Strikes by Position - Clinch', '0/0'),
            'SDLL/A': fighter_data.get('Strikes by Position - Ground', '0/0'),
            'TSL': fighter_data.get('Sig. Strikes Landed', '0'),
            'TSA': fighter_data.get('Sig. Strikes Attempted', '0'),
            'SSL': fighter_data.get('Sig. Strikes Landed', '0'),
            'SSA': fighter_data.get('Sig. Strikes Attempted', '0'),
            'TSL-TSA': f"{fighter_data.get('Striking Accuracy', '0%')}",
            'KD': fighter_data.get('Knockdown Avg', '0'),
            '%BODY': fighter_data.get('Sig. Str. by target - Body Strike Percentage', '0%'),
            '%HEAD': fighter_data.get('Sig. Str. by target - Head Strike Percentage', '0%'),
            '%LEG': fighter_data.get('Sig. Str. by target - Leg Strike Percentage', '0%')
        }
        
        # Extract ground data
        ground_record = {
            'Player': fighter_data.get('Name', ''),
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Opponent': 'N/A',
            'Event': 'N/A',
            'Result': 'N/A',
            'SGBL': '0',  # Standing Ground Body Landed
            'SGBA': '0',  # Standing Ground Body Attempted
            'SGHL': '0',  # Standing Ground Head Landed
            'SGHA': '0',  # Standing Ground Head Attempted
            'SGLL': '0',  # Standing Ground Leg Landed
            'SGLA': '0',  # Standing Ground Leg Attempted
            'AD': fighter_data.get('Takedown avg Per 15 Min', '0'),
            'ADHG': '0',  # Additional ground metrics
            'ADTB': '0',
            'ADT': '0',
            'ADTS': '0',
            'SM': fighter_data.get('Submission avg Per 15 Min', '0')
        }
        
        # Extract clinch data
        clinch_record = {
            'fighters': fighter_data.get('Name', '')
        }
        
        return profile, [striking_record], [ground_record], [clinch_record]

    def process_existing_html_files(self, html_dir: str = 'fighter_profiles (20250215)') -> None:
        """Process existing HTML files to extract fighter data."""
        html_path = Path(html_dir)
        if not html_path.exists():
            logging.warning(f"HTML directory {html_dir} not found")
            return
        
        logging.info(f"Processing existing HTML files from {html_dir}")
        
        html_files = list(html_path.glob('*.html'))
        logging.info(f"Found {len(html_files)} HTML files to process")
        
        for html_file in tqdm(html_files, desc="Processing HTML files"):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract fighter name from filename
                fighter_name = html_file.stem.replace('_', ' ')
                
                # Extract fighter data using the same logic as scraping
                fighter_data = self._extract_fighter_data_from_html(soup, fighter_name)
                
                if fighter_data:
                    profile, striking, ground, clinch = self.process_fighter_data(fighter_data)
                    self.fighter_profiles.append(profile)
                    self.striking_data.extend(striking)
                    self.ground_data.extend(ground)
                    self.clinch_data.extend(clinch)
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
            'Source': 'HTML File'
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
                    fighter_data['Division Title'] = division_elem.text.strip()
            except AttributeError:
                pass
            
            # Record info
            try:
                record_elem = hero_info_div.find(class_='hero-profile__division-body')
                if record_elem:
                    fighter_data['Division Record'] = record_elem.text.strip()
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



    def scrape_fighters(self, fighters: List[str]) -> None:
        """Scrape data for all fighters."""
        logging.info(f"Starting to scrape data for {len(fighters)} fighters")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit UFC scraping tasks
            ufc_futures = {executor.submit(self.scrape_ufc_profile, fighter): fighter for fighter in fighters}
            
            # Process completed tasks
            for future in tqdm(ufc_futures, desc="Scraping UFC profiles"):
                fighter_name = ufc_futures[future]
                try:
                    fighter_data = future.result()
                    if fighter_data:
                        self.success_count += 1
                        profile, striking, ground, clinch = self.process_fighter_data(fighter_data)
                        self.fighter_profiles.append(profile)
                        self.striking_data.extend(striking)
                        self.ground_data.extend(ground)
                        self.clinch_data.extend(clinch)
                        logging.info(f"Successfully scraped {fighter_name}")
                    else:
                        self.failure_count += 1
                        logging.warning(f"Failed to scrape {fighter_name}")
                except Exception as e:
                    self.failure_count += 1
                    logging.error(f"Error processing {fighter_name}: {e}")

    def save_data(self) -> None:
        """Save all processed data to CSV files."""
        logging.info("Saving data to CSV files...")
        
        # Save fighter profiles
        if self.fighter_profiles:
            df_profiles = pd.DataFrame(self.fighter_profiles)
            df_profiles.to_csv('fighter_profiles.csv', index=False)
            logging.info(f"Saved {len(self.fighter_profiles)} fighter profiles")
        
        # Save striking data
        if self.striking_data:
            df_striking = pd.DataFrame(self.striking_data)
            df_striking.to_csv('striking_data.csv', index=False)
            logging.info(f"Saved {len(self.striking_data)} striking records")
        
        # Save ground data
        if self.ground_data:
            df_ground = pd.DataFrame(self.ground_data)
            df_ground.to_csv('ground_data.csv', index=False)
            logging.info(f"Saved {len(self.ground_data)} ground records")
        
        # Save clinch data
        if self.clinch_data:
            df_clinch = pd.DataFrame(self.clinch_data)
            df_clinch.to_csv('clinch_data.csv', index=False)
            logging.info(f"Saved {len(self.clinch_data)} clinch records")

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("Closed undetected driver")
            except:
                pass

    def run_pipeline(self, fighters_file: str = 'fighters_name.csv', use_existing_html: bool = True) -> None:
        """Run the complete UFC fighter data pipeline."""
        logging.info("Starting UFC Fighter Data Pipeline")
        
        # Load fighter names
        try:
            df = pd.read_csv(fighters_file)
            if 'Fighter Name' in df.columns:
                fighters = df['Fighter Name'].tolist()
            elif 'fighters' in df.columns:
                fighters = df['fighters'].tolist()
            else:
                logging.error(f"Could not find 'Fighter Name' or 'fighters' column in {fighters_file}")
                return
        except Exception as e:
            logging.error(f"Error loading fighter names from {fighters_file}: {e}")
            return
        
        logging.info(f"Loaded {len(fighters)} fighters from {fighters_file}")
        
        # First, process existing HTML files if available
        if use_existing_html:
            self.process_existing_html_files()
            logging.info(f"Processed existing HTML files. Success: {self.success_count}, Failures: {self.failure_count}")
        
        # Identify fighters that still need to be scraped
        processed_names = {profile['Name'] for profile in self.fighter_profiles}
        remaining_fighters = [f for f in fighters if f not in processed_names]
        
        if remaining_fighters:
            logging.info(f"Need to scrape {len(remaining_fighters)} additional fighters")
            self.scrape_fighters(remaining_fighters)
        else:
            logging.info("All fighters already processed from existing HTML files")
        
        # Save processed data
        self.save_data()
        
        # Print summary
        logging.info(f"Pipeline completed!")
        logging.info(f"Success: {self.success_count}, Failures: {self.failure_count}")
        logging.info(f"Total fighters processed: {len(fighters)}")
        
        # Cleanup
        self.cleanup()

def main():
    """Main entry point for the UFC fighter pipeline."""
    # Create pipeline instance with enhanced Cloudflare bypass
    pipeline = UFCFighterPipeline(
        output_dir='fighter_profiles',
        max_workers=2,  # Reduced for stability with undetected driver
        rate_limit=3.0,  # Increased for better success rate
        max_retries=3,
        use_undetected=True
    )
    
    try:
        # Run the pipeline
        pipeline.run_pipeline()
    except KeyboardInterrupt:
        logging.info("Pipeline interrupted by user")
        pipeline.cleanup()
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        pipeline.cleanup()
        raise

if __name__ == "__main__":
    main() 