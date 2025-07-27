#!/usr/bin/env python3
"""
Test script to check individual auction page structure
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

def test_auction_page():
    """Check what's on a specific auction page"""
    
    # Setup Chrome driver
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options)
    
    try:
        # Test the coins auction page
        auction_url = "https://slocalestateauctions.com/auction/coins_silver_gold_cccx"
        print(f"Navigating to {auction_url}...")
        driver.get(auction_url)
        time.sleep(5)
        
        print(f"Page title: {driver.title}")
        
        # Look for auction items on this page
        selectors_to_check = [
            ".auction-item",
            ".item", 
            ".product",
            ".lot",
            "[class*='item']",
            "[class*='lot']",
            "[class*='product']",
            "div.card",
            "div.row .col",
            "table tr",
            ".auction-lot",
            ".lot-item"
        ]
        
        print("\nChecking for auction item elements...")
        for selector in selectors_to_check:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"✓ Found {len(elements)} elements with selector: {selector}")
                if len(elements) < 20:  # Only show details for small lists
                    for i, elem in enumerate(elements[:5]):
                        try:
                            text = elem.text[:100] if elem.text else "[No text]"
                            classes = elem.get_attribute('class') or "[No classes]"
                            print(f"  Element {i+1}: {text[:50]}... (classes: {classes})")
                        except:
                            print(f"  Element {i+1}: [Error getting info]")
            else:
                print(f"✗ No elements found with selector: {selector}")
        
        # Save page source for debugging
        with open("auction_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\nAuction page source saved as auction_page_source.html")
        
        # Take screenshot
        driver.save_screenshot("auction_page_screenshot.png")
        print("Screenshot saved as auction_page_screenshot.png")
        
        # Wait to see the browser
        print("\nBrowser will close in 10 seconds...")
        time.sleep(10)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_auction_page()