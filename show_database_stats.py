#!/usr/bin/env python3
"""
Show detailed database statistics
"""

from src.database.db_manager import DatabaseManager

def show_database_stats():
    """Show detailed statistics of scraped items"""
    db_manager = DatabaseManager()
    
    print("="*80)
    print("DETAILED DATABASE STATISTICS")
    print("="*80)
    
    # Get all items
    all_items = db_manager.get_active_items()
    print(f"Total active items: {len(all_items)}")
    
    if not all_items:
        print("No items in database.")
        return
    
    # Show price distribution
    prices = [item['current_bid'] for item in all_items if item['current_bid'] > 0]
    if prices:
        print(f"\nPrice Statistics:")
        print(f"- Items with prices: {len(prices)}")
        print(f"- Highest price: ${max(prices):.2f}")
        print(f"- Lowest price: ${min(prices):.2f}")
        print(f"- Average price: ${sum(prices)/len(prices):.2f}")
    
    # Show items by price ranges
    price_ranges = {
        "$0": len([p for p in prices if p == 0]),
        "$1-$50": len([p for p in prices if 1 <= p <= 50]),
        "$51-$100": len([p for p in prices if 51 <= p <= 100]), 
        "$101-$500": len([p for p in prices if 101 <= p <= 500]),
        "$500+": len([p for p in prices if p > 500])
    }
    
    print(f"\nPrice Distribution:")
    for range_name, count in price_ranges.items():
        print(f"- {range_name}: {count} items")
    
    # Show highest value items
    high_value_items = [item for item in all_items if item['current_bid'] >= 100]
    high_value_items.sort(key=lambda x: x['current_bid'], reverse=True)
    
    print(f"\nTop 10 Highest Value Items:")
    print("-" * 60)
    for i, item in enumerate(high_value_items[:10], 1):
        title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
        print(f"{i:2d}. ${item['current_bid']:>8.2f} - {title}")
    
    # Show some sample coin items
    coin_items = [item for item in all_items if 
                  'coin' in item['title'].lower() or 
                  'silver' in item['title'].lower() or
                  'gold' in item['title'].lower()]
    
    print(f"\nCoin/Precious Metal Items Found: {len(coin_items)}")
    print("-" * 60)
    for i, item in enumerate(coin_items[:5], 1):
        title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
        print(f"{i}. ${item['current_bid']:>7.2f} - {title}")
    
    print("="*80)

if __name__ == "__main__":
    show_database_stats()