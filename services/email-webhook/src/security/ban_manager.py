"""IP ban manager with in-memory tracking and database persistence.

Tracks failed authentication attempts and manages IP bans.
Syncs ban list to database every 5 minutes for persistence across restarts.
"""

import time
from collections import OrderedDict
from typing import Dict, List, Optional, Any
import threading
import asyncio
from src.config import Config


class BanManager:
    """Manages IP bans with failure tracking and database persistence.

    Tracks two separate data structures:
    1. Failures: {ip: {attempt_count, first_attempt}} - for threshold detection
    2. Bans: {ip: {banned_until, reason, attempt_count}} - for enforcement

    An IP is banned when it exceeds failure threshold within 5-minute window.
    Ban list is synced to database every 5 minutes (default) for persistence.
    """

    def __init__(self, config: Config = None, db_pool: Any = None):
        """Initialize ban manager.

        Args:
            config: Config instance (uses default if not provided)
            db_pool: asyncpg connection pool for database operations
        """
        self.config = config or Config()
        self.db_pool = db_pool

        # Track failed attempts per IP: {ip: {attempt_count, first_attempt}}
        self._failures: OrderedDict = OrderedDict()

        # Track banned IPs: {ip: {banned_until, reason, attempt_count}}
        self._bans: OrderedDict = OrderedDict()

        self._lock = threading.RLock()
        self._last_db_sync = 0

    def record_failure(self, ip_address: str) -> None:
        """Record a failed authentication attempt for an IP.

        Increments failure counter. If IP hasn't failed before, initializes
        with current timestamp for 5-minute window calculation.

        Args:
            ip_address: Client IP address
        """
        current_time = time.time()

        with self._lock:
            if ip_address not in self._failures:
                self._failures[ip_address] = {
                    'attempt_count': 0,
                    'first_attempt': current_time,
                }

            entry = self._failures[ip_address]
            entry['attempt_count'] += 1

    def should_ban_ip(self, ip_address: str) -> bool:
        """Check if IP should be banned based on failure threshold.

        IP is banned if it has exceeded RATE_LIMIT_BAN_THRESHOLD failed attempts
        within the last 5 minutes.

        Args:
            ip_address: Client IP address

        Returns:
            True if IP should be banned, False otherwise
        """
        current_time = time.time()
        failure_window = 5 * 60  # 5 minutes

        with self._lock:
            if ip_address not in self._failures:
                return False

            entry = self._failures[ip_address]
            time_since_first = current_time - entry['first_attempt']

            # If first attempt is outside 5-minute window, reset counter
            if time_since_first > failure_window:
                del self._failures[ip_address]
                return False

            # Check if attempt count exceeds threshold
            return entry['attempt_count'] >= self.config.rate_limit_ban_threshold

    def ban_ip(self, ip_address: str, reason: str) -> None:
        """Ban an IP address immediately.

        Adds IP to ban list with expiry time and syncs to database.

        Args:
            ip_address: Client IP address to ban
            reason: Reason for ban (logged for auditing)
        """
        current_time = time.time()
        ban_duration_seconds = self.config.rate_limit_ban_duration_hours * 3600
        banned_until = current_time + ban_duration_seconds

        with self._lock:
            # Get attempt count for context
            attempt_count = 0
            if ip_address in self._failures:
                attempt_count = self._failures[ip_address]['attempt_count']

            # Add to ban list
            self._bans[ip_address] = {
                'banned_until': banned_until,
                'reason': reason,
                'attempt_count': attempt_count,
                'banned_at': current_time,
            }

            # Trigger database sync (will happen in background)
            self._last_db_sync = 0  # Force sync on next cleanup

    def is_ip_banned(self, ip_address: str) -> bool:
        """Check if an IP address is currently banned.

        Also removes expired bans from tracking.

        Args:
            ip_address: Client IP address

        Returns:
            True if IP is banned and ban hasn't expired, False otherwise
        """
        current_time = time.time()

        with self._lock:
            if ip_address not in self._bans:
                return False

            entry = self._bans[ip_address]
            banned_until = entry['banned_until']

            # Check if ban has expired
            if current_time > banned_until:
                del self._bans[ip_address]
                return False

            return True

    def unban_ip(self, ip_address: str) -> bool:
        """Manually unban an IP address.

        Removes from in-memory ban list. Manual admin action.

        Args:
            ip_address: Client IP address to unban

        Returns:
            True if IP was banned and has been unbanned, False if wasn't banned
        """
        with self._lock:
            if ip_address in self._bans:
                del self._bans[ip_address]
                return True
            return False

    def cleanup_expired_bans(self) -> int:
        """Remove expired bans from tracking.

        Called periodically to clean up bans that have expired naturally.

        Returns:
            Number of expired bans removed
        """
        current_time = time.time()
        removed_count = 0

        with self._lock:
            # Find expired bans
            expired_ips = [
                ip for ip, entry in self._bans.items()
                if current_time > entry['banned_until']
            ]

            # Remove expired bans
            for ip in expired_ips:
                del self._bans[ip]
                removed_count += 1

            # Also clean up old failure attempts (older than 5 minutes)
            failure_window = 5 * 60
            expired_failures = [
                ip for ip, entry in self._failures.items()
                if current_time - entry['first_attempt'] > failure_window
            ]
            for ip in expired_failures:
                del self._failures[ip]

        return removed_count

    async def sync_to_database(self) -> None:
        """Sync ban list to PostgreSQL for persistence.

        Runs every 5 minutes (SYNC_INTERVAL). Inserts or updates entries in
        ip_bans table. Should be called from background task.

        Only syncs if db_pool is configured.
        """
        if not self.db_pool:
            return

        current_time = time.time()
        sync_interval = 5 * 60  # 5 minutes

        # Skip if not enough time has passed since last sync
        if current_time - self._last_db_sync < sync_interval:
            return

        with self._lock:
            bans_snapshot = dict(self._bans)

        try:
            async with self.db_pool.acquire() as conn:
                # Insert or update all current bans
                for ip_address, ban_info in bans_snapshot.items():
                    await conn.execute(
                        """
                        INSERT INTO ip_bans (ip_address, banned_until, reason, attempt_count)
                        VALUES ($1, to_timestamp($2), $3, $4)
                        ON CONFLICT (ip_address) DO UPDATE
                        SET banned_until = to_timestamp($2),
                            reason = $3,
                            attempt_count = $4
                        """,
                        ip_address,
                        ban_info['banned_until'],
                        ban_info['reason'],
                        ban_info['attempt_count'],
                    )

        except Exception as e:
            # Log error but don't fail - bans stay in memory
            import logging
            logging.error(f"Failed to sync bans to database: {e}")

        self._last_db_sync = current_time

    async def load_from_database(self) -> None:
        """Load ban list from PostgreSQL on startup.

        Restores bans that were previously persisted.

        Only loads if db_pool is configured.
        """
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT ip_address, banned_until, reason, attempt_count
                    FROM ip_bans
                    WHERE banned_until > NOW()
                    """
                )

                with self._lock:
                    for row in rows:
                        # Convert TIMESTAMPTZ to Unix timestamp
                        banned_until = row['banned_until'].timestamp() if row['banned_until'] else time.time()

                        self._bans[row['ip_address']] = {
                            'banned_until': banned_until,
                            'reason': row['reason'],
                            'attempt_count': row['attempt_count'],
                            'banned_at': banned_until - (self.config.rate_limit_ban_duration_hours * 3600),
                        }

        except Exception as e:
            # Log error but continue - will rebuild from requests
            import logging
            logging.warning(f"Failed to load bans from database: {e}")

    def get_all_bans(self) -> Dict[str, Dict[str, Any]]:
        """Get all current bans (for monitoring/debugging).

        Returns:
            Dict of all IPs and their ban information
        """
        with self._lock:
            return dict(self._bans)

    def get_failure_count(self, ip_address: str) -> int:
        """Get current failure count for an IP.

        Args:
            ip_address: Client IP address

        Returns:
            Number of failures in current 5-minute window (0 if not tracked)
        """
        current_time = time.time()
        failure_window = 5 * 60

        with self._lock:
            if ip_address not in self._failures:
                return 0

            entry = self._failures[ip_address]

            # Check if still in window
            if current_time - entry['first_attempt'] > failure_window:
                return 0

            return entry['attempt_count']

    def clear(self) -> None:
        """Clear all bans and failures. Used for testing.

        WARNING: This should only be used in tests!
        """
        with self._lock:
            self._failures.clear()
            self._bans.clear()
            self._last_db_sync = 0
