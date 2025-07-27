#!/usr/bin/env python3
"""
Test the fixed scraper on the real website
"""

import logging
from src.scraper.fixed_auction_scraper import FixedAuctionScraper

def setup_logging():
    """Set up logging to see what's happening"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scraper_test.log')
        ]
    )

def test_fixed_scraper():
    """Test the updated scraper"""
    print("Testing Fixed Auction Scraper")
    print("=" * 50)
    
    setup_logging()
    
    # Run with visible browser first to see what happens
    scraper = FixedAuctionScraper(headless=False)
    
    try:
        print("Running scraper (browser will be visible)...")
        results = scraper.run(max_auction_groups=2)  # Test with 2 auction groups
        
        print("\nSCRAPING RESULTS:")
        print("-" * 30)
        print(f"Items found: {results['items_found']}")
        print(f"Items flagged as valuable: {results['items_flagged']}")
        
        if results['valuable_items']:
            print("\nVALUABLE ITEMS:")
            for i, item in enumerate(results['valuable_items'], 1):
                print(f"{i}. {item['title']}")
                print(f"   Current Bid: ${item['current_bid']:.2f}")
                print(f"   Keywords: {', '.join(item['keywords'])}")
                print(f"   URL: {item['url']}")
                print()
        
        if results['errors']:
            print("ERRORS:")
            for error in results['errors']:
                print(f"- {error}")
        
        print("\nTest completed! Check scraper_test.log for detailed logs.")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_scraper()