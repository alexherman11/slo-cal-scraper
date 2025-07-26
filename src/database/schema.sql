-- Core auction data structure
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    condition TEXT,
    brand TEXT,
    model TEXT,
    current_bid REAL NOT NULL,
    auction_end TIMESTAMP NOT NULL,
    auction_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Price history for trend analysis
CREATE TABLE IF NOT EXISTS bid_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    bid_amount REAL NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bid_count INTEGER
);

-- Comparable sales for profit calculations (Phase 2)
CREATE TABLE IF NOT EXISTS comparable_sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    platform TEXT NOT NULL, -- 'ebay', 'mercari', etc.
    sale_price REAL NOT NULL,
    sale_date TIMESTAMP,
    listing_url TEXT,
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profit analysis
CREATE TABLE IF NOT EXISTS profit_analysis (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    estimated_value REAL,
    current_bid REAL NOT NULL,
    potential_profit REAL,
    profit_margin REAL,
    confidence_score REAL,
    recommendation TEXT,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Watchlist for specific searches
CREATE TABLE IF NOT EXISTS watchlist (
    watch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    category TEXT,
    min_profit_threshold REAL DEFAULT 50.0,
    max_bid_amount REAL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping sessions for tracking
CREATE TABLE IF NOT EXISTS scrape_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    items_found INTEGER DEFAULT 0,
    items_flagged INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    error_message TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_items_auction_end ON items(auction_end) WHERE is_active = 1;
CREATE INDEX IF NOT EXISTS idx_items_current_bid ON items(current_bid);
CREATE INDEX IF NOT EXISTS idx_items_title ON items(title);
CREATE INDEX IF NOT EXISTS idx_bid_history_item_time ON bid_history(item_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_profit_analysis_margin ON profit_analysis(profit_margin DESC);
CREATE INDEX IF NOT EXISTS idx_comparable_sales_item ON comparable_sales(item_id, platform);

-- Enable Write-Ahead Logging for better concurrency
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = 10000;