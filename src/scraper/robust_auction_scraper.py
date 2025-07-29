import logging
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import undetected_chromedriver as uc
from urllib.parse import urljoin

from src.config.settings import AUCTION_CONFIG, SCRAPER_CONFIG, WATCH_KEYWORDS, AVOID_KEYWORDS
from src.scraper.rate_limiter import PoliteRateLimiter
from src.scraper.utils import ScraperUtils
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class RobustAuctionScraper:
    """Ultra-robust scraper that focuses solely on clicking Next buttons with extensive retry logic"""
    
    def __init__(self, headless: bool = True):
        """Initialize the auction scraper"""
        self.base_url = AUCTION_CONFIG['base_url']
        self.headless = headless
        self.driver = None
        self.wait = None
        self.rate_limiter = PoliteRateLimiter(
            min_delay=AUCTION_CONFIG['scrape_delay_min'],
            max_delay=AUCTION_CONFIG['scrape_delay_max'],
            requests_per_minute=AUCTION_CONFIG['requests_per_minute']
        )
        self.utils = ScraperUtils()
        self.db_manager = DatabaseManager()
        self.session_id = None
        
        # Robust scraping parameters
        self.max_retries = 5
        self.retry_delay = 3
        self.page_load_timeout = 15
        self.element_timeout = 10
        
    def setup_driver(self):
        """Set up Chrome driver with anti-detection and stability measures"""
        try:
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Stability and anti-detection options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Speed up loading
            options.add_argument('--disable-javascript')  # Reduce complexity
            
            # Set timeouts
            options.add_argument(f'--page-load-strategy=normal')
            
            if SCRAPER_CONFIG['user_agent_rotation']:
                user_agent = self.utils.get_random_user_agent()
                options.add_argument(f'user-agent={user_agent}')
            
            self.driver = uc.Chrome(options=options)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            self.wait = WebDriverWait(self.driver, self.element_timeout)
            
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            logger.info("Robust Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup driver: {e}")
            raise
    
    def teardown_driver(self):
        """Safely close the driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    def find_auction_groups(self) -> List[str]:
        """Find all auction group links on the main page with retry logic"""
        auction_links = []
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Navigating to {self.base_url} (attempt {attempt + 1})")
                self.driver.get(self.base_url)
                time.sleep(5)  # Give page time to load
                
                # Look for auction group links
                selectors_to_try = [
                    "h4.AuctionGroupsLink a",
                    ".auction-groups a",
                    ".auction-group-section a",
                    "a[href*='/auction/']",
                    ".card a[href*='auction']"
                ]
                
                for selector in selectors_to_try:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            logger.info(f"Found {len(elements)} auction links using selector: {selector}")
                            for element in elements:
                                href = element.get_attribute('href')
                                if href and '/auction/' in href:
                                    full_url = urljoin(self.base_url, href)
                                    if full_url not in auction_links:
                                        auction_links.append(full_url)
                                        title = element.get_attribute('textContent') or 'Unknown Auction'
                                        logger.info(f"Found auction: {title.strip()}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if auction_links:
                    break
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"All attempts failed to find auction groups")
                    break
        
        logger.info(f"Total auction groups found: {len(auction_links)}")
        return auction_links
    
    def navigate_through_all_items(self, auction_url: str) -> List[Dict[str, Any]]:
        """Navigate through ALL items using only Next button clicks with extensive retry logic"""
        items = []
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        try:
            logger.info(f"Starting robust item navigation for: {auction_url}")
            
            # Go to first item
            first_item_url = self.find_and_navigate_to_first_item(auction_url)
            if not first_item_url:
                logger.error("Could not find or navigate to first item")
                return items
            
            current_item_number = 1
            
            while consecutive_failures < max_consecutive_failures:
                try:
                    # Extract current item with retry logic
                    item = self.extract_current_item_with_retry()
                    
                    if item:
                        items.append(item)
                        logger.info(f"Extracted item {current_item_number}: {item['title'][:50]}")
                        consecutive_failures = 0  # Reset failure counter
                        current_item_number += 1
                    else:
                        logger.warning(f"Failed to extract item {current_item_number}")
                        consecutive_failures += 1
                    
                    # Try to go to next item with retry logic
                    if not self.click_next_button_with_retry():
                        logger.info("No more Next buttons found - reached end of auction")
                        break
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing item {current_item_number}: {e}")
                    consecutive_failures += 1
                    
                    if consecutive_failures < max_consecutive_failures:
                        logger.info(f"Retrying after error... ({consecutive_failures}/{max_consecutive_failures})")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error("Too many consecutive failures, stopping")
                        break
            
            logger.info(f"Navigation completed. Total items found: {len(items)}")
            
        except Exception as e:
            logger.error(f"Critical error in navigation: {e}")
        
        return items
    
    def find_and_navigate_to_first_item(self, auction_url: str) -> Optional[str]:
        """Find and navigate to the first item with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Loading auction page (attempt {attempt + 1}): {auction_url}")
                self.driver.get(auction_url)
                time.sleep(5)
                
                # Look for first item link
                first_item_selectors = [
                    "a[href*='lot-1']",
                    "a[href*='item-1']",
                    "a[href*='/1/']",
                    "a[href*='lot/1']"
                ]
                
                for selector in first_item_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            first_url = elements[0].get_attribute('href')
                            if first_url:
                                logger.info(f"Found first item URL: {first_url}")
                                self.driver.get(first_url)
                                time.sleep(3)
                                return first_url
                    except Exception as e:
                        continue
                
                # Fallback: look for any lot link
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                    lot_match = re.search(r'Lot #(\d+)', page_text)
                    if lot_match:
                        logger.info(f"Found lot reference: {lot_match.group()}")
                        return auction_url  # Stay on current page
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to find first item failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
        
        logger.error("Could not find first item after all attempts")
        return None
    
    def extract_current_item_with_retry(self) -> Optional[Dict[str, Any]]:
        """Extract current item information with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Wait for page to load
                time.sleep(2)
                
                # Get page text
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                
                # Look for lot title pattern
                title_match = re.search(r'Lot #\d+[^\n]*', page_text, re.IGNORECASE)
                if not title_match:
                    if attempt < self.max_retries - 1:
                        logger.debug(f"No lot title found, retrying... (attempt {attempt + 1})")
                        time.sleep(2)
                        continue
                    else:
                        logger.debug("No lot title found after all attempts")
                        return None
                
                title = title_match.group().strip()
                
                # Extract current bid/price
                current_bid = 0.0
                price_patterns = [
                    r'Current bid:?\s*\$?([\d,]+\.?\d*)',
                    r'Starting bid:?\s*\$?([\d,]+\.?\d*)',
                    r'Price:?\s*\$?([\d,]+\.?\d*)',
                    r'\$\s*([\d,]+\.?\d*)'
                ]
                
                for pattern in price_patterns:
                    price_match = re.search(pattern, page_text, re.IGNORECASE)
                    if price_match:
                        try:
                            current_bid = float(price_match.group(1).replace(',', ''))
                            break
                        except:
                            continue
                
                # Generate auction ID from URL
                current_url = self.driver.current_url
                auction_id = f"robust_{hash(current_url + title) % 100000}"
                
                # Default auction end time
                auction_end = datetime.now() + timedelta(days=7)
                
                item_data = {
                    'auction_id': auction_id,
                    'title': title[:200],
                    'current_bid': current_bid,
                    'auction_url': current_url,
                    'auction_end': auction_end,
                    'description': title
                }
                
                return item_data
                
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} to extract item failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
        
        logger.warning("Failed to extract item after all attempts")
        return None
    
    def click_next_button_with_retry(self) -> bool:
        """Click Next button with extensive retry logic"""
        for attempt in range(self.max_retries):
            try:
                current_url = self.driver.current_url
                
                # Wait for page to be ready
                time.sleep(1)
                
                # Look for Next button using multiple strategies
                next_button_found = False
                
                # Strategy 1: XPath for text content
                xpath_selectors = [
                    "//button[contains(text(), 'Next')]",
                    "//a[contains(text(), 'Next')]",
                    "//button[contains(text(), '→')]",
                    "//button[contains(text(), '>')]",
                    "//input[@type='button' and contains(@value, 'Next')]"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                logger.debug(f"Found Next button using {xpath}")
                                element.click()
                                next_button_found = True
                                break
                        if next_button_found:
                            break
                    except Exception as e:
                        continue
                
                # Strategy 2: CSS selectors
                if not next_button_found:
                    css_selectors = [
                        ".next-button",
                        ".btn-next",
                        "[onclick*='next']",
                        "[onclick*='forward']",
                        "button.btn.btn-primary"
                    ]
                    
                    for selector in css_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    text = element.text.lower()
                                    if 'next' in text or '>' in text or '→' in text:
                                        logger.debug(f"Found Next button using {selector}")
                                        element.click()
                                        next_button_found = True
                                        break
                            if next_button_found:
                                break
                        except Exception as e:
                            continue
                
                if not next_button_found:
                    if attempt < self.max_retries - 1:
                        logger.debug(f"Next button not found, retrying... (attempt {attempt + 1})")
                        time.sleep(2)
                        continue
                    else:
                        logger.debug("Next button not found after all attempts")
                        return False
                
                # Wait for navigation to complete
                time.sleep(3)
                
                # Check if URL changed (successful navigation)
                new_url = self.driver.current_url
                if new_url != current_url:
                    logger.debug(f"Successfully navigated to: {new_url}")
                    return True
                else:
                    if attempt < self.max_retries - 1:
                        logger.debug(f"URL didn't change, retrying... (attempt {attempt + 1})")
                        time.sleep(2)
                        continue
                    else:
                        logger.debug("Navigation failed - URL didn't change")
                        return False
                        
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} to click Next button failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
        
        logger.debug("Failed to click Next button after all attempts")
        return False
    
    def run(self, max_auction_groups: int = 3) -> Dict[str, Any]:
        """Run the robust scraping process"""
        results = {
            'items_found': 0,
            'items_flagged': 0,
            'valuable_items': [],
            'watchlist_matches': [],
            'errors': []
        }
        
        try:
            self.setup_driver()
            self.session_id = self.db_manager.create_scrape_session()
            logger.info("Starting robust auction scraping...")
            
            # Find auction groups
            auction_links = self.find_auction_groups()
            
            if not auction_links:
                logger.warning("No auction groups found!")
                results['errors'].append("No auction groups found on main page")
                return results
            
            # Scrape each auction group
            all_items = []
            for i, auction_url in enumerate(auction_links[:max_auction_groups]):
                logger.info(f"Processing auction group {i+1}/{min(len(auction_links), max_auction_groups)}")
                
                items = self.navigate_through_all_items(auction_url)
                all_items.extend(items)
                logger.info(f"Found {len(items)} items in auction group {i+1}")
                
                # Rate limiting between groups
                self.rate_limiter.wait()
            
            # Process and save items
            for item in all_items:
                try:
                    # Check if item is valuable
                    value_analysis = self.utils.is_valuable_item(
                        item['title'], 
                        item.get('description', '')
                    )
                    
                    # Save to database
                    item_id = self.db_manager.save_item(item)
                    
                    if value_analysis['value_score'] > 0:
                        results['items_flagged'] += 1
                        results['valuable_items'].append({
                            'title': item['title'],
                            'current_bid': item['current_bid'],
                            'keywords': value_analysis['keywords_found'],
                            'url': item['auction_url']
                        })
                        
                        logger.info(f"Flagged valuable item: {item['title'][:50]} - ${item['current_bid']}")
                    
                except Exception as e:
                    logger.error(f"Error processing item {item.get('title', 'Unknown')}: {e}")
                    results['errors'].append(f"Error processing item: {e}")
            
            results['items_found'] = len(all_items)
            
            # Update session
            self.db_manager.update_scrape_session(
                self.session_id,
                ended_at=datetime.now(),
                items_found=results['items_found'],
                items_flagged=results['items_flagged'],
                status='completed'
            )
            
            # Mark expired items
            expired_count = self.db_manager.mark_expired_items()
            logger.info(f"Marked {expired_count} expired items")
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            results['errors'].append(f"Scraping error: {e}")
            
            if self.session_id:
                self.db_manager.update_scrape_session(
                    self.session_id,
                    ended_at=datetime.now(),
                    status='error',
                    error_message=str(e)
                )
        
        finally:
            self.teardown_driver()
        
        return results