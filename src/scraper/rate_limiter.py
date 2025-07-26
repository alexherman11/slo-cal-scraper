import time
import random
import logging
from datetime import datetime, timedelta
from typing import List

logger = logging.getLogger(__name__)

class PoliteRateLimiter:
    """
    Implements polite rate limiting for web scraping with human-like behavior
    """
    
    def __init__(self, min_delay: float = 2, max_delay: float = 5, 
                 requests_per_minute: int = 15):
        """
        Initialize rate limiter
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            requests_per_minute: Maximum number of requests per minute
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_per_minute = requests_per_minute
        self.request_times: List[datetime] = []
        
    def wait(self):
        """Wait before making the next request"""
        now = datetime.now()
        
        # Remove old requests (older than 1 minute)
        self.request_times = [
            req_time for req_time in self.request_times
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Check if we've hit the per-minute limit
        if len(self.request_times) >= self.requests_per_minute:
            # Calculate how long to wait
            oldest_request = self.request_times[0]
            time_since_oldest = (now - oldest_request).total_seconds()
            
            if time_since_oldest < 60:
                sleep_time = 60 - time_since_oldest + 1  # Add 1 second buffer
                logger.info(f"Rate limit reached. Waiting {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
        
        # Add random delay for human-like behavior
        delay = random.uniform(self.min_delay, self.max_delay)
        
        # Occasionally add longer delays (human behavior)
        if random.random() < 0.1:  # 10% chance
            delay *= random.uniform(1.5, 2.5)
            logger.debug(f"Adding extended delay: {delay:.1f} seconds")
        
        logger.debug(f"Waiting {delay:.1f} seconds before next request")
        time.sleep(delay)
        
        # Record this request
        self.request_times.append(datetime.now())
    
    def add_jitter(self, base_value: float, jitter_percent: float = 0.2) -> float:
        """
        Add random jitter to a value
        
        Args:
            base_value: Base value to add jitter to
            jitter_percent: Percentage of jitter (0.2 = ±20%)
        
        Returns:
            Value with jitter applied
        """
        jitter = base_value * jitter_percent
        return base_value + random.uniform(-jitter, jitter)
    
    def get_status(self) -> dict:
        """Get current rate limiter status"""
        now = datetime.now()
        
        # Clean old requests
        self.request_times = [
            req_time for req_time in self.request_times
            if now - req_time < timedelta(minutes=1)
        ]
        
        return {
            'requests_in_last_minute': len(self.request_times),
            'requests_remaining': max(0, self.requests_per_minute - len(self.request_times)),
            'can_proceed': len(self.request_times) < self.requests_per_minute
        }