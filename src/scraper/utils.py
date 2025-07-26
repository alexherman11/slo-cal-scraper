import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class ScraperUtils:
    """Utility functions for web scraping"""
    
    @staticmethod
    def clean_price(price_str: str) -> Optional[float]:
        """
        Extract numeric price from string
        
        Args:
            price_str: Price string (e.g., "$350.00", "USD 350")
        
        Returns:
            Float price or None if cannot parse
        """
        if not price_str:
            return None
        
        # Remove currency symbols and common price indicators
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        
        # Handle different decimal separators
        cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse price: {price_str}")
            return None
    
    @staticmethod
    def parse_auction_end_time(time_str: str) -> Optional[datetime]:
        """
        Parse various auction end time formats
        
        Args:
            time_str: Time string to parse
        
        Returns:
            datetime object or None if cannot parse
        """
        if not time_str:
            return None
        
        # Common date formats on auction sites
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M",
            "%B %d, %Y at %I:%M %p",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {time_str}")
        return None
    
    @staticmethod
    def extract_item_id(url: str) -> Optional[str]:
        """
        Extract item/auction ID from URL
        
        Args:
            url: Auction item URL
        
        Returns:
            Item ID or None
        """
        # Common patterns for auction IDs
        patterns = [
            r'/item/(\d+)',
            r'/auction/(\d+)',
            r'[?&]id=(\d+)',
            r'/lot/(\d+)',
            r'-(\d+)\.html?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, use the last part of the URL
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        if parts and parts[-1]:
            return parts[-1]
        
        return None
    
    @staticmethod
    def is_valid_url(url: str, base_url: str) -> bool:
        """
        Check if URL is valid and belongs to the target domain
        
        Args:
            url: URL to check
            base_url: Base URL of the target site
        
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(base_url)
            
            # Check if it's a relative URL or same domain
            return (not parsed.netloc or 
                    parsed.netloc == base_parsed.netloc)
        except Exception:
            return False
    
    @staticmethod
    def make_absolute_url(url: str, base_url: str) -> str:
        """
        Convert relative URL to absolute URL
        
        Args:
            url: URL (relative or absolute)
            base_url: Base URL for relative URLs
        
        Returns:
            Absolute URL
        """
        return urljoin(base_url, url)
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Get a random user agent string"""
        ua = UserAgent()
        return ua.random
    
    @staticmethod
    def extract_condition(text: str) -> Optional[str]:
        """
        Extract item condition from text
        
        Args:
            text: Text containing condition info
        
        Returns:
            Condition string or None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Common condition keywords
        conditions = {
            'new': ['new', 'brand new', 'sealed', 'unopened', 'mint'],
            'like new': ['like new', 'excellent', 'near mint'],
            'good': ['good condition', 'very good', 'gently used'],
            'fair': ['fair', 'used', 'some wear'],
            'poor': ['poor', 'damaged', 'for parts', 'not working', 'broken']
        }
        
        for condition, keywords in conditions.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return condition
        
        return 'unknown'
    
    @staticmethod
    def is_valuable_item(title: str, description: str = "") -> Dict[str, Any]:
        """
        Check if item might be valuable based on keywords
        
        Args:
            title: Item title
            description: Item description
        
        Returns:
            Dictionary with valuable indicators
        """
        combined_text = f"{title} {description}".lower()
        
        # Valuable keywords
        valuable_keywords = {
            'precious_metals': ['gold', 'silver', 'platinum', 'sterling'],
            'gems': ['diamond', 'emerald', 'ruby', 'sapphire', 'pearl'],
            'collectibles': ['vintage', 'antique', 'rare', 'limited edition', 'signed'],
            'brands': ['rolex', 'cartier', 'tiffany', 'hermes', 'louis vuitton'],
            'materials': ['leather', 'silk', 'cashmere', 'mahogany', 'crystal'],
            'coins': ['coin', 'numismatic', 'proof', 'uncirculated'],
        }
        
        # Red flag keywords
        avoid_keywords = ['replica', 'style', 'inspired', 'fake', 'faux', 
                         'damaged', 'broken', 'parts only', 'not working']
        
        results = {
            'categories': [],
            'keywords_found': [],
            'red_flags': [],
            'value_score': 0
        }
        
        # Check for valuable keywords
        for category, keywords in valuable_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    results['categories'].append(category)
                    results['keywords_found'].append(keyword)
                    results['value_score'] += 1
        
        # Check for red flags
        for keyword in avoid_keywords:
            if keyword in combined_text:
                results['red_flags'].append(keyword)
                results['value_score'] -= 2
        
        # Remove duplicates
        results['categories'] = list(set(results['categories']))
        results['keywords_found'] = list(set(results['keywords_found']))
        
        return results
    
    @staticmethod
    def calculate_fees(sale_price: float, shipping_cost: float = 0) -> Dict[str, float]:
        """
        Calculate eBay fees for profit estimation
        
        Args:
            sale_price: Expected sale price
            shipping_cost: Shipping cost
        
        Returns:
            Dictionary with fee breakdown
        """
        # eBay fees (as of the documentation)
        ebay_final_value_fee = sale_price * 0.136  # 13.6%
        payment_processing_fee = (sale_price + shipping_cost) * 0.0235 + 0.30
        
        total_fees = ebay_final_value_fee + payment_processing_fee
        
        return {
            'ebay_fee': round(ebay_final_value_fee, 2),
            'payment_fee': round(payment_processing_fee, 2),
            'total_fees': round(total_fees, 2),
            'net_after_fees': round(sale_price - total_fees, 2)
        }