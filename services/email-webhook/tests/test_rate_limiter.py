"""Tests for rate limiting engine.

Tests the rate limiter, storage, and ban manager components.
Verifies correct enforcement of per-IP and global limits.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock
from src.config import Config
from src.security.rate_limit_storage import RateLimitStorage
from src.security.rate_limiter import RateLimiter
from src.security.ban_manager import BanManager


class TestRateLimitStorage:
    """Tests for RateLimitStorage class."""

    def test_increment_counter_minute_window(self):
        """Test incrementing per-minute counter."""
        storage = RateLimitStorage()

        # First increment should return 1
        count = storage.increment_counter('192.168.1.1', 'minute')
        assert count == 1

        # Second increment should return 2
        count = storage.increment_counter('192.168.1.1', 'minute')
        assert count == 2

        # Third IP should start at 1
        count = storage.increment_counter('192.168.1.2', 'minute')
        assert count == 1

    def test_increment_counter_hour_window(self):
        """Test incrementing per-hour counter."""
        storage = RateLimitStorage()

        # First increment should return 1
        count = storage.increment_counter('192.168.1.1', 'hour')
        assert count == 1

        # Second increment should return 2
        count = storage.increment_counter('192.168.1.1', 'hour')
        assert count == 2

    def test_increment_counter_window_reset(self):
        """Test that windows reset after expiration."""
        storage = RateLimitStorage()

        # Increment minute counter
        storage.increment_counter('192.168.1.1', 'minute')

        # Modify internal state to simulate time passage
        entry = storage._storage['192.168.1.1']
        entry['minute_start'] = time.time() - 61  # 61 seconds ago

        # Next increment should reset and return 1
        count = storage.increment_counter('192.168.1.1', 'minute')
        assert count == 1

    def test_get_remaining(self):
        """Test getting remaining requests."""
        storage = RateLimitStorage()
        limit = 5

        # Before any requests, should have full limit
        remaining = storage.get_remaining('192.168.1.1', 'minute', limit)
        assert remaining == 5

        # After one request, should have 4 remaining
        storage.increment_counter('192.168.1.1', 'minute')
        remaining = storage.get_remaining('192.168.1.1', 'minute', limit)
        assert remaining == 4

        # After five requests, should have 0 remaining
        for _ in range(4):
            storage.increment_counter('192.168.1.1', 'minute')
        remaining = storage.get_remaining('192.168.1.1', 'minute', limit)
        assert remaining == 0

    def test_global_counter(self):
        """Test global hourly counter."""
        storage = RateLimitStorage()

        # Increment from multiple IPs
        storage.increment_global_counter()
        storage.increment_global_counter()

        # Check global remaining
        remaining = storage.get_global_remaining(100)
        assert remaining == 98

    def test_get_reset_time(self):
        """Test getting reset time for windows."""
        storage = RateLimitStorage()

        storage.increment_counter('192.168.1.1', 'minute')
        reset_time = storage.get_reset_time('192.168.1.1', 'minute')

        # Reset should be approximately 60 seconds from now
        now = time.time()
        assert 59 < (reset_time - now) < 61

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        storage = RateLimitStorage()

        # Add some entries
        storage.increment_counter('192.168.1.1', 'minute')
        storage.increment_counter('192.168.1.2', 'minute')

        # Modify internal state to make one expired
        entry = storage._storage['192.168.1.1']
        entry['last_request'] = time.time() - 7200  # 2 hours ago

        # Cleanup with 3600 second TTL should remove the old one
        removed = storage.cleanup_expired(ttl_seconds=3600)
        assert removed == 1

        # The fresh entry should still be there
        remaining = storage.get_remaining('192.168.1.2', 'minute', 5)
        assert remaining == 4

    def test_cleanup_expired_invalid_window(self):
        """Test that invalid windows raise ValueError."""
        storage = RateLimitStorage()

        with pytest.raises(ValueError):
            storage.increment_counter('192.168.1.1', 'invalid')

        with pytest.raises(ValueError):
            storage.get_remaining('192.168.1.1', 'invalid', 5)

        with pytest.raises(ValueError):
            storage.get_reset_time('192.168.1.1', 'invalid')


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_per_ip_minute_limit(self):
        """Test per-IP per-minute rate limit enforcement."""
        config = Config()
        config.rate_limit_per_ip_minute = 5
        config.rate_limit_per_ip_hour = 50
        config.rate_limit_global_hour = 100

        limiter = RateLimiter(config=config)

        # First 5 requests should be allowed
        for i in range(5):
            allowed, metadata = limiter.check_rate_limit('192.168.1.1')
            assert allowed is True

        # Sixth request should be denied
        allowed, metadata = limiter.check_rate_limit('192.168.1.1')
        assert allowed is False
        assert metadata['limit_type'] == 'per_ip_minute'
        assert metadata['remaining'] == 0

    def test_per_ip_hour_limit(self):
        """Test per-IP per-hour rate limit enforcement."""
        config = Config()
        config.rate_limit_per_ip_minute = 1000  # Very high
        config.rate_limit_per_ip_hour = 3
        config.rate_limit_global_hour = 1000

        limiter = RateLimiter(config=config)

        # First 3 requests should be allowed
        for i in range(3):
            allowed, metadata = limiter.check_rate_limit('192.168.1.1')
            assert allowed is True

        # Fourth request should be denied (hour limit)
        allowed, metadata = limiter.check_rate_limit('192.168.1.1')
        assert allowed is False
        assert metadata['limit_type'] == 'per_ip_hour'

    def test_global_hour_limit(self):
        """Test global per-hour rate limit enforcement."""
        config = Config()
        config.rate_limit_per_ip_minute = 1000
        config.rate_limit_per_ip_hour = 1000
        config.rate_limit_global_hour = 3

        limiter = RateLimiter(config=config)

        # First 3 requests from any IPs should be allowed
        for i in range(3):
            allowed, metadata = limiter.check_rate_limit(f'192.168.1.{i}')
            assert allowed is True

        # Fourth request should be denied (global limit)
        allowed, metadata = limiter.check_rate_limit('10.0.0.1')
        assert allowed is False
        assert metadata['limit_type'] == 'global_hour'

    def test_authenticated_multiplier(self):
        """Test 5x multiplier for authenticated requests."""
        config = Config()
        config.rate_limit_per_ip_minute = 5
        config.rate_limit_per_ip_hour = 50
        config.rate_limit_global_hour = 100
        config.rate_limit_authenticated_multiplier = 5

        limiter = RateLimiter(config=config)

        # Unauthenticated: limit is 5
        for i in range(5):
            allowed, metadata = limiter.check_rate_limit('192.168.1.1', authenticated=False)
            assert allowed is True

        allowed, metadata = limiter.check_rate_limit('192.168.1.1', authenticated=False)
        assert allowed is False

        # Clear storage for authenticated test
        limiter.storage.clear()

        # Authenticated: limit is 25 (5 * 5)
        for i in range(25):
            allowed, metadata = limiter.check_rate_limit('192.168.1.2', authenticated=True)
            assert allowed is True

        allowed, metadata = limiter.check_rate_limit('192.168.1.2', authenticated=True)
        assert allowed is False

    def test_different_ips_independent(self):
        """Test that different IPs have independent limits."""
        config = Config()
        config.rate_limit_per_ip_minute = 3

        limiter = RateLimiter(config=config)

        # First IP hits limit
        for i in range(3):
            limiter.check_rate_limit('192.168.1.1')

        allowed, _ = limiter.check_rate_limit('192.168.1.1')
        assert allowed is False

        # Second IP should still have requests available
        allowed, _ = limiter.check_rate_limit('192.168.1.2')
        assert allowed is True

    def test_reset_time_returned(self):
        """Test that reset time is provided in metadata."""
        config = Config()
        limiter = RateLimiter(config=config)

        allowed, metadata = limiter.check_rate_limit('192.168.1.1')
        assert allowed is True
        assert 'reset_time' in metadata
        assert 'reset_seconds' in metadata
        assert metadata['reset_seconds'] > 0


class TestBanManager:
    """Tests for BanManager class."""

    def test_record_failure(self):
        """Test recording failure attempts."""
        manager = BanManager()

        manager.record_failure('192.168.1.1')

        # Check failure count
        count = manager.get_failure_count('192.168.1.1')
        assert count == 1

        manager.record_failure('192.168.1.1')
        count = manager.get_failure_count('192.168.1.1')
        assert count == 2

    def test_should_ban_ip(self):
        """Test ban threshold detection."""
        config = Config()
        config.rate_limit_ban_threshold = 3

        manager = BanManager(config=config)

        # Record failures below threshold
        for i in range(2):
            manager.record_failure('192.168.1.1')

        assert manager.should_ban_ip('192.168.1.1') is False

        # Record one more to exceed threshold
        manager.record_failure('192.168.1.1')
        assert manager.should_ban_ip('192.168.1.1') is True

    def test_ban_ip(self):
        """Test banning an IP."""
        manager = BanManager()

        manager.ban_ip('192.168.1.1', 'Too many failed attempts')

        assert manager.is_ip_banned('192.168.1.1') is True

    def test_ban_expiry(self):
        """Test that bans expire after duration."""
        config = Config()
        config.rate_limit_ban_duration_hours = 0.0001  # Very short for testing (0.36 seconds)

        manager = BanManager(config=config)
        manager.ban_ip('192.168.1.1', 'Test ban')

        # Should be banned
        assert manager.is_ip_banned('192.168.1.1') is True

        # Wait for ban to expire
        time.sleep(0.5)

        # Should no longer be banned
        assert manager.is_ip_banned('192.168.1.1') is False

    def test_unban_ip(self):
        """Test manual unbanning."""
        manager = BanManager()

        manager.ban_ip('192.168.1.1', 'Test ban')
        assert manager.is_ip_banned('192.168.1.1') is True

        # Unban it
        result = manager.unban_ip('192.168.1.1')
        assert result is True
        assert manager.is_ip_banned('192.168.1.1') is False

        # Unbanning non-existent ban returns False
        result = manager.unban_ip('192.168.1.2')
        assert result is False

    def test_cleanup_expired_bans(self):
        """Test cleanup of expired bans."""
        config = Config()
        config.rate_limit_ban_duration_hours = 0.0001

        manager = BanManager(config=config)

        manager.ban_ip('192.168.1.1', 'Test ban')
        manager.ban_ip('192.168.1.2', 'Test ban')

        # Both should be banned
        assert manager.is_ip_banned('192.168.1.1') is True
        assert manager.is_ip_banned('192.168.1.2') is True

        # Wait for expiry
        time.sleep(0.5)

        # Cleanup should remove both
        removed = manager.cleanup_expired_bans()
        assert removed == 2

        # Both should no longer be banned
        assert manager.is_ip_banned('192.168.1.1') is False
        assert manager.is_ip_banned('192.168.1.2') is False

    def test_failure_window_expiry(self):
        """Test that failures expire after 5 minutes."""
        manager = BanManager()

        manager.record_failure('192.168.1.1')

        # Simulate time passage by modifying internal state
        entry = manager._failures['192.168.1.1']
        entry['first_attempt'] = time.time() - 301  # 301 seconds ago

        # Check if should ban (should be false due to window expiry)
        assert manager.should_ban_ip('192.168.1.1') is False

        # Failure count should reset
        assert manager.get_failure_count('192.168.1.1') == 0

    def test_get_all_bans(self):
        """Test retrieving all current bans."""
        manager = BanManager()

        manager.ban_ip('192.168.1.1', 'Reason 1')
        manager.ban_ip('192.168.1.2', 'Reason 2')

        all_bans = manager.get_all_bans()
        assert len(all_bans) == 2
        assert '192.168.1.1' in all_bans
        assert '192.168.1.2' in all_bans
        assert all_bans['192.168.1.1']['reason'] == 'Reason 1'
