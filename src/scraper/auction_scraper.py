import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

from src.config.settings import AUCTION_CONFIG, SCRAPER_CONFIG, WATCH_KEYWORDS, AVOID_KEYWORDS
from src.scraper.rate_limiter import PoliteRateLimiter
from src.scraper.utils import ScraperUtils
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AuctionScraper:
    """Main scraper for slocalestateauctions.com"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the auction scraper
        
        Args:
            headless: Run browser in headless mode
        """
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
        
    def setup_driver(self):
        """Set up Chrome driver with anti-detection measures"""
        try:
            # Use undetected-chromedriver for better anti-detection
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Standard options for stability
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            
            # Set window size for consistency
            options.add_argument('--window-size=1920,1080')
            
            # Set user agent if rotation is enabled
            if SCRAPER_CONFIG['user_agent_rotation']:
                user_agent = self.utils.get_random_user_agent()
                options.add_argument(f'user-agent={user_agent}')
            
            # Create driver
            self.driver = uc.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, SCRAPER_CONFIG['timeout'])
            
            # Additional anti-detection JavaScript
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            logger.info("Chrome driver initialized successfully")
            
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
    
    def scrape_auction_listings(self, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape auction listings from the main page
        
        Args:
            max_pages: Maximum number of pages to scrape
        
        Returns:
            List of auction items
        """
        if max_pages is None:
            max_pages = AUCTION_CONFIG['max_pages_per_run']
        
        all_auctions = []
        page = 1
        
        try:
            # Navigate to the base URL
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            self.rate_limiter.wait()
            
            while page <= max_pages:
                logger.info(f"Scraping page {page}")
                
                # Wait for auction items to load
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "auction-item"))
                    )
                except TimeoutException:
                    # Try alternative selectors
                    try:
                        self.wait.until(
                            EC.presence_of_element_located((By.CLASS_NAME, "item"))
                        )
                    except TimeoutException:
                        logger.warning("No auction items found on page")
                        break
                
                # Extract auction items
                items = self.extract_auction_items()
                all_auctions.extend(items)
                
                logger.info(f"Found {len(items)} items on page {page}")
                
                # Try to go to next page
                if not self.go_to_next_page():
                    logger.info("No more pages available")
                    break
                
                page += 1
                self.rate_limiter.wait()
                
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        
        return all_auctions
    
    def extract_auction_items(self) -> List[Dict[str, Any]]:
        """Extract auction items from the current page"""
        items = []
        
        # Try multiple possible selectors
        selectors = [
            "div.auction-item",
            "div.item",
            "article.auction",
            "li.auction-listing",
            "div.product-item"
        ]
        
        auction_elements = []
        for selector in selectors:
            auction_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if auction_elements:
                logger.debug(f"Found {len(auction_elements)} items using selector: {selector}")
                break
        
        for element in auction_elements:
            try:
                item_data = self.extract_item_details(element)
                if item_data:
                    items.append(item_data)
            except Exception as e:
                logger.error(f"Error extracting item: {e}")
                continue
        
        return items
    
    def extract_item_details(self, element) -> Optional[Dict[str, Any]]:
        """Extract details from a single auction item element"""
        try:
            # Extract title
            title = None
            title_selectors = ["h3", "h4", ".title", ".item-title", "a"]
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue
            
            if not title:
                logger.warning("Could not find title for item")
                return None
            
            # Extract current bid
            current_bid = None
            bid_selectors = [".current-bid", ".price", ".bid-amount", "span.bid"]
            for selector in bid_selectors:
                try:
                    bid_elem = element.find_element(By.CSS_SELECTOR, selector)
                    bid_text = bid_elem.text.strip()
                    current_bid = self.utils.clean_price(bid_text)
                    if current_bid is not None:
                        break
                except NoSuchElementException:
                    continue
            
            if current_bid is None:
                logger.warning(f"Could not find bid for item: {title}")
                return None
            
            # Extract URL
            url = None
            try:
                link_elem = element.find_element(By.TAG_NAME, "a")
                url = link_elem.get_attribute("href")
                url = self.utils.make_absolute_url(url, self.base_url)
            except NoSuchElementException:
                logger.warning(f"Could not find URL for item: {title}")
            
            # Extract auction ID
            auction_id = self.utils.extract_item_id(url) if url else None
            if not auction_id:
                # Generate ID from title and current time
                auction_id = f"{hash(title)}_{int(time.time())}"
            
            # Extract end time (if visible on listing)
            end_time = None
            time_selectors = [".end-time", ".time-left", ".auction-end"]
            for selector in time_selectors:
                try:
                    time_elem = element.find_element(By.CSS_SELECTOR, selector)
                    time_text = time_elem.text.strip()
                    end_time = self.utils.parse_auction_end_time(time_text)
                    if end_time:
                        break
                except NoSuchElementException:
                    continue
            
            # If no end time found, we'll need to get it from the detail page
            if not end_time:
                end_time = datetime.now() + timedelta(days=7)  # Default to 7 days
            
            # Check if item is valuable
            value_analysis = self.utils.is_valuable_item(title)
            
            # Check against watchlist keywords
            matches_watchlist = any(
                keyword.lower() in title.lower() 
                for keyword in WATCH_KEYWORDS
            )
            
            # Check for red flags
            has_red_flags = any(
                keyword.lower() in title.lower() 
                for keyword in AVOID_KEYWORDS
            )
            
            item_data = {
                'auction_id': auction_id,
                'title': title,
                'current_bid': current_bid,
                'auction_url': url,
                'auction_end': end_time,
                'category': value_analysis['categories'][0] if value_analysis['categories'] else None,
                'is_valuable': value_analysis['value_score'] > 0,
                'matches_watchlist': matches_watchlist,
                'has_red_flags': has_red_flags,
                'keywords_found': value_analysis['keywords_found'],
            }
            
            return item_data
            
        except Exception as e:
            logger.error(f"Error extracting item details: {e}")
            return None
    
    def go_to_next_page(self) -> bool:
        """Navigate to the next page of listings"""
        # Try common pagination selectors
        next_selectors = [
            "a.next",
            "a[rel='next']",
            ".pagination .next",
            "button.next-page",
            "a:contains('Next')",
            "a:contains('»')"
        ]
        
        for selector in next_selectors:
            try:
                # Try CSS selector first
                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if next_button.is_enabled():
                    next_button.click()
                    return True
            except NoSuchElementException:
                continue
            except Exception as e:
                logger.debug(f"Error clicking next button: {e}")
                continue
        
        # Try JavaScript click as fallback
        try:
            next_buttons = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Next")
            for button in next_buttons:
                if button.is_displayed():
                    self.driver.execute_script("arguments[0].click();", button)
                    return True
        except Exception:
            pass
        
        return False
    
    def scrape_item_details(self, item_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information from an item page
        
        Args:
            item_url: URL of the item detail page
        
        Returns:
            Dictionary with additional item details
        """
        try:
            logger.info(f"Scraping details from: {item_url}")
            self.driver.get(item_url)
            self.rate_limiter.wait()
            
            details = {}
            
            # Extract description
            desc_selectors = [".description", ".item-description", "#description"]
            for selector in desc_selectors:
                try:
                    desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    details['description'] = desc_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract condition
            condition_text = details.get('description', '')
            details['condition'] = self.utils.extract_condition(condition_text)
            
            # Extract more accurate end time
            time_selectors = [".countdown", ".time-remaining", ".end-date"]
            for selector in time_selectors:
                try:
                    time_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    time_text = time_elem.text.strip()
                    end_time = self.utils.parse_auction_end_time(time_text)
                    if end_time:
                        details['auction_end'] = end_time
                        break
                except NoSuchElementException:
                    continue
            
            return details
            
        except Exception as e:
            logger.error(f"Error scraping item details: {e}")
            return None
    
    def run(self, scrape_details: bool = False) -> Dict[str, Any]:
        """
        Run the complete scraping process
        
        Args:
            scrape_details: Whether to scrape individual item pages
        
        Returns:
            Summary of the scraping session
        """
        results = {
            'items_found': 0,
            'items_flagged': 0,
            'valuable_items': [],
            'watchlist_matches': [],
            'errors': []
        }
        
        try:
            # Create scraping session
            self.session_id = self.db_manager.create_scrape_session()
            
            # Setup driver
            self.setup_driver()
            
            # Scrape listings
            logger.info("Starting auction scraping...")
            items = self.scrape_auction_listings()
            results['items_found'] = len(items)
            
            # Process each item
            for item in items:
                try:
                    # Skip items with red flags
                    if item.get('has_red_flags'):
                        logger.info(f"Skipping item with red flags: {item['title']}")
                        continue
                    
                    # Get additional details if requested
                    if scrape_details and item.get('auction_url'):
                        details = self.scrape_item_details(item['auction_url'])
                        if details:
                            item.update(details)
                    
                    # Save to database
                    item_id = self.db_manager.save_item(item)
                    
                    # Flag valuable items
                    if item.get('is_valuable') or item.get('matches_watchlist'):
                        results['items_flagged'] += 1
                        
                        if item.get('is_valuable'):
                            results['valuable_items'].append({
                                'title': item['title'],
                                'current_bid': item['current_bid'],
                                'keywords': item.get('keywords_found', []),
                                'url': item.get('auction_url')
                            })
                        
                        if item.get('matches_watchlist'):
                            results['watchlist_matches'].append({
                                'title': item['title'],
                                'current_bid': item['current_bid'],
                                'url': item.get('auction_url')
                            })
                    
                except Exception as e:
                    error_msg = f"Error processing item {item.get('title', 'Unknown')}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Mark expired items
            expired_count = self.db_manager.mark_expired_items()
            logger.info(f"Marked {expired_count} expired items")
            
            # Update session
            self.db_manager.update_scrape_session(
                self.session_id,
                ended_at=datetime.now(),
                items_found=results['items_found'],
                items_flagged=results['items_flagged'],
                status='completed'
            )
            
        except Exception as e:
            error_msg = f"Scraping failed: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            
            if self.session_id:
                self.db_manager.update_scrape_session(
                    self.session_id,
                    ended_at=datetime.now(),
                    status='failed',
                    error_message=str(e)
                )
        
        finally:
            self.teardown_driver()
        
        return results