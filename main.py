#!/usr/bin/env python3
"""
Estate Auction Scraper - Main Entry Point
Phase 1: Core scraping functionality
"""

import sys
import logging
import argparse
from datetime import datetime
from colorlog import ColoredFormatter

from src.scraper.enhanced_auction_scraper import EnhancedAuctionScraper
from src.database import DatabaseManager
from src.config import LOGGING_CONFIG, PROFIT_CONFIG, WATCH_KEYWORDS

def setup_logging(log_level: str = None):
    """Set up colored console logging"""
    if log_level is None:
        log_level = LOGGING_CONFIG['level']
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    
    colored_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    console_handler.setFormatter(colored_formatter)
    
    # File handler
    file_handler = logging.FileHandler(LOGGING_CONFIG['file'])
    file_formatter = logging.Formatter(LOGGING_CONFIG['format'])
    file_handler.setFormatter(file_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

def display_results(results: dict):
    """Display scraping results in a formatted way"""
    print("\n" + "="*60)
    print("SCRAPING RESULTS")
    print("="*60)
    
    print(f"\nTotal items found: {results['items_found']}")
    print(f"Items flagged as valuable: {results['items_flagged']}")
    
    if results['valuable_items']:
        print("\n" + "-"*40)
        print("VALUABLE ITEMS FOUND:")
        print("-"*40)
        for i, item in enumerate(results['valuable_items'], 1):
            print(f"\n{i}. {item['title']}")
            print(f"   Current Bid: ${item['current_bid']:.2f}")
            print(f"   Keywords: {', '.join(item['keywords'])}")
            if item.get('url'):
                print(f"   URL: {item['url']}")
    
    if results['watchlist_matches']:
        print("\n" + "-"*40)
        print("WATCHLIST MATCHES:")
        print("-"*40)
        for i, item in enumerate(results['watchlist_matches'], 1):
            print(f"\n{i}. {item['title']}")
            print(f"   Current Bid: ${item['current_bid']:.2f}")
            if item.get('url'):
                print(f"   URL: {item['url']}")
    
    if results['errors']:
        print("\n" + "-"*40)
        print("ERRORS ENCOUNTERED:")
        print("-"*40)
        for error in results['errors']:
            print(f"- {error}")
    
    print("\n" + "="*60 + "\n")

def view_database_summary():
    """Display summary of items in database"""
    db_manager = DatabaseManager()
    
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)
    
    # Get active items
    all_active = db_manager.get_active_items()
    print(f"\nActive items in database: {len(all_active)}")
    
    if all_active:
        print("\nMost recent items:")
        print("-"*40)
        for item in all_active[:5]:
            print(f"- {item['title'][:60]}... (${item['current_bid']:.2f})")
    
    # Get undervalued items
    undervalued = db_manager.get_undervalued_items(
        min_profit_margin=PROFIT_CONFIG['min_percentage']
    )
    
    if undervalued:
        print(f"\nUndervalued items (>{PROFIT_CONFIG['min_percentage']}% profit potential):")
        print("-"*40)
        for result in undervalued[:5]:
            item = result['item']
            analysis = result['analysis']
            # These are still SQLAlchemy objects, need to handle differently
            with db_manager.get_session() as session:
                # Reattach objects to session
                merged_item = session.merge(item)
                merged_analysis = session.merge(analysis)
                print(f"- {merged_item.title[:50]}...")
                print(f"  Current: ${merged_item.current_bid:.2f}, "
                      f"Est. Value: ${merged_analysis.estimated_value:.2f}, "
                      f"Margin: {merged_analysis.profit_margin:.1f}%")
    
    print("\n" + "="*60 + "\n")

def add_to_watchlist(keyword: str, min_profit: float = None):
    """Add a keyword to the watchlist"""
    db_manager = DatabaseManager()
    
    if min_profit is None:
        min_profit = PROFIT_CONFIG['min_percentage']
    
    db_manager.add_to_watchlist(
        keyword=keyword,
        min_profit_threshold=min_profit
    )
    
    print(f"Added '{keyword}' to watchlist (min profit: {min_profit}%)")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Estate Auction Scraper - Find undervalued items"
    )
    
    # Action arguments
    parser.add_argument(
        'action',
        choices=['scrape', 'view', 'watch', 'test', 'monitor', 'check-urgent', 'test-notifications'],
        help='Action to perform'
    )
    
    # Optional arguments
    parser.add_argument(
        '--pages',
        type=int,
        help='Maximum number of pages to scrape'
    )
    
    parser.add_argument(
        '--details',
        action='store_true',
        help='Scrape detailed item pages (slower but more accurate)'
    )
    
    parser.add_argument(
        '--keyword',
        type=str,
        help='Keyword for watchlist'
    )
    
    parser.add_argument(
        '--min-profit',
        type=float,
        help='Minimum profit percentage for watchlist'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode'
    )
    
    parser.add_argument(
        '--no-headless',
        dest='headless',
        action='store_false',
        help='Run browser with GUI'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        if args.action == 'scrape':
            # Run the scraper
            logger.info("Starting auction scraper...")
            scraper = EnhancedAuctionScraper(headless=args.headless)
            results = scraper.run(max_auction_groups=args.pages or 3)
            display_results(results)
            
        elif args.action == 'view':
            # View database summary
            view_database_summary()
            
        elif args.action == 'watch':
            # Add to watchlist
            if not args.keyword:
                print("Error: --keyword required for watch action")
                sys.exit(1)
            add_to_watchlist(args.keyword, args.min_profit)
            
        elif args.action == 'test':
            # Test mode - quick functionality check
            logger.info("Running in test mode...")
            print("\nConfiguration loaded successfully!")
            print(f"Watch keywords: {', '.join(WATCH_KEYWORDS[:5])}...")
            print(f"Min profit threshold: {PROFIT_CONFIG['min_percentage']}%")
            
            # Test database connection
            db_manager = DatabaseManager()
            print("\nDatabase connection: OK")
            
            # Test scraper initialization
            scraper = EnhancedAuctionScraper(headless=True)
            print("Scraper initialization: OK")
            
            print("\nAll systems ready! Run 'python main.py scrape' to start scraping.")
            
        elif args.action == 'monitor':
            # Start continuous monitoring
            from src.scheduler.monitor import run_monitor_service
            logger.info("Starting continuous monitoring service...")
            run_monitor_service()
            
        elif args.action == 'check-urgent':
            # Manual urgent item check
            from src.scheduler.monitor import AuctionMonitor
            monitor = AuctionMonitor()
            monitor.run_manual_check()
            
        elif args.action == 'test-notifications':
            # Test notification system
            from src.notifications.notifier import AuctionNotifier
            notifier = AuctionNotifier()
            notifier.test_notifications()
    
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()