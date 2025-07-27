import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import and_, or_, desc
from src.database.models import (
    Session, Item, BidHistory, ProfitAnalysis, 
    Watchlist, ScrapeSession, ComparableSale
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the auction scraper"""
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def create_scrape_session(self) -> int:
        """Create a new scraping session"""
        with self.get_session() as session:
            scrape_session = ScrapeSession()
            session.add(scrape_session)
            session.flush()
            return scrape_session.session_id
    
    def update_scrape_session(self, session_id: int, **kwargs):
        """Update scraping session details"""
        with self.get_session() as session:
            scrape_session = session.query(ScrapeSession).filter_by(
                session_id=session_id
            ).first()
            if scrape_session:
                for key, value in kwargs.items():
                    setattr(scrape_session, key, value)
    
    def save_item(self, item_data: Dict[str, Any]) -> Optional[int]:
        """Save or update an auction item"""
        with self.get_session() as session:
            # Check if item already exists
            existing_item = session.query(Item).filter_by(
                auction_id=item_data['auction_id']
            ).first()
            
            if existing_item:
                # Update existing item
                for key, value in item_data.items():
                    setattr(existing_item, key, value)
                existing_item.updated_at = datetime.now(timezone.utc)
                item_id = existing_item.item_id
                
                # Record bid history if price changed
                if existing_item.current_bid != item_data.get('current_bid'):
                    self._record_bid_history(
                        session, item_id, item_data['current_bid']
                    )
            else:
                # Create new item
                new_item = Item(**item_data)
                session.add(new_item)
                session.flush()
                item_id = new_item.item_id
                
                # Record initial bid
                self._record_bid_history(
                    session, item_id, item_data['current_bid']
                )
            
            return item_id
    
    def _record_bid_history(self, session: SQLSession, item_id: int, bid_amount: float):
        """Record bid history for an item"""
        history = BidHistory(
            item_id=item_id,
            bid_amount=bid_amount
        )
        session.add(history)
    
    def get_active_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all active auction items"""
        with self.get_session() as session:
            query = session.query(Item).filter_by(is_active=True)
            query = query.order_by(desc(Item.created_at))
            
            if limit:
                query = query.limit(limit)
            
            items = query.all()
            # Convert to dict to avoid detached instance issues
            return [{
                'item_id': item.item_id,
                'auction_id': item.auction_id,
                'title': item.title,
                'current_bid': item.current_bid,
                'auction_end': item.auction_end,
                'auction_url': item.auction_url,
                'created_at': item.created_at,
                'is_active': item.is_active
            } for item in items]
    
    def get_items_by_keywords(self, keywords: List[str]) -> List[Item]:
        """Get items matching any of the keywords"""
        with self.get_session() as session:
            conditions = []
            for keyword in keywords:
                conditions.append(Item.title.ilike(f'%{keyword}%'))
            
            return session.query(Item).filter(
                and_(
                    or_(*conditions),
                    Item.is_active == True
                )
            ).all()
    
    def get_undervalued_items(self, min_profit_margin: float = 50.0) -> List[Dict[str, Any]]:
        """Get items with high profit potential"""
        with self.get_session() as session:
            # Join with profit analysis
            query = session.query(
                Item, ProfitAnalysis
            ).join(
                ProfitAnalysis, Item.item_id == ProfitAnalysis.item_id
            ).filter(
                and_(
                    Item.is_active == True,
                    ProfitAnalysis.profit_margin >= min_profit_margin
                )
            ).order_by(desc(ProfitAnalysis.profit_margin))
            
            results = []
            for item, analysis in query.all():
                results.append({
                    'item': item,
                    'analysis': analysis
                })
            
            return results
    
    def get_urgent_profitable_items(self, min_profit_margin: float = 50.0, hours_remaining: int = 24) -> List[Dict[str, Any]]:
        """Get profitable items ending within specified hours"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() + timedelta(hours=hours_remaining)
        
        with self.get_session() as session:
            query = session.query(
                Item, ProfitAnalysis
            ).join(
                ProfitAnalysis, Item.item_id == ProfitAnalysis.item_id
            ).filter(
                and_(
                    Item.is_active == True,
                    ProfitAnalysis.profit_margin >= min_profit_margin,
                    Item.auction_end <= cutoff_time,
                    Item.auction_end > datetime.now()  # Not expired
                )
            ).order_by(Item.auction_end)  # Most urgent first
            
            results = []
            for item, analysis in query.all():
                # Calculate hours remaining
                time_remaining = item.auction_end - datetime.now()
                hours_left = time_remaining.total_seconds() / 3600
                
                results.append({
                    'item': {
                        'item_id': item.item_id,
                        'auction_id': item.auction_id,
                        'title': item.title,
                        'current_bid': item.current_bid,
                        'auction_end': item.auction_end,
                        'auction_url': item.auction_url
                    },
                    'analysis': {
                        'estimated_value': analysis.estimated_value,
                        'profit_margin': analysis.profit_margin,
                        'confidence_score': analysis.confidence_score
                    },
                    'hours_remaining': round(hours_left, 1)
                })
            
            return results
    
    def save_profit_analysis(self, analysis_data: Dict[str, Any]):
        """Save profit analysis for an item"""
        with self.get_session() as session:
            # Check if analysis exists for today
            existing = session.query(ProfitAnalysis).filter(
                and_(
                    ProfitAnalysis.item_id == analysis_data['item_id'],
                    ProfitAnalysis.analysis_date >= datetime.now(timezone.utc).date()
                )
            ).first()
            
            if existing:
                # Update existing analysis
                for key, value in analysis_data.items():
                    setattr(existing, key, value)
            else:
                # Create new analysis
                analysis = ProfitAnalysis(**analysis_data)
                session.add(analysis)
    
    def get_watchlist(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get watchlist items"""
        with self.get_session() as session:
            query = session.query(Watchlist)
            if active_only:
                query = query.filter_by(is_active=True)
            watchlist = query.all()
            # Convert to dict to avoid detached instance issues
            return [{
                'watch_id': w.watch_id,
                'keyword': w.keyword,
                'category': w.category,
                'min_profit_threshold': w.min_profit_threshold,
                'max_bid_amount': w.max_bid_amount,
                'is_active': w.is_active,
                'created_at': w.created_at
            } for w in watchlist]
    
    def add_to_watchlist(self, keyword: str, **kwargs):
        """Add keyword to watchlist"""
        with self.get_session() as session:
            watchlist_item = Watchlist(keyword=keyword, **kwargs)
            session.add(watchlist_item)
    
    def mark_expired_items(self):
        """Mark items as inactive if auction has ended"""
        with self.get_session() as session:
            expired_items = session.query(Item).filter(
                and_(
                    Item.is_active == True,
                    Item.auction_end < datetime.now(timezone.utc)
                )
            ).all()
            
            for item in expired_items:
                item.is_active = False
            
            return len(expired_items)
    
    def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get item by ID"""
        with self.get_session() as session:
            item = session.query(Item).filter_by(item_id=item_id).first()
            if item:
                # Convert to dict to avoid detached instance issues
                return {
                    'item_id': item.item_id,
                    'auction_id': item.auction_id,
                    'title': item.title,
                    'current_bid': item.current_bid,
                    'auction_end': item.auction_end,
                    'auction_url': item.auction_url,
                    'created_at': item.created_at,
                    'is_active': item.is_active
                }
            return None
    
    def get_bid_history(self, item_id: int) -> List[BidHistory]:
        """Get bid history for an item"""
        with self.get_session() as session:
            return session.query(BidHistory).filter_by(
                item_id=item_id
            ).order_by(desc(BidHistory.recorded_at)).all()