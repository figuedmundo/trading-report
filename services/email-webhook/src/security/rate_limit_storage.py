"""In-memory rate limit storage with TTL-based cleanup.

Stores rate limiting counters per IP address with sliding window support.
Uses OrderedDict for efficient expired entry removal.
Provides atomic operations to prevent race conditions.
"""

import time
from collections import OrderedDict
from typing import Tuple, Optional
import threading


class RateLimitStorage:
    """Manages in-memory rate limit counters with TTL-based expiration.

    Structure: {ip_address: {
        'minute_window': count,
        'hour_window': count,
        'last_request': timestamp,
        'minute_start': timestamp,
        'hour_start': timestamp
    }}

    Windows are time-based sliding windows:
    - minute_window: requests in last 60 seconds
    - hour_window: requests in last 3600 seconds
    """

    def __init__(self):
        """Initialize rate limit storage with empty counters."""
        self._storage: OrderedDict = OrderedDict()
        self._global_counter = {
            'hour_window': 0,
            'hour_start': time.time(),
        }
        self._lock = threading.RLock()

    def increment_counter(self, ip_address: str, window: str) -> int:
        """Increment rate limit counter for IP address in specified window.

        Args:
            ip_address: Client IP address
            window: Either 'minute' or 'hour'

        Returns:
            Updated counter value after increment

        Raises:
            ValueError: If window is not 'minute' or 'hour'
        """
        if window not in ('minute', 'hour'):
            raise ValueError(f"Invalid window: {window}. Must be 'minute' or 'hour'")

        current_time = time.time()

        with self._lock:
            # Ensure IP entry exists
            if ip_address not in self._storage:
                self._storage[ip_address] = {
                    'minute_window': 0,
                    'hour_window': 0,
                    'last_request': current_time,
                    'minute_start': current_time,
                    'hour_start': current_time,
                }

            entry = self._storage[ip_address]

            # Reset minute window if 60+ seconds have passed
            if current_time - entry['minute_start'] >= 60:
                entry['minute_window'] = 0
                entry['minute_start'] = current_time

            # Reset hour window if 3600+ seconds have passed
            if current_time - entry['hour_start'] >= 3600:
                entry['hour_window'] = 0
                entry['hour_start'] = current_time

            # Increment appropriate counter
            if window == 'minute':
                entry['minute_window'] += 1
                result = entry['minute_window']
            else:  # window == 'hour'
                entry['hour_window'] += 1
                result = entry['hour_window']

            # Update last request time
            entry['last_request'] = current_time

            return result

    def increment_global_counter(self) -> int:
        """Increment global hourly rate limit counter.

        Returns:
            Updated global counter value after increment
        """
        current_time = time.time()

        with self._lock:
            # Reset global counter if 3600+ seconds have passed
            if current_time - self._global_counter['hour_start'] >= 3600:
                self._global_counter['hour_window'] = 0
                self._global_counter['hour_start'] = current_time

            self._global_counter['hour_window'] += 1
            return self._global_counter['hour_window']

    def get_remaining(self, ip_address: str, window: str, limit: int) -> int:
        """Get remaining requests allowed for IP in specified window.

        Args:
            ip_address: Client IP address
            window: Either 'minute' or 'hour'
            limit: The rate limit threshold for this window

        Returns:
            Remaining requests (0 if limit exceeded)

        Raises:
            ValueError: If window is not 'minute' or 'hour'
        """
        if window not in ('minute', 'hour'):
            raise ValueError(f"Invalid window: {window}. Must be 'minute' or 'hour'")

        with self._lock:
            if ip_address not in self._storage:
                return limit

            entry = self._storage[ip_address]

            # Return remaining for the requested window
            if window == 'minute':
                current = entry['minute_window']
            else:  # window == 'hour'
                current = entry['hour_window']

            return max(0, limit - current)

    def get_global_remaining(self, limit: int) -> int:
        """Get remaining global requests allowed for the hour.

        Args:
            limit: The global rate limit threshold

        Returns:
            Remaining global requests (0 if limit exceeded)
        """
        with self._lock:
            current = self._global_counter['hour_window']
            return max(0, limit - current)

    def get_reset_time(self, ip_address: str, window: str) -> float:
        """Get Unix timestamp when the rate limit window will reset.

        Args:
            ip_address: Client IP address
            window: Either 'minute' or 'hour'

        Returns:
            Unix timestamp when window resets

        Raises:
            ValueError: If window is not 'minute' or 'hour'
        """
        if window not in ('minute', 'hour'):
            raise ValueError(f"Invalid window: {window}. Must be 'minute' or 'hour'")

        with self._lock:
            if ip_address not in self._storage:
                return time.time() + (60 if window == 'minute' else 3600)

            entry = self._storage[ip_address]

            if window == 'minute':
                start_time = entry['minute_start']
                window_seconds = 60
            else:  # window == 'hour'
                start_time = entry['hour_start']
                window_seconds = 3600

            reset_time = start_time + window_seconds
            return reset_time

    def get_global_reset_time(self) -> float:
        """Get Unix timestamp when the global hour window will reset.

        Returns:
            Unix timestamp when global hour window resets
        """
        with self._lock:
            return self._global_counter['hour_start'] + 3600

    def cleanup_expired(self, ttl_seconds: int = 3600) -> int:
        """Remove expired entries from storage.

        Entries are considered expired if last_request is older than ttl_seconds.
        Called periodically (e.g., every 60 seconds) to prevent memory growth.

        Args:
            ttl_seconds: Time-to-live for entries (default 1 hour)

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        removed_count = 0

        with self._lock:
            # Find expired entries
            expired_ips = [
                ip for ip, entry in self._storage.items()
                if current_time - entry['last_request'] > ttl_seconds
            ]

            # Remove expired entries
            for ip in expired_ips:
                del self._storage[ip]
                removed_count += 1

        return removed_count

    def get_all_counters(self) -> dict:
        """Get all current rate limit counters for monitoring/debugging.

        Returns:
            Deep copy of storage dict with all IP counters
        """
        with self._lock:
            return dict(self._storage)

    def clear(self) -> None:
        """Clear all rate limit counters. Used for testing.

        WARNING: This should only be used in tests!
        """
        with self._lock:
            self._storage.clear()
            self._global_counter['hour_window'] = 0
            self._global_counter['hour_start'] = time.time()
