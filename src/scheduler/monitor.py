import logging
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any
import threading
import signal
import sys

from src.scraper.enhanced_auction_scraper import EnhancedAuctionScraper
from src.database.db_manager import DatabaseManager
from src.notifications.notifier import AuctionNotifier
from src.config.settings import PROFIT_CONFIG, MONITORING_CONFIG

logger = logging.getLogger(__name__)

class AuctionMonitor:
    """Continuous monitoring system for auction alerts"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the monitor"""
        self.config = config or MONITORING_CONFIG
        self.db_manager = DatabaseManager()
        self.notifier = AuctionNotifier(self.config.get('notifications', {}))
        self.running = False
        self.monitor_thread = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    def start_monitoring(self):
        """Start the continuous monitoring process"""
        if self.running:
            logger.warning("Monitor is already running")
            return
        
        self.running = True
        logger.info("Starting auction monitor...")
        
        # Schedule different tasks
        self.setup_schedules()
        
        # Start the monitoring thread
        self.monitor_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Auction monitor started successfully")
        logger.info("Monitoring schedule:")
        logger.info(f"  - Urgent alerts: Every {self.config.get('urgent_check_interval', 30)} minutes")
        logger.info(f"  - Full scrape: Every {self.config.get('scrape_interval', 2)} hours")
        logger.info(f"  - Database cleanup: Every {self.config.get('cleanup_interval', 24)} hours")
    
    def setup_schedules(self):
        """Setup monitoring schedules"""
        # Urgent item checks (frequent)
        urgent_interval = self.config.get('urgent_check_interval', 30)  # minutes
        schedule.every(urgent_interval).minutes.do(self.check_urgent_items)
        
        # Full scraping (less frequent)
        scrape_interval = self.config.get('scrape_interval', 2)  # hours
        schedule.every(scrape_interval).hours.do(self.run_full_scrape)
        
        # Database cleanup (daily)
        cleanup_interval = self.config.get('cleanup_interval', 24)  # hours
        schedule.every(cleanup_interval).hours.do(self.cleanup_database)
        
        # Run initial checks
        schedule.every().minute.do(self.initial_checks).tag('initial')
    
    def run_scheduler(self):
        """Run the scheduled tasks"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Continue monitoring even if one task fails
    
    def initial_checks(self):
        """Run initial checks on startup"""
        logger.info("Running initial checks...")
        self.check_urgent_items()
        
        # Clear the initial check schedule
        schedule.clear('initial')
        return schedule.CancelJob
    
    def check_urgent_items(self):
        """Check for urgent profitable items"""
        try:
            logger.info("Checking for urgent profitable items...")
            
            min_profit = PROFIT_CONFIG.get('min_percentage', 50.0)
            hours_remaining = self.config.get('urgent_hours_threshold', 24)
            
            urgent_items = self.db_manager.get_urgent_profitable_items(
                min_profit_margin=min_profit,
                hours_remaining=hours_remaining
            )
            
            if urgent_items:
                logger.info(f"Found {len(urgent_items)} urgent items")
                self.notifier.notify_urgent_items(urgent_items)
            else:
                logger.info("No urgent items found")
                
        except Exception as e:
            logger.error(f"Error checking urgent items: {e}")
    
    def run_full_scrape(self):
        """Run a full scraping session"""
        try:
            logger.info("Starting scheduled full scrape...")
            
            scraper = EnhancedAuctionScraper(headless=True)
            max_pages = self.config.get('max_pages_per_scrape', 3)
            
            results = scraper.run(max_auction_groups=max_pages)
            
            logger.info(f"Scrape completed: {results['items_found']} items found, "
                       f"{results['items_flagged']} flagged as valuable")
            
            # After scraping, check for new urgent items
            self.check_urgent_items()
            
        except Exception as e:
            logger.error(f"Error during scheduled scrape: {e}")
    
    def cleanup_database(self):
        """Clean up old database entries"""
        try:
            logger.info("Running database cleanup...")
            
            # Mark expired items as inactive
            expired_count = self.db_manager.mark_expired_items()
            logger.info(f"Marked {expired_count} expired items as inactive")
            
            # Additional cleanup can be added here
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
    
    def stop(self):
        """Stop the monitoring process"""
        if not self.running:
            return
        
        logger.info("Stopping auction monitor...")
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # Clear all scheduled jobs
        schedule.clear()
        
        logger.info("Auction monitor stopped")
    
    def status(self):
        """Get monitor status"""
        return {
            'running': self.running,
            'scheduled_jobs': len(schedule.jobs),
            'next_run': str(schedule.next_run()) if schedule.jobs else None,
            'config': self.config
        }
    
    def run_manual_check(self):
        """Run a manual urgent item check"""
        logger.info("Running manual urgent item check...")
        self.check_urgent_items()
    
    def test_system(self):
        """Test the monitoring system"""
        logger.info("Testing monitoring system...")
        
        # Test notifications
        self.notifier.test_notifications()
        
        # Test database connection
        try:
            active_items = self.db_manager.get_active_items()
            logger.info(f"Database test: Found {len(active_items)} active items")
        except Exception as e:
            logger.error(f"Database test failed: {e}")
        
        logger.info("System test completed")

def run_monitor_service():
    """Run the monitor as a service"""
    monitor = AuctionMonitor()
    
    try:
        monitor.start_monitoring()
        
        print("🚀 Auction Monitor Started!")
        print("="*50)
        print("The system is now monitoring for urgent auction items.")
        print("Press Ctrl+C to stop the monitor.")
        print("="*50)
        
        # Keep the main thread alive
        while monitor.running:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down monitor...")
    except Exception as e:
        logger.error(f"Monitor service error: {e}")
    finally:
        monitor.stop()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_monitor_service()