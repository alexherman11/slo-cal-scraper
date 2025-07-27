Estate Auction Web Scraper
An intelligent web scraper designed to identify undervalued items and calculate potential resale profits.

Overview
This scraper automatically monitors estate auctions, identifies items with high profit potential, and provides market value estimates to help make informed bidding decisions. It focuses on items that are:

Significantly undervalued
Highly resellable on platforms like eBay, Facebook Marketplace, and Craigslist
Match specific keywords or categories you're interested in
Features (Phase 1 - Current)
Automated Scraping: Monitors auction listings with polite rate limiting
Intelligent Detection: Identifies valuable items using keyword matching and pattern recognition
Database Storage: Tracks items, bid history, and profit analysis
Watchlist Support: Set custom keywords and profit thresholds
Anti-Detection: Uses undetected-chromedriver with human-like behavior
Comprehensive Logging: Colored console output and detailed log files
Installation
Clone the repository
bash
git clone <repository-url>
cd estate-auction-scraper
Create a virtual environment
bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies
bash
pip install -r requirements.txt
Set up configuration
bash
cp .env.example .env
# Edit .env with your settings
Install Chrome/Chromium The scraper requires Chrome or Chromium browser installed on your system.
Quick Start
Test the setup
bash
python main.py test
Run your first scrape
bash
python main.py scrape
View results
bash
python main.py view
Usage
Command Line Interface
bash
# Basic scraping (5 pages, headless mode)
python main.py scrape

# Scrape with detailed item pages (slower but more accurate)
python main.py scrape --details

# Scrape specific number of pages
python main.py scrape --pages 10

# Run with browser window visible
python main.py scrape --no-headless

# View database summary
python main.py view

# Add keyword to watchlist
python main.py watch --keyword "sterling silver" --min-profit 60

# Debug mode
python main.py scrape --log-level DEBUG
Configuration
Key settings in .env:

BASE_URL: Target auction site (default: https://slocalestateauctions.com)
SCRAPE_DELAY_MIN/MAX: Delay between requests (seconds)
REQUESTS_PER_MINUTE: Rate limiting
MIN_PROFIT_PERCENTAGE: Minimum profit margin to flag items
HEADLESS_MODE: Run browser in background
Default Watch Keywords
The scraper automatically watches for:

Precious Items: Gold, silver, diamonds, turquoise
Collectibles: Vintage toys, coins, sports memorabilia
Brands: High-end pipes, cast iron cookware, first editions
Electronics: Vintage cameras and audio equipment
Items containing red flags (replica, damaged, broken) are automatically filtered out.

Project Structure
estate-auction-scraper/
├── src/
│   ├── scraper/          # Web scraping components
│   ├── database/         # Database models and manager
│   ├── api/             # External API integrations (Phase 2)
│   └── config/          # Configuration settings
├── data/                # SQLite database storage
├── logs/                # Application logs
├── tests/               # Test suite
└── main.py             # Entry point
Database Schema
The scraper uses SQLite with the following main tables:

items: Auction items and current bids
bid_history: Track bid progression
profit_analysis: Estimated values and margins
watchlist: Custom keywords to monitor
scrape_sessions: Scraping run history
Profit Calculation
Profit estimates account for:

eBay fees: 13.6% final value + 2.35% + $0.30 payment processing
Shipping costs (when applicable)
Market price based on sold listings (Phase 2)
Development Roadmap
Phase 1 (Current) ✅
Core web scraping with Selenium
SQLite database storage
Keyword matching and valuable item detection
Basic profit calculations
Phase 2 🚧
eBay Marketplace Insights API integration
Automated price lookups across platforms
Statistical analysis of sold items
Confidence scoring for estimates
Phase 3 📋
Bid management system
Maximum profitable bid calculations
Automated recommendations
Export reports
Phase 4 🌐
Web interface with Flask/React
Real-time dashboard
Mobile responsive design
Advanced analytics
Testing
Run the test suite:

bash
pytest tests/ -v
Troubleshooting
Common Issues
Chrome driver issues
The scraper uses undetected-chromedriver which should auto-download the correct version
If issues persist, manually download ChromeDriver matching your Chrome version
Rate limiting
Default settings are conservative (15 requests/minute)
Adjust in .env if needed, but be respectful
No items found
Check if the site structure has changed
Try running with --no-headless to see what's happening
Enable DEBUG logging for more details
Debug Mode
For detailed debugging:

bash
python main.py scrape --log-level DEBUG --no-headless
Legal Considerations
This tool is for educational and personal use
Always respect website terms of service
Use reasonable rate limits
Don't interfere with normal site operations
Check local laws regarding web scraping
Contributing
Fork the repository
Create a feature branch
Make your changes
Add tests if applicable
Submit a pull request
License
This project is provided as-is for educational purposes. See LICENSE file for details.

Disclaimer
This tool is designed to help identify potentially valuable items at estate auctions. Always:

Verify item authenticity before bidding
Research current market values
Account for all fees and costs
bid responsibly within your means
The developers are not responsible for any financial decisions made using this tool.

