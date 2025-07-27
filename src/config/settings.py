import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Auction site configuration
AUCTION_CONFIG = {
    "base_url": os.getenv("BASE_URL", "https://slocalestateauctions.com"),
    "scrape_delay_min": float(os.getenv("SCRAPE_DELAY_MIN", "2")),
    "scrape_delay_max": float(os.getenv("SCRAPE_DELAY_MAX", "5")),
    "requests_per_minute": int(os.getenv("REQUESTS_PER_MINUTE", "15")),
    "max_pages_per_run": int(os.getenv("MAX_PAGES_PER_RUN", "5")),
}

# Scraper settings
SCRAPER_CONFIG = {
    "headless": os.getenv("HEADLESS_MODE", "True").lower() == "true",
    "user_agent_rotation": os.getenv("USER_AGENT_ROTATION", "True").lower() == "true",
    "timeout": 30,
    "retry_attempts": 3,
}

# Database configuration
DATABASE_CONFIG = {
    "path": os.getenv("DATABASE_PATH", str(DATA_DIR / "auction.db")),
    "echo": False,  # Set to True for SQL debugging
}

# eBay API configuration (for Phase 2)
EBAY_CONFIG = {
    "client_id": os.getenv("EBAY_CLIENT_ID", ""),
    "client_secret": os.getenv("EBAY_CLIENT_SECRET", ""),
    "sandbox": os.getenv("EBAY_SANDBOX", "True").lower() == "true",
}

# Profit thresholds
PROFIT_CONFIG = {
    "min_percentage": float(os.getenv("MIN_PROFIT_PERCENTAGE", "50")),
    "min_amount": float(os.getenv("MIN_PROFIT_AMOUNT", "25")),
}

# Logging configuration
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": os.getenv("LOG_FILE", str(LOG_DIR / "scraper.log")),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# Keywords and categories to watch
WATCH_KEYWORDS = [
    # Jewelry and precious items
    "turquoise", "sterling silver", "gold", "diamond", "emerald", "ruby",
    "bakelite", "vintage jewelry", "estate jewelry",
    
    # Collectibles
    "mercury dime", "silver coin", "sports memorabilia", "star wars",
    "vintage toy", "1980s", "collectible", "rare",
    
    # Specialized items
    "dunhill pipe", "griswold", "wagner", "cast iron", "first edition",
    "signed", "autograph", "antique",
    
    # Electronics (be selective)
    "vintage camera", "leica", "hasselblad", "vintage audio",
]

# Categories to avoid
AVOID_KEYWORDS = [
    "replica", "reproduction", "style", "inspired", "damaged",
    "parts only", "not working", "for parts", "broken",
]

# Monitoring and notification configuration
MONITORING_CONFIG = {
    # Check intervals
    "urgent_check_interval": int(os.getenv("URGENT_CHECK_INTERVAL", "30")),  # minutes
    "scrape_interval": int(os.getenv("SCRAPE_INTERVAL", "2")),  # hours
    "cleanup_interval": int(os.getenv("CLEANUP_INTERVAL", "24")),  # hours
    
    # Alert thresholds
    "urgent_hours_threshold": int(os.getenv("URGENT_HOURS_THRESHOLD", "24")),  # hours
    "max_pages_per_scrape": int(os.getenv("MAX_PAGES_PER_SCRAPE", "3")),
    
    # Notification settings
    "notifications": {
        "desktop_notifications": os.getenv("DESKTOP_NOTIFICATIONS", "True").lower() == "true",
        "email": {
            "enabled": os.getenv("EMAIL_NOTIFICATIONS", "False").lower() == "true",
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "sender_email": os.getenv("SENDER_EMAIL", ""),
            "sender_password": os.getenv("SENDER_PASSWORD", ""),
            "recipient_email": os.getenv("RECIPIENT_EMAIL", ""),
        }
    }
}