#!/usr/bin/env python3
"""
Debug script to check website structure
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

def debug_website():
    """Check what's actually on the website"""
    
    # Setup Chrome driver
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options)
    
    try:
        print("Navigating to slocalestateauctions.com...")
        driver.get("https://slocalestateauctions.com")
        time.sleep(5)
        
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Take a screenshot
        driver.save_screenshot("website_screenshot.png")
        print("Screenshot saved as website_screenshot.png")
        
        # Get page source and save it
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Page source saved as page_source.html")
        
        # Look for common auction-related elements
        selectors_to_check = [
            "div.auction-item",
            "div.item",
            "article.auction", 
            "li.auction-listing",
            "div.product-item",
            ".auction",
            ".listing",
            ".item",
            "[class*='auction']",
            "[class*='item']",
            "[class*='lot']",
            "[class*='bid']"
        ]
        
        print("\nChecking for auction elements...")
        for selector in selectors_to_check:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"✓ Found {len(elements)} elements with selector: {selector}")
                if len(elements) < 10:  # Only show details for small lists
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text[:100] if elem.text else elem.get_attribute('class')
                            print(f"  Element {i+1}: {text}")
                        except:
                            print(f"  Element {i+1}: [Could not get text]")
            else:
                print(f"✗ No elements found with selector: {selector}")
        
        # Wait a bit to see the browser
        print("\nBrowser will close in 10 seconds...")
        time.sleep(10)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_website()