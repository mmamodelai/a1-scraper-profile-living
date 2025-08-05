#!/usr/bin/env python3
"""
UFC Fighter HTML Scraper
Dedicated script for scraping fighter profiles from UFC.com and saving HTML files.
Uses advanced Cloudflare bypass techniques.
"""

import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time
import logging
from typing import Dict, List, Optional
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime
import urllib.parse
from bs4 import BeautifulSoup

# Advanced scraping imports for Cloudflare bypass
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
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

class UFCScraper:
    """Dedicated UFC fighter profile scraper with Cloudflare bypass."""
    
    def __init__(self, output_dir: str = 'fighter_profiles', max_workers: int = 2, 
                 rate_limit: float = 3.0, max_retries: int = 3, use_undetected: bool = True):
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
            options.add_argument('--disable-javascript')
            
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

    def scrape_fighter_profile(self, fighter_name: str) -> bool:
        """Scrape a single fighter profile and save HTML."""
        try:
            # Format fighter name for URL
            formatted_name = urllib.parse.quote(fighter_name.lower().replace(' ', '-'))
            url = f"https://www.ufc.com/athlete/{formatted_name}"
            
            response = self._make_request(url)
            if not response:
                return False
            
            # Save HTML file (upsert mode - overwrites existing files)
            html_file = self.output_dir / f"{fighter_name.replace(' ', '_')}_ufc.html"
            if html_file.exists():
                logging.info(f"Overwriting existing UFC HTML for {fighter_name}")
            else:
                logging.info(f"Creating new UFC HTML for {fighter_name}")
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return True
            
        except Exception as e:
            logging.error(f"Error scraping UFC profile for {fighter_name}: {e}")
            return False

    def scrape_fighters(self, fighters: List[str]) -> None:
        """Scrape data for all fighters."""
        logging.info(f"Starting to scrape data for {len(fighters)} fighters")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit scraping tasks
            futures = {executor.submit(self.scrape_fighter_profile, fighter): fighter for fighter in fighters}
            
            # Process completed tasks
            for future in tqdm(futures, desc="Scraping UFC profiles"):
                fighter_name = futures[future]
                try:
                    success = future.result()
                    if success:
                        self.success_count += 1
                        logging.info(f"Successfully scraped {fighter_name}")
                    else:
                        self.failure_count += 1
                        logging.warning(f"Failed to scrape {fighter_name}")
                except Exception as e:
                    self.failure_count += 1
                    logging.error(f"Error processing {fighter_name}: {e}")

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("Closed undetected driver")
            except:
                pass

    def run_scraper(self, fighters_file: str = 'fighters_name.csv') -> None:
        """Run the UFC scraper."""
        logging.info("Starting UFC Fighter Scraper")
        
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
        
        # Scrape all fighters
        self.scrape_fighters(fighters)
        
        # Print summary
        logging.info(f"Scraper completed!")
        logging.info(f"Success: {self.success_count}, Failures: {self.failure_count}")
        logging.info(f"Total fighters processed: {len(fighters)}")
        
        # Cleanup
        self.cleanup()

def main():
    """Main entry point for the UFC scraper."""
    # Create scraper instance
    scraper = UFCScraper(
        output_dir='fighter_profiles',
        max_workers=2,
        rate_limit=3.0,
        max_retries=3,
        use_undetected=True
    )
    
    try:
        # Run the scraper
        scraper.run_scraper()
    except KeyboardInterrupt:
        logging.info("Scraper interrupted by user")
        scraper.cleanup()
    except Exception as e:
        logging.error(f"Scraper failed: {e}")
        scraper.cleanup()
        raise

if __name__ == "__main__":
    main() 