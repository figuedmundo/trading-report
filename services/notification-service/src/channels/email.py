"""
Email channel implementation with SMTP integration.

Handles email delivery via SMTP servers.
"""

import re
import time
from typing import Dict, Any
from src.channels.base import Channel
from src.utils.logger import get_logger
from src.channels.smtp_client import SMTPClient

logger = get_logger(__name__)


class EmailChannel(Channel):
    """SMTP email delivery channel."""

    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        """
        Send email via SMTP.

        Args:
            message: Message to send (HTML content)
            recipient: Recipient email address

        Returns:
            Result dict with success status and details
        """
        start_time = time.time()

        # Validate recipient email
        if not self.validate_recipient(recipient):
            return {
                "success": False,
                "external_id": None,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error_code": "INVALID_EMAIL",
                "error_message": f"Invalid email address: {recipient}",
            }

        try:
            # Send via SMTP
            smtp_client = SMTPClient(self.config)
            message_id = await smtp_client.send_message(
                to_addr=recipient,
                subject="Trading Analysis Report",
                html_body=message,
                text_body=self._html_to_text(message),
                timeout_seconds=int(self.config.get("smtp_timeout_seconds", "10")),
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "external_id": message_id,
                "latency_ms": latency_ms,
                "error_code": None,
                "error_message": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_code = getattr(e, "smtp_code", "SMTP_ERROR")

            return {
                "success": False,
                "external_id": None,
                "latency_ms": latency_ms,
                "error_code": str(error_code),
                "error_message": str(e),
            }

    def validate_recipient(self, recipient: str) -> bool:
        """
        Validate email format using regex.

        Args:
            recipient: Email address to validate

        Returns:
            True if valid email format
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, recipient))

    def validate_config(self) -> bool:
        """
        Check SMTP configuration is present.

        Returns:
            True if required SMTP config present
        """
        required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]
        return all(key in self.config for key in required)

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML to plain text (simple version).

        Args:
            html: HTML content

        Returns:
            Plain text version
        """
        # Simple regex-based conversion
        # Remove script tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove style tags
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text
