import pytest
from datetime import datetime, timedelta
from src.scraper.utils import ScraperUtils
from src.scraper.rate_limiter import PoliteRateLimiter
from src.database.db_manager import DatabaseManager

class TestScraperUtils:
    """Test scraper utility functions"""
    
    def test_clean_price(self):
        """Test price extraction from various formats"""
        utils = ScraperUtils()
        
        assert utils.clean_price("$350.00") == 350.00
        assert utils.clean_price("USD 1,234.56") == 1234.56
        assert utils.clean_price("€99.99") == 99.99
        assert utils.clean_price("Price: $50") == 50.0
        assert utils.clean_price("") is None
        assert utils.clean_price("No price") is None
    
    def test_extract_condition(self):
        """Test condition extraction"""
        utils = ScraperUtils()
        
        assert utils.extract_condition("Brand new in box") == "new"
        assert utils.extract_condition("Excellent condition") == "like new"
        assert utils.extract_condition("Some wear and tear") == "fair"
        assert utils.extract_condition("For parts only") == "poor"
        assert utils.extract_condition("Random text") == "unknown"
    
    def test_is_valuable_item(self):
        """Test valuable item detection"""
        utils = ScraperUtils()
        
        # Test valuable items
        result = utils.is_valuable_item("14K Gold Diamond Ring")
        assert result['value_score'] > 0
        assert 'precious_metals' in result['categories']
        assert 'gold' in result['keywords_found']
        
        # Test items with red flags
        result = utils.is_valuable_item("Gold Plated Replica Watch")
        assert result['value_score'] < 0
        assert 'replica' in result['red_flags']
        
        # Test collectibles
        result = utils.is_valuable_item("Vintage Star Wars First Edition")
        assert result['value_score'] > 0
        assert 'collectibles' in result['categories']
    
    def test_calculate_fees(self):
        """Test eBay fee calculation"""
        utils = ScraperUtils()
        
        fees = utils.calculate_fees(100.0, 10.0)
        assert fees['ebay_fee'] == 13.60  # 13.6% of $100
        assert fees['payment_fee'] == 2.89  # 2.35% of $110 + $0.30
        assert fees['total_fees'] == 16.49
        assert fees['net_after_fees'] == 83.51

class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter setup"""
        limiter = PoliteRateLimiter(min_delay=1, max_delay=2, requests_per_minute=30)
        
        status = limiter.get_status()
        assert status['requests_in_last_minute'] == 0
        assert status['requests_remaining'] == 30
        assert status['can_proceed'] is True
    
    def test_jitter(self):
        """Test jitter functionality"""
        limiter = PoliteRateLimiter()
        
        base_value = 10.0
        for _ in range(10):
            jittered = limiter.add_jitter(base_value, 0.2)
            assert 8.0 <= jittered <= 12.0  # ±20% of 10

class TestDatabaseManager:
    """Test database operations"""
    
    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        return DatabaseManager()
    
    def test_create_scrape_session(self, db_manager):
        """Test creating a scrape session"""
        session_id = db_manager.create_scrape_session()
        assert isinstance(session_id, int)
        assert session_id > 0
    
    def test_save_item(self, db_manager):
        """Test saving an auction item"""
        item_data = {
            'auction_id': 'test_123',
            'title': 'Test Vintage Item',
            'current_bid': 50.0,
            'auction_url': 'http://example.com/item/123',
            'auction_end': datetime.now() + timedelta(days=3)
        }
        
        item_id = db_manager.save_item(item_data)
        assert isinstance(item_id, int)
        
        # Test retrieving the item
        item = db_manager.get_item_by_id(item_id)
        assert item is not None
        assert item.title == 'Test Vintage Item'
        assert item.current_bid == 50.0
    
    def test_watchlist(self, db_manager):
        """Test watchlist functionality"""
        db_manager.add_to_watchlist('test_keyword', min_profit_threshold=40.0)
        
        watchlist = db_manager.get_watchlist()
        assert any(w.keyword == 'test_keyword' for w in watchlist)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])