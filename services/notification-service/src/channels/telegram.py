"""
Telegram channel implementation with Bot API integration.

Handles Telegram message delivery via Bot API.
"""

import asyncio
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

            chunks = self._split_message(markdown_v2_message, 4000)

            telegram_client = TelegramClient(self.config)
            message_ids = []

            for i, chunk in enumerate(chunks):
                final_text = chunk
                if len(chunks) > 1:
                    header = f"*Message Part {i + 1}/{len(chunks)}*\n\n"
                    final_text = header + chunk

                msg_id = await telegram_client.send_message(
                    chat_id=recipient,
                    text=final_text,
                    parse_mode="MarkdownV2",
                    timeout_seconds=int(self.config.get("api_timeout_seconds", "10")),
                )
                message_ids.append(msg_id)
                if len(chunks) > 1:
                    await asyncio.sleep(0.5)

            latency_ms = int((time.time() - start_time) * 1000)
            external_id = (
                "|".join(message_ids) if len(message_ids) > 1 else message_ids[0]
            )

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
        return "TELEGRAM_BOT_TOKEN" in self.config and bool(
            self.config["TELEGRAM_BOT_TOKEN"]
        )

    @staticmethod
    def _split_message(message: str, max_length: int) -> List[str]:
        if len(message) <= max_length:
            return [message]

        chunks = []
        current_text = message

        while len(current_text) > max_length:
            split_idx = current_text.rfind("\n\n", 0, max_length)

            if split_idx == -1:
                split_idx = current_text.rfind("\n", 0, max_length)

            if split_idx == -1:
                split_idx = current_text.rfind(" ", 0, max_length)

            if split_idx == -1:
                split_idx = max_length

            chunks.append(current_text[:split_idx].strip())
            current_text = current_text[split_idx:].strip()

        if current_text:
            chunks.append(current_text)

        return chunks
