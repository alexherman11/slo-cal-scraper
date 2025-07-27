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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from urllib.parse import urljoin

from src.config.settings import AUCTION_CONFIG, SCRAPER_CONFIG, WATCH_KEYWORDS, AVOID_KEYWORDS
from src.scraper.rate_limiter import PoliteRateLimiter
from src.scraper.utils import ScraperUtils
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class EnhancedAuctionScraper:
    """Enhanced scraper that aggressively extracts ALL potential items from auction pages"""
    
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
            time.sleep(3)
            
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
            
            logger.info(f"Total auction groups found: {len(auction_links)}")
            return auction_links
            
        except Exception as e:
            logger.error(f"Error finding auction groups: {e}")
            return []
    
    def scrape_auction_page(self, auction_url: str) -> List[Dict[str, Any]]:
        """Enhanced scraping of auction page to find ALL potential items"""
        items = []
        
        try:
            logger.info(f"Scraping auction page: {auction_url}")
            self.driver.get(auction_url)
            time.sleep(5)  # Give more time for dynamic content
            
            # Strategy 1: Look for structured auction items
            items.extend(self.extract_structured_items())
            
            # Strategy 2: Look for table-based items
            items.extend(self.extract_table_items())
            
            # Strategy 3: Look for grid/card-based items  
            items.extend(self.extract_grid_items())
            
            # Strategy 4: Extract from any element containing price indicators
            items.extend(self.extract_price_based_items())
            
            # Strategy 5: Extract from text content (backup method)
            items.extend(self.extract_text_based_items())
            
            # Remove duplicates based on title
            unique_items = []
            seen_titles = set()
            for item in items:
                title_key = item['title'].lower().strip()
                if title_key not in seen_titles and len(title_key) > 3:
                    seen_titles.add(title_key)
                    unique_items.append(item)
            
            # Add auction URL to all items
            for item in unique_items:
                item['auction_url'] = auction_url
            
            logger.info(f"Extracted {len(unique_items)} unique items from {auction_url}")
            
        except Exception as e:
            logger.error(f"Error scraping auction page {auction_url}: {e}")
        
        return unique_items
    
    def extract_structured_items(self) -> List[Dict[str, Any]]:
        """Extract from structured auction item containers"""
        items = []
        
        selectors = [
            ".lot-item", ".auction-item", ".item", ".product-item",
            ".auction-lot", ".listing-item", "[class*='item']",
            "[class*='lot']", "[class*='product']", "[id*='item']",
            "[id*='lot']", ".card", "article"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 1:  # Must be multiple items
                    logger.debug(f"Extracting from {len(elements)} elements using {selector}")
                    for element in elements:
                        item = self.extract_item_from_element(element)
                        if item:
                            items.append(item)
                    break  # Use first successful selector
            except Exception as e:
                continue
        
        return items
    
    def extract_table_items(self) -> List[Dict[str, Any]]:
        """Extract items from table rows"""
        items = []
        
        try:
            tables = self.driver.find_elements(By.CSS_SELECTOR, "table")
            for table in tables:
                rows = table.find_elements(By.CSS_SELECTOR, "tr")
                if len(rows) > 2:  # Skip header-only tables
                    logger.debug(f"Extracting from table with {len(rows)} rows")
                    for row in rows[1:]:  # Skip header row
                        item = self.extract_item_from_element(row)
                        if item:
                            items.append(item)
        except Exception as e:
            logger.debug(f"Error extracting table items: {e}")
        
        return items
    
    def extract_grid_items(self) -> List[Dict[str, Any]]:
        """Extract items from Bootstrap grid or similar layouts"""
        items = []
        
        grid_selectors = [
            ".row .col", ".row > div", ".grid-item",
            ".col-md-6", ".col-lg-4", ".col-sm-12"
        ]
        
        for selector in grid_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) > 2:  # Must have multiple items
                    logger.debug(f"Extracting from {len(elements)} grid items using {selector}")
                    for element in elements:
                        item = self.extract_item_from_element(element)
                        if item and len(item['title']) > 5:  # Meaningful titles only
                            items.append(item)
                    if items:  # Stop at first successful grid
                        break
            except Exception as e:
                continue
        
        return items
    
    def extract_price_based_items(self) -> List[Dict[str, Any]]:
        """Find items by looking for price indicators"""
        items = []
        
        try:
            # Find all elements containing price-like text
            price_patterns = [
                "//*[contains(text(), '$')]",
                "//*[contains(text(), 'USD')]", 
                "//*[contains(text(), 'bid')]",
                "//*[contains(text(), 'price')]"
            ]
            
            price_elements = []
            for pattern in price_patterns:
                elements = self.driver.find_elements(By.XPATH, pattern)
                price_elements.extend(elements)
            
            # Get parent containers that might be item containers
            for elem in price_elements[:20]:  # Limit to avoid performance issues
                try:
                    # Try parent and grandparent elements
                    containers = [elem]
                    try:
                        containers.append(elem.find_element(By.XPATH, ".."))
                        containers.append(elem.find_element(By.XPATH, "../.."))
                    except:
                        pass
                    
                    for container in containers:
                        item = self.extract_item_from_element(container)
                        if item and len(item['title']) > 3:
                            items.append(item)
                            break
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error in price-based extraction: {e}")
        
        return items
    
    def extract_text_based_items(self) -> List[Dict[str, Any]]:
        """Extract items from page text content as fallback"""
        items = []
        
        try:
            # Get all text content and look for patterns
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for lines that might be item descriptions
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                
                # ONLY accept lines that match the "Lot #[number] - [item name]" format
                if not self.is_valid_auction_item(line):
                    continue
                
                # Try to extract price from line
                price_match = re.search(r'\$[\d,]+\.?\d*', line)
                price = 0.0
                if price_match:
                    try:
                        price = float(price_match.group().replace('$', '').replace(',', ''))
                    except:
                        pass
                
                if len(line) < 200:  # Reasonable title length
                    item = {
                        'title': line,
                        'current_bid': price,
                        'description': line,
                        'auction_id': f"text_{hash(line) % 10000}",
                        'auction_end': datetime.now() + timedelta(days=7)
                    }
                    items.append(item)
        except Exception as e:
            logger.debug(f"Error in text-based extraction: {e}")
        
        return items[:10]  # Limit text-based items
    
    def is_valid_auction_item(self, title: str) -> bool:
        """Check if the title matches the expected auction item format: 'Lot #[number] - [item name]'"""
        if not title or len(title.strip()) < 5:
            return False
        
        title = title.strip()
        
        # Check for the exact pattern: "Lot #" followed by number(s), then " - " and item name
        lot_pattern = re.compile(r'^Lot\s+#\d+\s*-\s*.+', re.IGNORECASE)
        
        if lot_pattern.match(title):
            logger.debug(f"Valid auction item found: {title[:50]}")
            return True
        
        logger.debug(f"Invalid item filtered out: {title[:50]}")
        return False
    
    def extract_item_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Enhanced item extraction from a web element"""
        try:
            # Get all text from element
            element_text = element.text.strip()
            if len(element_text) < 3:
                return None
            
            # Try to find title from various sources
            title = None
            title_selectors = [
                "h1", "h2", "h3", "h4", "h5", "h6",
                ".title", ".name", ".item-title", ".product-title",
                "strong", "b", "a", "span"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title and len(title) > 3:
                        break
                except:
                    continue
            
            # Fallback to element text
            if not title:
                lines = element_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3 and len(line) < 200:
                        title = line
                        break
            
            if not title or len(title) < 3:
                return None
            
            # CRITICAL FILTER: Only accept items that match "Lot #[number] - [item name]" format
            if not self.is_valid_auction_item(title):
                return None
            
            # Extract price using multiple methods
            current_bid = 0.0
            
            # Method 1: Look for price in text
            price_matches = re.findall(r'\$[\d,]+\.?\d*', element_text)
            if price_matches:
                for match in price_matches:
                    try:
                        price = float(match.replace('$', '').replace(',', ''))
                        if 0.01 <= price <= 50000:  # Reasonable price range
                            current_bid = price
                            break
                    except:
                        continue
            
            # Method 2: Look for price in attributes
            if current_bid == 0:
                try:
                    price_attrs = ['data-price', 'data-bid', 'data-amount']
                    for attr in price_attrs:
                        price_text = element.get_attribute(attr)
                        if price_text:
                            current_bid = float(re.sub(r'[^\d.]', '', price_text))
                            break
                except:
                    pass
            
            # Generate unique auction ID
            auction_id = f"enhanced_{hash(title + element_text) % 100000}"
            
            # Try to find item-specific URL
            item_url = ""
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, "a")
                href = link_elem.get_attribute('href')
                if href and href.startswith('http'):
                    item_url = href
            except:
                pass
            
            # Default auction end time
            auction_end = datetime.now() + timedelta(days=7)
            
            item_data = {
                'auction_id': auction_id,
                'title': title[:200],  # Limit title length
                'current_bid': current_bid,
                'auction_url': item_url,
                'auction_end': auction_end,
                'description': element_text[:500] if element_text else ''
            }
            
            logger.debug(f"Extracted item: {title[:50]} - ${current_bid}")
            return item_data
            
        except Exception as e:
            logger.debug(f"Error extracting item data: {e}")
            return None
    
    def run(self, max_auction_groups: int = 3) -> Dict[str, Any]:
        """Run the enhanced scraping process"""
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
            logger.info("Starting enhanced auction scraping...")
            
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
                logger.info(f"Found {len(items)} items in auction group {i+1}")
                
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