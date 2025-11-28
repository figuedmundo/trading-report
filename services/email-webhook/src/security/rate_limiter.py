"""Rate limiting enforcement engine.

Implements multi-level rate limiting with per-IP and global limits.
Supports authenticated request multiplier for valid signatures.
Returns metadata for response headers and logging.
"""

import time
from typing import Tuple, Dict, Any
from src.config import Config
from src.security.rate_limit_storage import RateLimitStorage


class RateLimiter:
    """Enforces rate limiting with per-IP minute/hour and global hour limits.

    Rate limit hierarchy (checked in order):
    1. Per-IP per-minute limit (default 5 requests/minute)
    2. Per-IP per-hour limit (default 50 requests/hour)
    3. Global per-hour limit (default 100 requests/hour)

    Authenticated requests (valid signature) get 5x multiplier on all limits.
    """

    def __init__(self, config: Config = None, storage: RateLimitStorage = None):
        """Initialize rate limiter with configuration.

        Args:
            config: Config instance (uses default if not provided)
            storage: RateLimitStorage instance (creates new if not provided)
        """
        self.config = config or Config()
        self.storage = storage or RateLimitStorage()

    def check_rate_limit(
        self,
        ip_address: str,
        authenticated: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limits.

        Checks limits in order and returns on first violation.
        Increments counters only if request passes all checks.

        Args:
            ip_address: Client IP address
            authenticated: Whether request has valid signature (5x multiplier)

        Returns:
            Tuple of (allowed: bool, metadata: dict)
            metadata contains:
            - allowed: bool
            - remaining: int (requests remaining in most restrictive limit)
            - reset_time: float (Unix timestamp of next limit reset)
            - limit_type: str (which limit would be exceeded: 'minute', 'hour', 'global')
            - reset_seconds: int (seconds until limit resets)
        """
        # Apply authenticated multiplier
        multiplier = self.config.rate_limit_authenticated_multiplier if authenticated else 1

        # Get effective limits
        per_ip_minute_limit = self.config.rate_limit_per_ip_minute * multiplier
        per_ip_hour_limit = self.config.rate_limit_per_ip_hour * multiplier
        global_hour_limit = self.config.rate_limit_global_hour * multiplier

        # Check per-IP minute limit
        minute_remaining = self.storage.get_remaining(ip_address, 'minute', per_ip_minute_limit)
        if minute_remaining <= 0:
            reset_time = self.storage.get_reset_time(ip_address, 'minute')
            return False, {
                'allowed': False,
                'remaining': 0,
                'reset_time': reset_time,
                'reset_seconds': max(0, int(reset_time - time.time())),
                'limit_type': 'per_ip_minute',
            }

        # Check per-IP hour limit
        hour_remaining = self.storage.get_remaining(ip_address, 'hour', per_ip_hour_limit)
        if hour_remaining <= 0:
            reset_time = self.storage.get_reset_time(ip_address, 'hour')
            return False, {
                'allowed': False,
                'remaining': 0,
                'reset_time': reset_time,
                'reset_seconds': max(0, int(reset_time - time.time())),
                'limit_type': 'per_ip_hour',
            }

        # Check global hour limit
        global_remaining = self.storage.get_global_remaining(global_hour_limit)
        if global_remaining <= 0:
            reset_time = self.storage.get_global_reset_time()
            return False, {
                'allowed': False,
                'remaining': 0,
                'reset_time': reset_time,
                'reset_seconds': max(0, int(reset_time - time.time())),
                'limit_type': 'global_hour',
            }

        # All limits passed - increment counters
        self.storage.increment_counter(ip_address, 'minute')
        self.storage.increment_counter(ip_address, 'hour')
        global_count = self.storage.increment_global_counter()

        # Return success with remaining from most restrictive limit
        minute_remaining_after = self.storage.get_remaining(ip_address, 'minute', per_ip_minute_limit)
        hour_remaining_after = self.storage.get_remaining(ip_address, 'hour', per_ip_hour_limit)
        global_remaining_after = self.storage.get_global_remaining(global_hour_limit)

        # Most restrictive remaining is the minimum
        min_remaining = min(minute_remaining_after, hour_remaining_after, global_remaining_after)

        # Reset time for most restrictive limit
        minute_reset = self.storage.get_reset_time(ip_address, 'minute')
        hour_reset = self.storage.get_reset_time(ip_address, 'hour')
        global_reset = self.storage.get_global_reset_time()

        # Find which limit is most restrictive (earliest reset time)
        resets = [
            (minute_reset, 'per_ip_minute'),
            (hour_reset, 'per_ip_hour'),
            (global_reset, 'global_hour'),
        ]
        reset_time, limit_type = min(resets, key=lambda x: x[0])

        return True, {
            'allowed': True,
            'remaining': min_remaining,
            'reset_time': reset_time,
            'reset_seconds': max(0, int(reset_time - time.time())),
            'limit_type': limit_type,
            'per_ip_minute_remaining': minute_remaining_after,
            'per_ip_hour_remaining': hour_remaining_after,
            'global_hour_remaining': global_remaining_after,
        }

    def get_counters_for_ip(self, ip_address: str) -> Dict[str, Any]:
        """Get current rate limit counters for an IP (for debugging).

        Args:
            ip_address: Client IP address

        Returns:
            Dict with current counter values
        """
        return self.storage.get_all_counters().get(ip_address, {})
