#!/usr/bin/env python3
"""
Demo scraper to show undervalued items
"""

import logging
from datetime import datetime, timedelta
from src.database.db_manager import DatabaseManager
from src.scraper.utils import ScraperUtils

def create_demo_data():
    """Create some demo auction items to show functionality"""
    db_manager = DatabaseManager()
    utils = ScraperUtils()
    
    # Create demo items that would be flagged as valuable
    demo_items = [
        {
            'auction_id': 'demo_001',
            'title': '14K Gold Diamond Ring Estate Piece',
            'current_bid': 125.0,
            'auction_url': 'https://slocalestateauctions.com/item/demo_001',
            'auction_end': datetime.now() + timedelta(days=2),
            'description': 'Beautiful 14K gold ring with diamond. Estate sale find.'
        },
        {
            'auction_id': 'demo_002', 
            'title': 'Vintage Sterling Silver Turquoise Bracelet',
            'current_bid': 45.0,
            'auction_url': 'https://slocalestateauctions.com/item/demo_002', 
            'auction_end': datetime.now() + timedelta(days=1),
            'description': 'Native American sterling silver and turquoise bracelet'
        },
        {
            'auction_id': 'demo_003',
            'title': 'Griswold Cast Iron Skillet #8',
            'current_bid': 35.0,
            'auction_url': 'https://slocalestateauctions.com/item/demo_003',
            'auction_end': datetime.now() + timedelta(hours=8),
            'description': 'Vintage Griswold cast iron skillet, excellent condition'
        },
        {
            'auction_id': 'demo_004',
            'title': 'Star Wars Original Trilogy VHS Set 1995',
            'current_bid': 25.0,
            'auction_url': 'https://slocalestateauctions.com/item/demo_004',
            'auction_end': datetime.now() + timedelta(days=3),
            'description': 'Original trilogy VHS set from 1995, collectible'
        },
        {
            'auction_id': 'demo_005',
            'title': 'Mercury Dime Roll 1940s Silver',
            'current_bid': 85.0,
            'auction_url': 'https://slocalestateauctions.com/item/demo_005', 
            'auction_end': datetime.now() + timedelta(days=1),
            'description': 'Roll of Mercury dimes from the 1940s, 90% silver'
        }
    ]
    
    print("Creating demo auction items...")
    for item in demo_items:
        item_id = db_manager.save_item(item)
        
        # Analyze the item for value
        value_analysis = utils.is_valuable_item(item['title'], item.get('description', ''))
        
        if value_analysis['value_score'] > 0:
            # Create a mock profit analysis
            estimated_value = estimate_item_value(item['title'], item['current_bid'])
            
            if estimated_value > item['current_bid']:
                profit_margin = ((estimated_value - item['current_bid']) / estimated_value) * 100
                
                # Save profit analysis
                analysis_data = {
                    'item_id': item_id,
                    'estimated_value': estimated_value,
                    'current_bid': item['current_bid'],
                    'potential_profit': estimated_value - item['current_bid'],
                    'profit_margin': profit_margin,
                    'confidence_score': min(0.85, value_analysis['value_score'] / 5),
                    'recommendation': 'BID' if profit_margin > 50 else 'WATCH'
                }
                
                db_manager.save_profit_analysis(analysis_data)
                print(f"[+] {item['title'][:40]}... - ${item['current_bid']:.2f} -> ${estimated_value:.2f} ({profit_margin:.1f}% profit)")

def estimate_item_value(title, current_bid):
    """Mock value estimation based on keywords"""
    title_lower = title.lower()
    
    # Simple estimation logic for demo
    if 'gold' in title_lower and 'diamond' in title_lower:
        return current_bid * 3.5  # Gold jewelry typically has good resale
    elif 'sterling silver' in title_lower:
        return current_bid * 2.8
    elif 'griswold' in title_lower:
        return current_bid * 4.2  # Vintage cast iron is very collectible
    elif 'star wars' in title_lower and 'original' in title_lower:
        return current_bid * 3.0
    elif 'mercury dime' in title_lower and 'silver' in title_lower:
        return current_bid * 2.5  # Silver coins have intrinsic value
    else:
        return current_bid * 1.8

def show_results():
    """Display the results"""
    db_manager = DatabaseManager()
    
    print("\n" + "="*80)
    print("SLOCAL ESTATE AUCTION SCRAPER - DEMO RESULTS")
    print("="*80)
    
    # Get all items
    active_items = db_manager.get_active_items()
    print(f"\nTotal active items in database: {len(active_items)}")
    
    # Get undervalued items
    undervalued = db_manager.get_undervalued_items(min_profit_margin=50.0)
    
    if undervalued:
        print(f"\n>> UNDERVALUED ITEMS (>50% profit potential):")
        print("-" * 80)
        for i, result in enumerate(undervalued, 1):
            item = result['item']
            analysis = result['analysis']
            
            # Access the attributes safely within a session context
            with db_manager.get_session() as session:
                merged_item = session.merge(item)
                merged_analysis = session.merge(analysis)
                
                print(f"\n{i}. {merged_item.title}")
                print(f"   Current Bid: ${merged_item.current_bid:.2f}")
                print(f"   Estimated Value: ${merged_analysis.estimated_value:.2f}")
                print(f"   Potential Profit: ${merged_analysis.potential_profit:.2f}")
                print(f"   Profit Margin: {merged_analysis.profit_margin:.1f}%")
                print(f"   Confidence: {merged_analysis.confidence_score:.1%}")
                print(f"   Recommendation: {merged_analysis.recommendation}")
                print(f"   URL: {merged_item.auction_url}")
                
                # Calculate time remaining
                time_remaining = merged_item.auction_end - datetime.now()
                if time_remaining.total_seconds() > 0:
                    if time_remaining.days > 0:
                        print(f"   Time Remaining: {time_remaining.days} days")
                    else:
                        hours = int(time_remaining.total_seconds() / 3600)
                        print(f"   Time Remaining: {hours} hours")
                else:
                    print(f"   [!] Auction has ended")
    else:
        print("\nNo undervalued items found.")
    
    print("\n" + "="*80)
    print("STRATEGY TIPS:")
    print("- Gold jewelry often sells for 2-4x auction prices")
    print("- Vintage Griswold cast iron is highly collectible")
    print("- Silver coins have intrinsic metal value plus collectible premium")
    print("- Star Wars collectibles from the 1990s are increasing in value")
    print("- Sterling silver jewelry typically has 150-300% markup potential")
    print("="*80)

def main():
    """Main demo function"""
    print("SLOCAL Estate Auction Scraper Demo")
    print("Creating demo data to show undervalued item detection...")
    
    create_demo_data()
    show_results()
    
    print(f"\n>> To run the real scraper: python main.py scrape")
    print(f">> To view database: python main.py view")

if __name__ == "__main__":
    main()