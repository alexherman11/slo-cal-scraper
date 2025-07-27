from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config.settings import DATABASE_CONFIG

Base = declarative_base()

class Item(Base):
    __tablename__ = 'items'
    
    item_id = Column(Integer, primary_key=True)
    auction_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    condition = Column(String)
    brand = Column(String)
    model = Column(String)
    current_bid = Column(Float, nullable=False)
    auction_end = Column(DateTime, nullable=False)
    auction_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Item(title='{self.title}', bid=${self.current_bid})>"

class BidHistory(Base):
    __tablename__ = 'bid_history'
    
    history_id = Column(Integer, primary_key=True)
    item_id = Column(Integer, nullable=False)
    bid_amount = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    bid_count = Column(Integer)
    
    def __repr__(self):
        return f"<BidHistory(item_id={self.item_id}, bid=${self.bid_amount})>"

class ComparableSale(Base):
    __tablename__ = 'comparable_sales'
    
    sale_id = Column(Integer, primary_key=True)
    item_id = Column(Integer, nullable=False)
    platform = Column(String, nullable=False)
    sale_price = Column(Float, nullable=False)
    sale_date = Column(DateTime)
    listing_url = Column(String)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ComparableSale(platform={self.platform}, price=${self.sale_price})>"

class ProfitAnalysis(Base):
    __tablename__ = 'profit_analysis'
    
    analysis_id = Column(Integer, primary_key=True)
    item_id = Column(Integer, nullable=False)
    estimated_value = Column(Float)
    current_bid = Column(Float, nullable=False)
    potential_profit = Column(Float)
    profit_margin = Column(Float)
    confidence_score = Column(Float)
    recommendation = Column(String)
    analysis_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ProfitAnalysis(item_id={self.item_id}, margin={self.profit_margin}%)>"

class Watchlist(Base):
    __tablename__ = 'watchlist'
    
    watch_id = Column(Integer, primary_key=True)
    keyword = Column(String, nullable=False)
    category = Column(String)
    min_profit_threshold = Column(Float, default=50.0)
    max_bid_amount = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<Watchlist(keyword='{self.keyword}', threshold={self.min_profit_threshold}%)>"

class ScrapeSession(Base):
    __tablename__ = 'scrape_sessions'
    
    session_id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime)
    items_found = Column(Integer, default=0)
    items_flagged = Column(Integer, default=0)
    status = Column(String, default='running')
    error_message = Column(String)
    
    def __repr__(self):
        return f"<ScrapeSession(id={self.session_id}, status={self.status})>"

# Create engine and session
engine = create_engine(f"sqlite:///{DATABASE_CONFIG['path']}", echo=DATABASE_CONFIG['echo'])
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)