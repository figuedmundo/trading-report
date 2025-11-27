"""
SMTP client for async email delivery.

Handles SMTP connections and message sending.
"""

import asyncio
from typing import Dict, Any
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import aiosmtplib
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SMTPClient:
    """SMTP client for sending emails."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SMTP client.

        Args:
            config: SMTP configuration dict with SMTP_HOST, SMTP_PORT, etc.
        """
        self.config = config
        self.host = config.get("SMTP_HOST")
        self.port = int(config.get("SMTP_PORT", "587"))
        self.user = config.get("SMTP_USER")
        self.password = config.get("SMTP_PASSWORD")
        self.sender_email = config.get("SENDER_EMAIL")

    async def send_message(
        self,
        to_addr: str,
        subject: str,
        html_body: str,
        text_body: str,
        timeout_seconds: int = 10,
    ) -> str:
        """
        Send email via SMTP.

        Args:
            to_addr: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            timeout_seconds: SMTP connection timeout

        Returns:
            Message-ID string (RFC 5322)

        Raises:
            Exception: If SMTP send fails
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = to_addr
            msg["Date"] = formatdate(localtime=True)

            # Generate Message-ID
            import uuid
            message_id = f"<{uuid.uuid4()}@{self.host}>"
            msg["Message-ID"] = message_id

            # Attach plain text and HTML parts
            part_text = MIMEText(text_body, "plain")
            part_html = MIMEText(html_body, "html")
            msg.attach(part_text)
            msg.attach(part_html)

            # Send via SMTP
            async with aiosmtplib.SMTP(hostname=self.host, port=self.port, timeout=timeout_seconds) as smtp:
                await smtp.login(self.user, self.password)
                await smtp.send_message(msg)

            logger.info(f"Email sent to {to_addr} with Message-ID: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to send email to {to_addr}: {str(e)}")
            raise

    async def test_connection(self) -> bool:
        """
        Test SMTP connection with credentials.

        Returns:
            True if connection successful
        """
        try:
            async with aiosmtplib.SMTP(hostname=self.host, port=self.port, timeout=5) as smtp:
                await smtp.login(self.user, self.password)
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}")
            return False
