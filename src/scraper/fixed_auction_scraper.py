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
from urllib.parse import urljoin

from src.config.settings import AUCTION_CONFIG, SCRAPER_CONFIG, WATCH_KEYWORDS, AVOID_KEYWORDS
from src.scraper.rate_limiter import PoliteRateLimiter
from src.scraper.utils import ScraperUtils
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class FixedAuctionScraper:
    """Updated scraper for slocalestateauctions.com that handles the real website structure"""
    
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
        
    def setup_driver(self):
        """Set up Chrome driver with anti-detection measures"""
        try:
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            if SCRAPER_CONFIG['user_agent_rotation']:
                user_agent = self.utils.get_random_user_agent()
                options.add_argument(f'user-agent={user_agent}')
            
            self.driver = uc.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, SCRAPER_CONFIG['timeout'])
            
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
    
    def find_auction_groups(self) -> List[str]:
        """Find all auction group links on the main page"""
        auction_links = []
        
        try:
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)  # Wait for page to load
            
            # Look for auction group links - based on the HTML structure we found
            selectors_to_try = [
                "h4.AuctionGroupsLink a",  # Specific selector from page source
                ".auction-groups a",
                ".auction-group-section a",
                "a[href*='/auction/']",  # Any link containing /auction/
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
            
            logger.info(f"Total auction groups found: {len(auction_links)}")
            return auction_links
            
        except Exception as e:
            logger.error(f"Error finding auction groups: {e}")
            return []
    
    def scrape_auction_page(self, auction_url: str) -> List[Dict[str, Any]]:
        """Scrape items from a specific auction page"""
        items = []
        
        try:
            logger.info(f"Scraping auction page: {auction_url}")
            self.driver.get(auction_url)
            time.sleep(3)
            
            # Try different selectors for auction items on the individual pages
            item_selectors = [
                ".lot-item",
                ".auction-item", 
                ".item",
                ".product-item",
                ".card .card-body",
                "tr[id*='lot']",  # Table rows with lot IDs
                "div[id*='item']",
                ".row .col",  # Bootstrap grid items
                "[class*='lot']",
                "[class*='item']"
            ]
            
            item_elements = []
            for selector in item_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 1:  # More than just container
                        logger.info(f"Found {len(elements)} potential items using: {selector}")
                        item_elements = elements
                        break
                except Exception as e:
                    continue
            
            if not item_elements:
                # Try finding any elements with price-like text
                price_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
                if price_elements:
                    logger.info(f"Found {len(price_elements)} elements with price indicators")
                    # Get parent elements that might be item containers
                    item_elements = [elem.find_element(By.XPATH, "..") for elem in price_elements[:10]]
            
            # Extract data from found elements
            for element in item_elements[:20]:  # Limit to first 20 items
                try:
                    item_data = self.extract_item_from_element(element, auction_url)
                    if item_data:
                        items.append(item_data)
                except Exception as e:
                    logger.debug(f"Error extracting item: {e}")
                    continue
            
            logger.info(f"Extracted {len(items)} items from {auction_url}")
            
        except Exception as e:
            logger.error(f"Error scraping auction page {auction_url}: {e}")
        
        return items
    
    def extract_item_from_element(self, element, auction_url: str) -> Optional[Dict[str, Any]]:
        """Extract item data from a web element"""
        try:
            # Try to find title/description
            title = None
            title_selectors = ["h1", "h2", "h3", "h4", "h5", ".title", ".name", "strong", "b"]
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title and len(title) > 3:
                        break
                except:
                    continue
            
            if not title:
                # Fallback to element text
                text = element.text.strip()
                if text and len(text) > 3:
                    # Take first line as title
                    title = text.split('\n')[0][:100]
            
            if not title or len(title) < 3:
                return None
            
            # Try to find price
            current_bid = 0.0
            price_text = element.text
            
            # Look for dollar amounts
            import re
            price_matches = re.findall(r'\$[\d,]+\.?\d*', price_text)
            if price_matches:
                # Take the first reasonable price
                for match in price_matches:
                    try:
                        price = float(match.replace('$', '').replace(',', ''))
                        if 1 <= price <= 10000:  # Reasonable price range
                            current_bid = price
                            break
                    except:
                        continue
            
            # Generate auction ID from URL and title
            auction_id = f"{auction_url.split('/')[-1]}_{hash(title) % 10000}"
            
            # Try to find more specific link if available
            item_url = auction_url
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, "a")
                href = link_elem.get_attribute('href')
                if href:
                    item_url = urljoin(self.base_url, href)
            except:
                pass
            
            # Default auction end time (in case we can't find it)
            auction_end = datetime.now() + timedelta(days=7)
            
            item_data = {
                'auction_id': auction_id,
                'title': title,
                'current_bid': current_bid,
                'auction_url': item_url,
                'auction_end': auction_end,
                'description': price_text[:200] if price_text else ''
            }
            
            logger.debug(f"Extracted item: {title} - ${current_bid}")
            return item_data
            
        except Exception as e:
            logger.debug(f"Error extracting item data: {e}")
            return None
    
    def run(self, max_auction_groups: int = 3) -> Dict[str, Any]:
        """Run the complete scraping process"""
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
            logger.info("Starting auction scraping...")
            
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
                
                items = self.scrape_auction_page(auction_url)
                all_items.extend(items)
                
                # Rate limiting between pages
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
                        
                        logger.info(f"Flagged valuable item: {item['title']} - ${item['current_bid']}")
                    
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