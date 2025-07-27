#!/usr/bin/env python3
"""
Inspect the coin dealer page to understand its structure
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

def inspect_coin_page():
    """Inspect the coin dealer page structure"""
    
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options)
    
    try:
        coin_url = "https://slocalestateauctions.com/auction/coins_silver_gold_cccx"
        print(f"Inspecting: {coin_url}")
        driver.get(coin_url)
        time.sleep(5)
        
        print(f"Page title: {driver.title}")
        
        # Save page source for analysis
        with open("coin_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Page source saved as coin_page_source.html")
        
        # Look for various element types that might contain items
        selectors_to_check = [
            "table tr",           # Table rows
            "div.card",           # Bootstrap cards
            "div.row > div",      # Grid items  
            "li",                 # List items
            "[class*='item']",    # Anything with 'item' in class
            "[class*='lot']",     # Anything with 'lot' in class
            "[class*='product']", # Anything with 'product' in class
            "div[id]",            # Divs with IDs
            ".container > div",   # Direct children of container
            "img",                # Images (might indicate items)
            "h1, h2, h3, h4, h5", # Headers that might be item titles
            "*[data-*]"           # Elements with data attributes
        ]
        
        print("\nAnalyzing page structure...")
        for selector in selectors_to_check:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"\n✓ {selector}: {len(elements)} elements")
                    # Show sample text from first few elements
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()[:100] if elem.text else "[No text]"
                            classes = elem.get_attribute('class') or "[No classes]"
                            tag = elem.tag_name
                            print(f"  [{i+1}] {tag}: {text}... (classes: {classes})")
                        except:
                            print(f"  [{i+1}] [Error getting element info]")
                else:
                    print(f"✗ {selector}: 0 elements")
            except Exception as e:
                print(f"✗ {selector}: Error - {e}")
        
        print(f"\nBrowser will close in 10 seconds...")
        time.sleep(10)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    inspect_coin_page()