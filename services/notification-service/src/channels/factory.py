"""
Channel factory for dynamic channel instantiation.

Loads channels from database configuration and instantiates them.
"""

from typing import Dict, Optional
from src.channels.base import Channel
from src.channels.email import EmailChannel
from src.channels.telegram import TelegramChannel
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError
from src.utils.rate_limiter import TokenBucket
from src.config import get_config

logger = get_logger(__name__)


class ChannelFactory:
    """Factory for creating and managing notification channels."""

    def __init__(self):
        """Initialize channel factory."""
        self.channels: Dict[str, Channel] = {}

    async def load_channels_from_config(self) -> Dict[str, Channel]:
        """
        Load enabled channels from database configuration.

        Returns:
            Dict mapping channel_name -> Channel instance

        Raises:
            ConfigurationError: If channel config invalid
        """
        try:
            async with get_db_connection() as conn:
                # Query all enabled channel configurations
                query = """
                    SELECT DISTINCT channel_name
                    FROM channel_configurations
                    WHERE is_enabled = true
                    ORDER BY channel_name
                """
                enabled_channels = await conn.fetch(query)

            self.channels = {}

            for row in enabled_channels:
                channel_name = row["channel_name"]

                # Load all settings for this channel
                async with get_db_connection() as conn:
                    settings_query = """
                        SELECT setting_key, setting_value
                        FROM channel_configurations
                        WHERE channel_name = $1
                    """
                    settings_rows = await conn.fetch(settings_query, channel_name)

                # Build config dict
                channel_config = {row["setting_key"]: row["setting_value"] for row in settings_rows}

                # Add secrets from environment
                config = get_config()
                if channel_name == "email":
                    if config.smtp_host:
                        channel_config["SMTP_HOST"] = config.smtp_host
                    if config.smtp_port:
                        channel_config["SMTP_PORT"] = str(config.smtp_port)
                    if config.smtp_user:
                        channel_config["SMTP_USER"] = config.smtp_user
                    if config.smtp_password:
                        channel_config["SMTP_PASSWORD"] = config.smtp_password
                    if config.sender_email:
                        channel_config["SENDER_EMAIL"] = config.sender_email

                elif channel_name == "telegram":
                    if config.telegram_bot_token:
                        channel_config["TELEGRAM_BOT_TOKEN"] = config.telegram_bot_token
                    if config.telegram_chat_id:
                        channel_config["TELEGRAM_CHAT_ID"] = config.telegram_chat_id

                # Instantiate channel
                channel = self._instantiate_channel(channel_name, channel_config)
                self.channels[channel_name] = channel
                logger.info(f"Channel loaded: {channel_name}")

            return self.channels

        except Exception as e:
            logger.error(f"Failed to load channels from config: {str(e)}")
            raise ConfigurationError(f"Failed to load channels: {str(e)}")

    async def get_channel(self, channel_name: str) -> Optional[Channel]:
        """
        Get a loaded channel instance by name.

        Args:
            channel_name: Name of channel to retrieve

        Returns:
            Channel instance or None if not enabled
        """
        return self.channels.get(channel_name)

    async def reload_channels(self) -> None:
        """Reload channels from database configuration."""
        logger.info("Reloading channels from configuration")
        await self.load_channels_from_config()

    @staticmethod
    def _instantiate_channel(channel_name: str, config: Dict) -> Channel:
        """
        Instantiate a channel by name and config.

        Args:
            channel_name: Name of channel to instantiate
            config: Channel configuration dict

        Returns:
            Channel instance

        Raises:
            ConfigurationError: If channel type unknown or config invalid
        """
        channel_name_lower = channel_name.lower().strip()

        if channel_name_lower == "email":
            channel = EmailChannel(channel_name, config)
        elif channel_name_lower == "telegram":
            channel = TelegramChannel(channel_name, config)
        else:
            raise ConfigurationError(f"Unknown channel type: {channel_name}")

        # Validate channel config
        if not channel.validate_config():
            raise ConfigurationError(f"Invalid configuration for channel: {channel_name}")

        # Set up rate limiter based on channel type
        channel.rate_limiter = ChannelFactory._setup_rate_limiter(channel_name, config)

        logger.info(f"Channel instantiated: {channel_name}")
        return channel

    @staticmethod
    def _setup_rate_limiter(channel_name: str, config: Dict) -> Optional[TokenBucket]:
        """
        Set up rate limiter for channel.

        Args:
            channel_name: Channel name
            config: Channel configuration

        Returns:
            TokenBucket instance or None if no rate limiting
        """
        channel_name_lower = channel_name.lower().strip()

        if channel_name_lower == "email":
            # Default: 100 emails per hour
            rate_limit = int(config.get("rate_limit_per_hour", "100"))
            refill_rate = rate_limit / 3600  # per second
            return TokenBucket(capacity=rate_limit, refill_rate=refill_rate)

        elif channel_name_lower == "telegram":
            # Default: 30 messages per minute
            rate_limit = int(config.get("rate_limit_per_minute", "30"))
            refill_rate = rate_limit / 60  # per second
            return TokenBucket(capacity=rate_limit, refill_rate=refill_rate)

        return None
