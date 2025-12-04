"""
Gmail IMAP Polling Service

Monitors Gmail inbox for trading report emails and forwards them to n8n webhook.
"""

import asyncio
import re
import email
from email import policy
from email.parser import BytesParser
from typing import Optional, Dict, Any
from datetime import datetime
import logging

import aiohttp
from imapclient import IMAPClient
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "gmail-bridge", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


class GmailPoller:
    """Polls Gmail via IMAP and forwards trading report emails to webhook."""
    
    def __init__(self):
        self.imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        self.email_user = os.getenv("SMTP_USER")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:5678/webhook-test/webhook/trading-reports")
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "60"))  # seconds
        self.search_criteria = os.getenv("EMAIL_SEARCH_CRITERIA", "UNSEEN")
        self.sender_filter = os.getenv("EMAIL_SENDER_FILTER", "")  # Optional sender email filter
        
        # Track processed email UIDs to avoid duplicates
        self.processed_uids = set()
        
    def connect_imap(self) -> IMAPClient:
        """Connect to Gmail IMAP server."""
        try:
            client = IMAPClient(self.imap_host, port=self.imap_port, ssl=True)
            client.login(self.email_user, self.email_password)
            client.select_folder("INBOX")
            logger.info(f"Connected to IMAP server: {self.imap_host}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            raise
    
    def extract_url_from_body(self, body: str) -> Optional[str]:
        """Extract first URL from email body."""
        # Match URLs starting with http:// or https://
        url_pattern = r'https?://[^\s<>"\']+'
        matches = re.findall(url_pattern, body)
        
        if matches:
            # Filter for ProTradingSkills URLs if available
            pts_urls = [url for url in matches if 'protradingskills.com' in url.lower()]
            if pts_urls:
                return pts_urls[0]
            # Otherwise return first URL found
            return matches[0]
        
        return None
    
    def parse_email(self, raw_email: bytes) -> Dict[str, Any]:
        """Parse raw email bytes into structured data."""
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_email)
            
            # Extract basic fields
            subject = msg.get('Subject', '')
            from_addr = msg.get('From', '')
            to_addr = msg.get('To', '')
            date = msg.get('Date', '')
            
            # Extract body (prefer plain text, fallback to HTML)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
                    elif content_type == "text/html" and not body:
                        body = part.get_payload(decode=True).decode(errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
            
            return {
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "body": body
            }
        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return {}
    
    async def forward_to_webhook(self, email_data: Dict[str, Any]) -> bool:
        """Forward email data to n8n webhook."""
        try:
            # Extract URL from body
            report_url = self.extract_url_from_body(email_data.get("body", ""))
            
            if not report_url:
                logger.warning(f"No URL found in email from {email_data.get('from')}")
                return False
            
            # Prepare payload matching n8n webhook expectations
            payload = {
                "from": email_data.get("from", ""),
                "subject": email_data.get("subject", ""),
                "body": email_data.get("body", ""),
                "report_url": report_url,
                "received_at": datetime.utcnow().isoformat()
            }
            
            # Send to webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Successfully forwarded email to webhook: {report_url}")
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to forward to webhook: {e}")
            return False
    
    async def poll_once(self, client: IMAPClient) -> int:
        """Poll inbox once and process new emails."""
        try:
            # Search for emails matching criteria
            messages = client.search(self.search_criteria)
            
            if not messages:
                logger.debug("No new messages found")
                return 0
            
            # Filter out already processed UIDs
            new_messages = [uid for uid in messages if uid not in self.processed_uids]
            
            if not new_messages:
                logger.debug(f"All {len(messages)} messages already processed")
                return 0
            
            logger.info(f"Found {len(new_messages)} new message(s)")
            
            processed_count = 0
            for uid in new_messages:
                try:
                    # Fetch email
                    raw_message = client.fetch([uid], ['RFC822'])
                    raw_email = raw_message[uid][b'RFC822']
                    
                    # Parse email
                    email_data = self.parse_email(raw_email)
                    
                    # Apply sender filter if configured
                    if self.sender_filter and self.sender_filter not in email_data.get("from", ""):
                        logger.info(f"Skipping email from {email_data.get('from')} (doesn't match filter)")
                        self.processed_uids.add(uid)
                        continue
                    
                    # Forward to webhook
                    success = await self.forward_to_webhook(email_data)
                    
                    if success:
                        processed_count += 1
                        self.processed_uids.add(uid)
                        
                        # Mark as read (optional)
                        if os.getenv("MARK_AS_READ", "false").lower() == "true":
                            client.add_flags([uid], ['\\Seen'])
                            logger.debug(f"Marked email UID {uid} as read")
                    
                except Exception as e:
                    logger.error(f"Error processing email UID {uid}: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error during poll: {e}")
            return 0
    
    async def run(self):
        """Main polling loop."""
        logger.info(f"Starting Gmail bridge service (poll interval: {self.poll_interval}s)")
        logger.info(f"Webhook URL: {self.webhook_url}")
        logger.info(f"IMAP search criteria: {self.search_criteria}")
        
        if self.sender_filter:
            logger.info(f"Sender filter: {self.sender_filter}")
        
        client = None
        
        try:
            client = self.connect_imap()
            
            while True:
                try:
                    processed = await self.poll_once(client)
                    
                    if processed > 0:
                        logger.info(f"Processed {processed} email(s) successfully")
                    
                    # Wait before next poll
                    await asyncio.sleep(self.poll_interval)
                    
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    # Try to reconnect
                    try:
                        if client:
                            client.logout()
                    except:
                        pass
                    
                    await asyncio.sleep(10)  # Wait before reconnecting
                    client = self.connect_imap()
                    
        except KeyboardInterrupt:
            logger.info("Shutting down Gmail bridge service...")
        finally:
            if client:
                try:
                    client.logout()
                    logger.info("Disconnected from IMAP server")
                except:
                    pass


async def main():
    """Entry point."""
    poller = GmailPoller()
    await poller.run()


if __name__ == "__main__":
    asyncio.run(main())
