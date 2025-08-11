#!/usr/bin/env python3

import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import os
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import random
from datetime import datetime

class ESPNFighterScraper:
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]

    def __init__(self, output_dir: str = 'fighter_profiles', max_workers: int = 3, 
                 rate_limit: float = 2.0, max_retries: int = 5):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.session = self._create_session()
        
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0
        self.request_count = 0
        self.requests_this_minute = 0
        self.minute_start = datetime.now()

    def _create_session(self) -> requests.Session:
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
        
        session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session

    def _rotate_user_agent(self):
        self.session.headers['User-Agent'] = random.choice(self.USER_AGENTS)

    def _rate_limit_wait(self):
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

    def _make_request(self, url: str, retries: int = 0) -> requests.Response:
        try:
            self._rate_limit_wait()
            self._rotate_user_agent()
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403 and retries < self.max_retries:
                wait_time = (2 ** retries) + random.uniform(0, 1)
                logging.warning(f"403 error, waiting {wait_time:.2f} seconds before retry {retries + 1}")
                time.sleep(wait_time)
                return self._make_request(url, retries + 1)
            raise

    def fetch_fighter_data(self, fighter_name: str) -> Optional[Dict]:
        try:
            # Step 1: Search for fighter
            encoded_name = requests.utils.quote(fighter_name)
            search_url = f"https://site.web.api.espn.com/apis/search/v2?region=us&lang=en&limit=10&page=1&query={encoded_name}"
            
            search_response = self._make_request(search_url)
            data_json = search_response.json()
            
            # Find player data
            player_json_data = None
            if "results" in data_json:
                for result in data_json["results"]:
                    if result.get("type") == "player":
                        contents = result.get("contents", [])
                        if isinstance(contents, list):
                            for content in contents:
                                if content.get("sport") == "mma":
                                    player_json_data = content
                                    break
                    if player_json_data:
                        break
            
            if not player_json_data:
                logging.warning(f"No MMA fighter found for {fighter_name}")
                self.failure_count += 1
                return None
            
            # Step 2: Get fighter stats page
            profile_url = player_json_data["link"]["web"]
            stats_url = profile_url.replace("/_/id/", "/stats/_/id/")
            
            profile_response = self._make_request(stats_url)
            
            # Save HTML content (upsert mode - overwrites existing files)
            file_path = self.output_dir / f"{fighter_name.replace(' ', '_')}.html"
            if file_path.exists():
                logging.info(f"Overwriting existing ESPN HTML for {fighter_name}")
            else:
                logging.info(f"Creating new ESPN HTML for {fighter_name}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(profile_response.text)
            
            self.success_count += 1
            logging.info(f"Successfully processed {fighter_name}")
            
            return {
                'name': fighter_name,
                'profile_url': profile_url,
                'stats_url': stats_url,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            self.failure_count += 1
            logging.error(f"Error processing {fighter_name}: {str(e)}")
            return None

    def process_saved_profiles(self) -> Dict[str, pd.DataFrame]:
        section_data = {
            'striking': [],
            'Clinch': [],
            'Ground': []
        }
        
        columns = {
            'striking': ['Date', 'Opponent', 'Event', 'Result', 'SDBL/A', 'SDHL/A', 'SDLL/A', 
                        'TSL', 'TSA', 'SSL', 'SSA', 'TSL-TSA', 'KD', '%BODY', '%HEAD', '%LEG'],
            'Clinch': ['Date', 'Opponent', 'Event', 'Result', 'SCBL', 'SCBA', 'SCHL', 'SCHA',
                      'SCLL', 'SCLA', 'RV', 'SR', 'TDL', 'TDA', 'TDS', 'TK ACC'],
            'Ground': ['Date', 'Opponent', 'Event', 'Result', 'SGBL', 'SGBA', 'SGHL', 'SGHA',
                      'SGLL', 'SGLA', 'AD', 'ADHG', 'ADTB', 'ADTM', 'ADTS', 'SM']
        }

        for file_path in self.output_dir.glob('*.html'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'lxml')
                
                player_name_elem = soup.find('h1', class_='PlayerHeader__Name')
                player_name = player_name_elem.get_text(strip=True) if player_name_elem else 'Unknown Player'
                
                for section in ['striking', 'Clinch', 'Ground']:
                    title_div = soup.find('div', string=section)
                    if title_div:
                        table = title_div.find_next('table')
                        if table:
                            rows = table.find_all('tr')[1:]  # Skip header
                            for row in rows:
                                cols = [td.get_text(strip=True) for td in row.find_all('td')]
                                if len(cols) >= len(columns[section]):
                                    data = {'Player': player_name}
                                    data.update(dict(zip(columns[section], cols)))
                                    section_data[section].append(data)
            
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {str(e)}")

        # Convert to DataFrames if there's data
        result_dfs = {}
        for section, data in section_data.items():
            if data:  # Only create DataFrame if there's data
                result_dfs[section] = pd.DataFrame(data)
            else:
                logging.warning(f"No data found for section: {section}")
                result_dfs[section] = pd.DataFrame(columns=['Player'] + columns[section])
                
        return result_dfs

    def scrape_fighters(self, fighters: List[str]) -> Dict[str, pd.DataFrame]:
        logging.info(f"Starting scrape for {len(fighters)} fighters")
        
        chunk_size = 50
        all_results = []
        
        for i in range(0, len(fighters), chunk_size):
            chunk = fighters[i:i + chunk_size]
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                chunk_results = list(tqdm(
                    executor.map(self.fetch_fighter_data, chunk),
                    total=len(chunk),
                    desc=f"Processing fighters {i+1}-{min(i+chunk_size, len(fighters))}"
                ))
                all_results.extend(chunk_results)
            
            if i + chunk_size < len(fighters):
                pause_time = random.uniform(5, 10)
                logging.info(f"Pausing for {pause_time:.2f} seconds between chunks")
                time.sleep(pause_time)
        
        successful_fighters = [r for r in all_results if r is not None]
        logging.info(f"Successfully processed {len(successful_fighters)} out of {len(fighters)} fighters")
        
        section_dfs = self.process_saved_profiles()
        
        for section, df in section_dfs.items():
            output_path = f'{section.lower()}_data.csv'
            df.to_csv(output_path, index=False)
            logging.info(f"Saved {section} data to {output_path}")
        
        return section_dfs


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler()
        ]
    )
    
    script_dir = Path(__file__).parent.absolute()
    fighters_csv_path = script_dir / 'fighters_name.csv'
    
    try:
        fighters_df = pd.read_csv(fighters_csv_path)
        fighters = fighters_df["Fighter Name"].tolist()

        # Optional sampling controls via env vars
        try:
            sample_mod_raw = os.environ.get('SAMPLE_MOD', '').strip()
            sample_offset_raw = os.environ.get('SAMPLE_OFFSET', '').strip()
            max_count_raw = os.environ.get('MAX_COUNT', '').strip()

            if sample_mod_raw:
                mod = int(sample_mod_raw)
                offset = int(sample_offset_raw) if sample_offset_raw else 0
                if mod > 0:
                    fighters = [name for idx, name in enumerate(fighters) if idx % mod == offset]
            if max_count_raw:
                limit = int(max_count_raw)
                if limit > 0:
                    fighters = fighters[:limit]
        except Exception as e:
            logging.warning(f"Sampling controls ignored due to error: {e}")
        
        logging.info(f"Found {len(fighters)} fighters in {fighters_csv_path} after sampling filters")
        
        scraper = ESPNFighterScraper(
            output_dir=script_dir / 'fighter_profiles',
            max_workers=3,
            rate_limit=2.0
        )
        
        results = scraper.scrape_fighters(fighters)
        
        print("\nScraping Summary:")
        print(f"Total Success Cases: {scraper.success_count}")
        print(f"Total Failure Cases: {scraper.failure_count}")
        
        for section, df in results.items():
            print(f"\nSection: {section}")
            if not df.empty:
                print(df.head())
            else:
                print("No data available")
            
    except FileNotFoundError:
        logging.error(f"Could not find fighters_name.csv in {script_dir}")
        print(f"Error: fighters_name.csv not found in {script_dir}")
        print("Please ensure fighters_name.csv is in the same directory as this script.")
        return
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        print(f"An error occurred: {str(e)}")
        return


if __name__ == "__main__":
    main()