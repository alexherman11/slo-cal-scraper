import logging
from datetime import datetime
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
                existing_item.updated_at = datetime.utcnow()
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
    
    def get_active_items(self, limit: Optional[int] = None) -> List[Item]:
        """Get all active auction items"""
        with self.get_session() as session:
            query = session.query(Item).filter_by(is_active=True)
            query = query.order_by(desc(Item.created_at))
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
    
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
    
    def save_profit_analysis(self, analysis_data: Dict[str, Any]):
        """Save profit analysis for an item"""
        with self.get_session() as session:
            # Check if analysis exists for today
            existing = session.query(ProfitAnalysis).filter(
                and_(
                    ProfitAnalysis.item_id == analysis_data['item_id'],
                    ProfitAnalysis.analysis_date >= datetime.utcnow().date()
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
    
    def get_watchlist(self, active_only: bool = True) -> List[Watchlist]:
        """Get watchlist items"""
        with self.get_session() as session:
            query = session.query(Watchlist)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()
    
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
                    Item.auction_end < datetime.utcnow()
                )
            ).all()
            
            for item in expired_items:
                item.is_active = False
            
            return len(expired_items)
    
    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """Get item by ID"""
        with self.get_session() as session:
            return session.query(Item).filter_by(item_id=item_id).first()
    
    def get_bid_history(self, item_id: int) -> List[BidHistory]:
        """Get bid history for an item"""
        with self.get_session() as session:
            return session.query(BidHistory).filter_by(
                item_id=item_id
            ).order_by(desc(BidHistory.recorded_at)).all()