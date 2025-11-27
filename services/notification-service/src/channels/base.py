"""
Base Channel abstract class for notification channels.

Defines the interface that all channel implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.utils.rate_limiter import TokenBucket


class Channel(ABC):
    """Abstract base class for notification channels."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize channel with name and configuration.

        Args:
            name: Channel name (email, telegram, sms, etc.)
            config: Channel-specific configuration dict
        """
        self.name = name
        self.config = config
        self.rate_limiter: Optional[TokenBucket] = None

    @abstractmethod
    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        """
        Send message to recipient via this channel.

        Args:
            message: Message to send
            recipient: Recipient address/ID (email, chat_id, phone, etc.)

        Returns:
            {
                'success': bool,
                'external_id': str (optional, email Message-ID or Telegram message_id),
                'latency_ms': int,
                'error_code': str (optional, if failed),
                'error_message': str (optional, if failed)
            }
        """
        pass

    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """
        Validate recipient format for this channel.

        Args:
            recipient: Recipient to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present.

        Returns:
            True if valid, False otherwise
        """
        pass

    def get_channel_status(self) -> Dict[str, Any]:
        """
        Return channel status: enabled, rate_limit, tokens available, etc.

        Returns:
            Dict with channel status information
        """
        return {
            "name": self.name,
            "enabled": True,
            "rate_limit": self.config.get("rate_limit_per_hour"),
            "tokens_available": self.rate_limiter.get_tokens_available() if self.rate_limiter else 0,
        }

    async def check_rate_limit(self) -> bool:
        """
        Check if channel is rate limited; return True if can proceed.

        Returns:
            True if can send, False if rate limited
        """
        if not self.rate_limiter:
            return True
        return await self.rate_limiter.try_consume(1)
