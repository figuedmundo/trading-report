"""
Telegram channel implementation with Bot API integration.

Handles Telegram message delivery via Bot API.
"""

import time
from typing import Dict, Any, List
from src.channels.base import Channel
from src.utils.logger import get_logger
from src.channels.telegram_client import TelegramClient
import telegramify_markdown

logger = get_logger(__name__)


class TelegramChannel(Channel):
    """Telegram Bot API delivery channel."""

    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        """
        Send message via Telegram Bot API.

        Args:
            message: Message to send (Markdown format)
            recipient: Recipient Telegram chat ID

        Returns:
            Result dict with success status and details
        """
        start_time = time.time()

        # Validate recipient (must be numeric chat ID)
        if not self.validate_recipient(recipient):
            return {
                "success": False,
                "external_id": None,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error_code": "INVALID_CHAT_ID",
                "error_message": f"Invalid Telegram chat ID: {recipient}",
            }

        try:
            # Convert standard Markdown to Telegram MarkdownV2
            # This handles escaping and formatting automatically
            markdown_v2_message = telegramify_markdown.markdownify(message)

            # Split message if exceeds 4096 character limit
            # Note: Splitting MarkdownV2 is tricky; telegramify might help, or we rely on basic splitting
            # Ideally, the summary should fit.
            messages_to_send = self._split_message(markdown_v2_message, 4096)

            telegram_client = TelegramClient(self.config)
            message_ids = []

            for chunk in messages_to_send:
                msg_id = await telegram_client.send_message(
                    chat_id=recipient,
                    text=chunk,
                    parse_mode="MarkdownV2",
                    timeout_seconds=int(self.config.get("api_timeout_seconds", "5")),
                )
                message_ids.append(msg_id)

            latency_ms = int((time.time() - start_time) * 1000)
            external_id = "|".join(message_ids) if len(message_ids) > 1 else message_ids[0]

            return {
                "success": True,
                "external_id": external_id,
                "latency_ms": latency_ms,
                "error_code": None,
                "error_message": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_code = getattr(e, "error_code", "TELEGRAM_ERROR")

            return {
                "success": False,
                "external_id": None,
                "latency_ms": latency_ms,
                "error_code": str(error_code),
                "error_message": str(e),
            }

    def validate_recipient(self, recipient: str) -> bool:
        """
        Validate Telegram chat ID (numeric only).

        Args:
            recipient: Chat ID to validate

        Returns:
            True if valid numeric chat ID
        """
        try:
            int(recipient)
            return True
        except (ValueError, TypeError):
            return False

    def validate_config(self) -> bool:
        """
        Check Telegram bot token is present.

        Returns:
            True if TELEGRAM_BOT_TOKEN present
        """
        return "TELEGRAM_BOT_TOKEN" in self.config and bool(self.config["TELEGRAM_BOT_TOKEN"])

    @staticmethod
    def _split_message(message: str, max_length: int) -> List[str]:
        """
        Split message into chunks respecting max length and boundaries.

        Args:
            message: Message to split
            max_length: Maximum length per chunk (Telegram limit is 4096)

        Returns:
            List of message chunks, each <= max_length
        """
        if len(message) <= max_length:
            return [message]

        chunks = []
        current_chunk = ""

        # Try to split on paragraph boundaries (double newline)
        paragraphs = message.split("\n\n")

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_length:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk)

        # If any chunk still exceeds max_length, split on word boundaries
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_length:
                final_chunks.append(chunk)
            else:
                # Split on word boundaries
                words = chunk.split(" ")
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_length:
                        if current:
                            current += " "
                        current += word
                    else:
                        if current:
                            final_chunks.append(current)
                        current = word

                if current:
                    final_chunks.append(current)

        return final_chunks
