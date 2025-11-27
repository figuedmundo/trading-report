"""
Telegram Bot API client for async message delivery.

Handles Telegram API connections and message sending.
"""

from typing import Dict, Any
import httpx
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TelegramError(Exception):
    """Telegram API error."""

    def __init__(self, message: str, error_code: str = "TELEGRAM_ERROR"):
        """Initialize Telegram error."""
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class TelegramClient:
    """Telegram Bot API client for sending messages."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Telegram client.

        Args:
            config: Telegram configuration dict with TELEGRAM_BOT_TOKEN
        """
        self.config = config
        self.bot_token = config.get("TELEGRAM_BOT_TOKEN")
        self.api_base = "https://api.telegram.org"

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        timeout_seconds: int = 5,
    ) -> str:
        """
        Send message via Telegram Bot API.

        Args:
            chat_id: Telegram chat ID (recipient)
            text: Message text
            parse_mode: Message parse mode (HTML, Markdown)
            timeout_seconds: API timeout

        Returns:
            Telegram message_id

        Raises:
            TelegramError: If API call fails
        """
        try:
            url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }

            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            result = response.json()

            if not result.get("ok"):
                error_msg = result.get("description", "Unknown error")
                raise TelegramError(f"Telegram API error: {error_msg}")

            message_id = str(result["result"]["message_id"])
            logger.info(f"Telegram message sent to {chat_id} with ID: {message_id}")
            return message_id

        except httpx.HTTPError as e:
            logger.error(f"Telegram API HTTP error: {str(e)}")
            raise TelegramError(f"HTTP error: {str(e)}", error_code="TELEGRAM_HTTP_ERROR")

        except Exception as e:
            logger.error(f"Telegram API error: {str(e)}")
            raise TelegramError(str(e))

    async def test_connection(self) -> bool:
        """
        Test Telegram bot token validity.

        Returns:
            True if bot token valid
        """
        try:
            url = f"{self.api_base}/bot{self.bot_token}/getMe"

            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                logger.info(f"Telegram bot verified: {result['result']['username']}")
                return True
            else:
                logger.error(f"Telegram bot verification failed: {result.get('description')}")
                return False

        except Exception as e:
            logger.error(f"Telegram bot verification error: {str(e)}")
            return False
