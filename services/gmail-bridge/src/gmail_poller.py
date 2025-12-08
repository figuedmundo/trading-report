"""Gmail IMAP Polling Service."""

import asyncio
import re
import logging
import hmac
import hashlib
import json
from email.parser import BytesParser
from email import policy
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import aiohttp
from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from .config import Config
from .models import EmailData, WebhookPayload, PollStats

logger = logging.getLogger(__name__)


class GmailPoller:
    """Polls Gmail via IMAP and forwards trading report emails to webhook."""

    def __init__(self):
        """Initialize Gmail poller with configuration."""
        self.config = Config
        self.imap_client: Optional[IMAPClient] = None
        self.processed_uids: set = set()
        self.is_running = False
        self.last_poll_time: Optional[datetime] = None
        self.next_poll_time: Optional[datetime] = None
        self.total_emails_processed = 0
        self.total_errors = 0
        self.poll_task: Optional[asyncio.Task] = None

    def connect_imap(self) -> IMAPClient:
        """Connect to Gmail IMAP server."""
        try:
            client = IMAPClient(
                self.config.IMAP_HOST,
                port=self.config.IMAP_PORT,
                ssl=True
            )
            client.login(self.config.SMTP_USER, self.config.EMAIL_PASSWORD)
            client.select_folder("INBOX")
            logger.info(f"Connected to IMAP server: {self.config.IMAP_HOST}:{self.config.IMAP_PORT}")
            return client
        except IMAPClientError as e:
            logger.error(f"IMAP authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            raise

    def disconnect_imap(self) -> None:
        """Disconnect from IMAP server."""
        if self.imap_client:
            try:
                self.imap_client.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.warning(f"Error during IMAP logout: {e}")
            finally:
                self.imap_client = None

    def extract_url_from_body(self, body: str) -> Optional[str]:
        """Extract first URL from email body."""
        url_pattern = r'https?://[^\s<>"\']+'
        matches = re.findall(url_pattern, body)

        if matches:
            # Prioritize ProTradingSkills URLs if available
            pts_urls = [url for url in matches if 'protradingskills.com' in url.lower()]
            if pts_urls:
                return pts_urls[0]
            return matches[0]

        return None

    def parse_email(self, raw_email: bytes) -> Optional[Dict[str, Any]]:
        """Parse raw email bytes into structured data."""
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_email)

            subject = msg.get("Subject", "")
            from_addr = msg.get("From", "")
            to_addr = msg.get("To", "")
            date = msg.get("Date", "")

            # Extract body (prefer plain text, fallback to HTML)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    elif content_type == "text/html" and not body:
                        body = part.get_payload(decode=True).decode(errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")

            return {
                "from": from_addr,
                "subject": subject,
                "to": to_addr,
                "date": date,
                "body": body,
            }
        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return None

    async def forward_to_webhook(self, email_data: Dict[str, Any]) -> bool:
        """Forward email data to webhook."""
        try:
            report_url = self.extract_url_from_body(email_data.get("body", ""))

            if not report_url:
                logger.warning(f"No URL found in email from {email_data.get('from')}")
                return False

            # Prepare payload
            payload = WebhookPayload(
                from_email=email_data.get("from", ""),
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                report_url=report_url,
                received_at=datetime.utcnow(),
            )

            # Prepare headers and body
            # Use mode='json' to ensure datetime objects are serialized to strings
            payload_dict = payload.model_dump(mode='json')
            # Using json.dumps with default separators to match standard JSON serialization
            # Note: Pydantic's model_dump_json() could also be used but we need consistent bytes for signing
            json_body = json.dumps(payload_dict).encode("utf-8")
            
            headers = {
                "Content-Type": "application/json"
            }

            # Add signature if secret is configured
            if self.config.WEBHOOK_SECRET_KEY:
                signature = hmac.new(
                    self.config.WEBHOOK_SECRET_KEY.encode("utf-8"),
                    json_body,
                    hashlib.sha256
                ).hexdigest()
                headers["X-Signature"] = signature
            else:
                logger.warning("WEBHOOK_SECRET_KEY not configured - sending request without signature")

            # Send to webhook with retry logic
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        self.config.WEBHOOK_URL,
                        data=json_body,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.WEBHOOK_TIMEOUT),
                    ) as response:
                        if response.status in (200, 201, 202):
                            logger.info(f"Successfully forwarded email to webhook: {report_url}")
                            return True
                        else:
                            error_text = await response.text()
                            logger.error(f"Webhook returned status {response.status}: {error_text}")
                            self.total_errors += 1
                            return False
                except asyncio.TimeoutError:
                    logger.error(f"Webhook request timeout after {self.config.WEBHOOK_TIMEOUT}s")
                    self.total_errors += 1
                    return False

        except Exception as e:
            logger.error(f"Failed to forward to webhook: {e}")
            self.total_errors += 1
            return False

    async def poll_once(self) -> PollStats:
        """Poll inbox once and process new emails."""
        stats = PollStats(
            timestamp=datetime.utcnow(),
            messages_found=0,
            new_messages=0,
            successfully_processed=0,
            failed_count=0,
        )

        if not self.imap_client:
            stats.errors.append("IMAP client not connected")
            return stats

        try:
            # Search for emails matching criteria
            messages = self.imap_client.search(self.config.EMAIL_SEARCH_CRITERIA)
            stats.messages_found = len(messages)

            if not messages:
                logger.debug("No messages matching search criteria")
                return stats

            # Filter out already processed UIDs
            new_messages = [uid for uid in messages if uid not in self.processed_uids]
            stats.new_messages = len(new_messages)

            if not new_messages:
                logger.debug(f"All {stats.messages_found} messages already processed")
                return stats

            logger.info(f"Found {len(new_messages)} new message(s)")

            for uid in new_messages:
                try:
                    # Fetch email
                    raw_message = self.imap_client.fetch([uid], ["RFC822"])
                    raw_email = raw_message[uid][b"RFC822"]

                    # Parse email
                    email_data = self.parse_email(raw_email)
                    if not email_data:
                        self.processed_uids.add(uid)
                        stats.failed_count += 1
                        continue

                    # Apply sender filter if configured
                    if self.config.EMAIL_SENDER_FILTER:
                        if self.config.EMAIL_SENDER_FILTER not in email_data.get("from", ""):
                            logger.info(
                                f"Skipping email from {email_data.get('from')} "
                                f"(doesn't match filter '{self.config.EMAIL_SENDER_FILTER}')"
                            )
                            self.processed_uids.add(uid)
                            continue

                    # Forward to webhook
                    success = await self.forward_to_webhook(email_data)

                    if success:
                        stats.successfully_processed += 1
                        self.total_emails_processed += 1
                        self.processed_uids.add(uid)

                        # Mark as read if configured
                        if self.config.MARK_AS_READ:
                            try:
                                self.imap_client.add_flags([uid], ["\\Seen"])
                                logger.debug(f"Marked email UID {uid} as read")
                            except Exception as e:
                                logger.warning(f"Failed to mark email as read: {e}")
                    else:
                        stats.failed_count += 1

                except Exception as e:
                    logger.error(f"Error processing email UID {uid}: {e}")
                    stats.errors.append(f"Failed to process UID {uid}: {str(e)}")
                    stats.failed_count += 1
                    continue

            return stats

        except IMAPClientError as e:
            logger.error(f"IMAP error during poll: {e}")
            stats.errors.append(f"IMAP error: {str(e)}")
            self.imap_client = None
            return stats
        except Exception as e:
            logger.error(f"Unexpected error during poll: {e}")
            stats.errors.append(f"Unexpected error: {str(e)}")
            return stats

    async def run(self) -> None:
        """Main polling loop."""
        logger.info(f"Starting Gmail bridge service (poll interval: {self.config.POLL_INTERVAL}s)")
        logger.info(f"IMAP: {self.config.IMAP_HOST}:{self.config.IMAP_PORT}")
        logger.info(f"Webhook URL: {self.config.WEBHOOK_URL}")
        logger.info(f"Search criteria: {self.config.EMAIL_SEARCH_CRITERIA}")

        if self.config.EMAIL_SENDER_FILTER:
            logger.info(f"Sender filter: {self.config.EMAIL_SENDER_FILTER}")

        self.is_running = True
        reconnect_delay = 5

        while self.is_running:
            try:
                # Connect if not already connected
                if not self.imap_client:
                    try:
                        self.imap_client = self.connect_imap()
                        reconnect_delay = 5  # Reset on successful connection
                    except Exception as e:
                        logger.error(f"Failed to connect to IMAP, retrying in {reconnect_delay}s: {e}")
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 2, 300)  # Cap at 5 minutes
                        continue

                # Poll once
                self.last_poll_time = datetime.utcnow()
                self.next_poll_time = self.last_poll_time + timedelta(seconds=self.config.POLL_INTERVAL)
                stats = await self.poll_once()

                if stats.successfully_processed > 0:
                    logger.info(
                        f"Poll complete: {stats.successfully_processed} emails processed, "
                        f"{stats.failed_count} failed"
                    )

                # Wait before next poll
                await asyncio.sleep(self.config.POLL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Polling task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                self.total_errors += 1
                self.disconnect_imap()
                await asyncio.sleep(10)

        self.is_running = False
        self.disconnect_imap()
        logger.info("Gmail bridge service stopped")

    def stop(self) -> None:
        """Stop the polling service."""
        self.is_running = False
        if self.poll_task and not self.poll_task.done():
            self.poll_task.cancel()
