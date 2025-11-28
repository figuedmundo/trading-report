"""IP allowlist manager with hybrid static and dynamic IP support.

Manages IP whitelisting with static configuration (environment variables) and
dynamic configuration (database with caching).
"""

import asyncio
from typing import List, Set
from datetime import datetime, timedelta
from src.config import get_config
from src.db.ip_allowlist_repository import IPAllowlistRepository
from src.utils.logger import get_logger
from src.utils.ip_utils import is_ip_in_cidr, validate_cidr_range
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class IPAllowlistManager:
    """Manages IP allowlist with static and dynamic IPs."""

    def __init__(self):
        """Initialize IP allowlist manager."""
        self.config = get_config()
        self.repository = IPAllowlistRepository()

        # Static IP ranges loaded from environment variables
        self.static_ranges: List[str] = []

        # Cached dynamic IPs from database
        self.cached_dynamic_ips: Set[str] = set()

        # Timestamp of last cache refresh
        self.last_cache_refresh: datetime = None

        # Cache refresh interval in seconds
        self.cache_refresh_seconds = self.config.ip_allowlist_cache_refresh_seconds

    async def initialize(self) -> None:
        """Initialize the IP allowlist manager by loading static and dynamic IPs.

        This method should be called during application startup.
        """
        logger.info("Initializing IP allowlist manager")

        # Load static IP ranges from environment variables
        self._load_static_ranges()

        # Load dynamic IPs from database
        try:
            await self.refresh_cache()
        except DatabaseError as e:
            logger.warning(
                "Failed to load dynamic IPs from database, will retry on next refresh",
                extra={"error": str(e)}
            )
            # Don't raise here - allow service to start with only static IPs

        logger.info(
            "IP allowlist manager initialized",
            extra={
                "static_ranges_count": len(self.static_ranges),
                "cached_dynamic_ips_count": len(self.cached_dynamic_ips),
            }
        )

    def _load_static_ranges(self) -> None:
        """Load static IP ranges from environment variables."""
        self.static_ranges = []

        # Parse Mailgun ranges
        if self.config.mailgun_ip_ranges:
            ranges = [r.strip() for r in self.config.mailgun_ip_ranges.split(",") if r.strip()]
            for cidr_range in ranges:
                if validate_cidr_range(cidr_range):
                    self.static_ranges.append(cidr_range)
                else:
                    logger.warning(
                        "Invalid CIDR range in MAILGUN_IP_RANGES",
                        extra={"range": cidr_range}
                    )

        # Parse SendGrid ranges
        if self.config.sendgrid_ip_ranges:
            ranges = [r.strip() for r in self.config.sendgrid_ip_ranges.split(",") if r.strip()]
            for cidr_range in ranges:
                if validate_cidr_range(cidr_range):
                    self.static_ranges.append(cidr_range)
                else:
                    logger.warning(
                        "Invalid CIDR range in SENDGRID_IP_RANGES",
                        extra={"range": cidr_range}
                    )

        # Parse custom allowed IPs
        if self.config.custom_allowed_ips:
            ranges = [r.strip() for r in self.config.custom_allowed_ips.split(",") if r.strip()]
            for cidr_range in ranges:
                if validate_cidr_range(cidr_range):
                    self.static_ranges.append(cidr_range)
                else:
                    logger.warning(
                        "Invalid CIDR range in CUSTOM_ALLOWED_IPS",
                        extra={"range": cidr_range}
                    )

        logger.info(
            "Loaded static IP ranges",
            extra={"count": len(self.static_ranges), "ranges": self.static_ranges}
        )

    async def refresh_cache(self) -> None:
        """Refresh cached dynamic IPs from database.

        This method queries the database for all enabled IPs and updates
        the in-memory cache.
        """
        try:
            logger.info("Refreshing IP allowlist cache")
            ips = await self.repository.get_enabled_ips()
            self.cached_dynamic_ips = set(ips)
            self.last_cache_refresh = datetime.now()

            logger.info(
                "IP allowlist cache refreshed",
                extra={"cached_ips_count": len(self.cached_dynamic_ips)}
            )

        except DatabaseError as e:
            logger.error(
                "Failed to refresh IP allowlist cache",
                extra={"error": str(e)}
            )
            raise

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if an IP address is allowed.

        Validation order:
        1. Check static ranges first (O(n) scan of static ranges)
        2. Then check cached database IPs

        Args:
            ip_address: IP address to check

        Returns:
            True if IP is allowed, False otherwise
        """
        # Check static ranges first
        for cidr_range in self.static_ranges:
            try:
                if is_ip_in_cidr(ip_address, cidr_range):
                    logger.debug(
                        "IP allowed by static range",
                        extra={
                            "ip_address": ip_address,
                            "range": cidr_range,
                        }
                    )
                    return True
            except ValueError as e:
                logger.warning(
                    "Error checking IP against static range",
                    extra={
                        "ip_address": ip_address,
                        "range": cidr_range,
                        "error": str(e),
                    }
                )
                continue

        # Check cached dynamic IPs
        for cidr_range in self.cached_dynamic_ips:
            try:
                if is_ip_in_cidr(ip_address, cidr_range):
                    logger.debug(
                        "IP allowed by dynamic allowlist",
                        extra={
                            "ip_address": ip_address,
                            "range": cidr_range,
                        }
                    )
                    return True
            except ValueError as e:
                logger.warning(
                    "Error checking IP against dynamic allowlist",
                    extra={
                        "ip_address": ip_address,
                        "range": cidr_range,
                        "error": str(e),
                    }
                )
                continue

        logger.warning(
            "IP not allowed",
            extra={"ip_address": ip_address}
        )
        return False

    def should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed.

        Returns:
            True if cache refresh interval has passed
        """
        if self.last_cache_refresh is None:
            return True

        elapsed_seconds = (datetime.now() - self.last_cache_refresh).total_seconds()
        return elapsed_seconds >= self.cache_refresh_seconds

    def get_cache_status(self) -> dict:
        """Get current cache status.

        Returns:
            Dict with cache status information
        """
        elapsed_seconds = None
        if self.last_cache_refresh is not None:
            elapsed_seconds = (datetime.now() - self.last_cache_refresh).total_seconds()

        return {
            "static_ranges_count": len(self.static_ranges),
            "cached_dynamic_ips_count": len(self.cached_dynamic_ips),
            "last_refresh": self.last_cache_refresh.isoformat() if self.last_cache_refresh else None,
            "elapsed_seconds_since_refresh": elapsed_seconds,
            "should_refresh": self.should_refresh_cache(),
        }
