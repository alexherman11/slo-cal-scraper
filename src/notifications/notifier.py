import logging
import smtplib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    MimeText = None
    MimeMultipart = None

try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    notification = None

logger = logging.getLogger(__name__)

class AuctionNotifier:
    """Handles notifications for urgent auction items"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize notifier with configuration"""
        self.config = config or {}
        self.email_config = self.config.get('email', {})
        self.desktop_enabled = self.config.get('desktop_notifications', True)
        
    def notify_urgent_items(self, urgent_items: List[Dict[str, Any]]):
        """Send notifications for urgent profitable items"""
        if not urgent_items:
            logger.info("No urgent items to notify about")
            return
        
        # Desktop notification for immediate attention
        if self.desktop_enabled:
            self.send_desktop_notification(urgent_items)
        
        # Email notification for detailed info
        if self.email_config.get('enabled', False):
            self.send_email_notification(urgent_items)
        
        # Console alert
        self.print_urgent_alert(urgent_items)
        
        # Log the notification
        logger.info(f"Sent notifications for {len(urgent_items)} urgent items")
    
    def send_desktop_notification(self, urgent_items: List[Dict[str, Any]]):
        """Send Windows desktop notification"""
        if not NOTIFICATIONS_AVAILABLE:
            logger.warning("Desktop notifications not available - plyer not installed")
            return
            
        try:
            count = len(urgent_items)
            most_urgent = urgent_items[0]  # Already sorted by time
            
            title = f"*** {count} Urgent Auction Alert{'s' if count > 1 else ''}! ***"
            
            if count == 1:
                item = most_urgent['item']
                analysis = most_urgent['analysis']
                message = (f"{item['title'][:50]}...\n"
                          f"Current: ${item['current_bid']:.2f}\n"
                          f"Profit: {analysis['profit_margin']:.1f}%\n"
                          f"Time: {most_urgent['hours_remaining']:.1f}h remaining")
            else:
                message = (f"Most urgent: {most_urgent['item']['title'][:40]}...\n"
                          f"Time: {most_urgent['hours_remaining']:.1f}h remaining\n"
                          f"Up to {max(item['analysis']['profit_margin'] for item in urgent_items):.1f}% profit")
            
            notification.notify(
                title=title,
                message=message,
                app_name="Estate Auction Scraper",
                timeout=30,  # 30 seconds
                toast=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")
    
    def send_email_notification(self, urgent_items: List[Dict[str, Any]]):
        """Send email notification with detailed item info"""
        if not EMAIL_AVAILABLE:
            logger.warning("Email notifications not available - email modules not accessible")
            return
            
        try:
            smtp_server = self.email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = self.email_config.get('smtp_port', 587)
            sender_email = self.email_config.get('sender_email')
            sender_password = self.email_config.get('sender_password')
            recipient_email = self.email_config.get('recipient_email')
            
            if not all([sender_email, sender_password, recipient_email]):
                logger.warning("Email configuration incomplete, skipping email notification")
                return
            
            # Create email content
            subject = f"🚨 {len(urgent_items)} Urgent Auction Alert{'s' if len(urgent_items) > 1 else ''}"
            
            html_body = self.create_email_html(urgent_items)
            
            # Create message
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient_email
            
            html_part = MimeText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {recipient_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def create_email_html(self, urgent_items: List[Dict[str, Any]]) -> str:
        """Create HTML email content"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #ff4444; color: white; padding: 15px; text-align: center; }}
                .item {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; background-color: #f9f9f9; }}
                .urgent {{ border-left: 5px solid #ff4444; }}
                .profit {{ color: #22aa22; font-weight: bold; }}
                .time {{ color: #ff6600; font-weight: bold; }}
                .link {{ background-color: #0066cc; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 Urgent Auction Alerts - {len(urgent_items)} Item{'s' if len(urgent_items) > 1 else ''}</h2>
                <p>High-profit items ending soon!</p>
            </div>
        """
        
        for item_data in urgent_items:
            item = item_data['item']
            analysis = item_data['analysis']
            hours_left = item_data['hours_remaining']
            
            urgency_class = "urgent" if hours_left < 6 else ""
            
            html += f"""
            <div class="item {urgency_class}">
                <h3>{item['title']}</h3>
                <p><strong>Current Bid:</strong> ${item['current_bid']:.2f}</p>
                <p><strong>Estimated Value:</strong> ${analysis['estimated_value']:.2f}</p>
                <p class="profit"><strong>Profit Margin:</strong> {analysis['profit_margin']:.1f}%</p>
                <p class="time"><strong>Time Remaining:</strong> {hours_left:.1f} hours</p>
                <p><strong>Confidence:</strong> {analysis['confidence_score']:.1f}%</p>
                <p><a href="{item['auction_url']}" class="link">View Item</a></p>
                <p><small>Auction ID: {item['auction_id']}</small></p>
            </div>
            """
        
        html += f"""
            <div style="text-align: center; margin-top: 20px; color: #666;">
                <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Estate Auction Scraper - Your Profit Alert System</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def print_urgent_alert(self, urgent_items: List[Dict[str, Any]]):
        """Print console alert for urgent items"""
        # Use ASCII characters for Windows console compatibility
        print("\n" + "="*80)
        print("*** URGENT AUCTION ALERTS ***")
        print("="*80)
        print(f"Found {len(urgent_items)} profitable item{'s' if len(urgent_items) > 1 else ''} ending soon!")
        print("-"*80)
        
        for i, item_data in enumerate(urgent_items, 1):
            item = item_data['item']
            analysis = item_data['analysis']
            hours_left = item_data['hours_remaining']
            
            urgency_marker = ">>>" if hours_left < 6 else ">>>"
            
            print(f"\n{urgency_marker} ALERT #{i}:")
            print(f"   Item: {item['title'][:60]}...")
            print(f"   Current Bid: ${item['current_bid']:.2f}")
            print(f"   Profit Margin: {analysis['profit_margin']:.1f}%")
            print(f"   Time Left: {hours_left:.1f} hours")
            print(f"   URL: {item['auction_url']}")
        
        print("\n" + "="*80)
        print("TIP: Click the links above to view and bid on items!")
        print("="*80 + "\n")

    def test_notifications(self):
        """Test notification system with dummy data"""
        test_items = [{
            'item': {
                'item_id': 1,
                'auction_id': 'test_123',
                'title': 'Test Item - Vintage Gold Coin Collection',
                'current_bid': 25.00,
                'auction_end': datetime.now(),
                'auction_url': 'https://example.com/test'
            },
            'analysis': {
                'estimated_value': 150.00,
                'profit_margin': 85.5,
                'confidence_score': 0.8
            },
            'hours_remaining': 2.5
        }]
        
        print("Testing notification system...")
        self.notify_urgent_items(test_items)
        print("Test notifications sent!")