"""Tests for IP allowlist functionality.

Tests cover:
- CIDR range matching
- Static IP range loading from environment variables
- Dynamic IP loading from database with caching
- Cache refresh mechanism
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import asyncpg

from src.security.ip_allowlist_manager import IPAllowlistManager
from src.db.ip_allowlist_repository import IPAllowlistRepository
from src.utils.ip_utils import is_ip_in_cidr, validate_cidr_range, validate_ip_address
from src.utils.exceptions import DatabaseError


class TestCIDRMatching:
    """Test CIDR range matching utility."""

    def test_ip_in_cidr_basic_match(self):
        """Test basic CIDR range matching - IP in range."""
        assert is_ip_in_cidr("192.168.1.5", "192.168.1.0/24") is True

    def test_ip_in_cidr_no_match(self):
        """Test CIDR range matching - IP not in range."""
        assert is_ip_in_cidr("192.168.2.5", "192.168.1.0/24") is False

    def test_ip_in_cidr_network_address(self):
        """Test CIDR range matching - network address."""
        assert is_ip_in_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_ip_in_cidr_broadcast_address(self):
        """Test CIDR range matching - broadcast address."""
        assert is_ip_in_cidr("192.168.1.255", "192.168.1.0/24") is True

    def test_ip_in_cidr_large_range(self):
        """Test CIDR range matching with larger CIDR block."""
        assert is_ip_in_cidr("149.72.50.100", "149.72.0.0/16") is True

    def test_ip_in_cidr_outside_large_range(self):
        """Test CIDR range matching - IP outside large range."""
        assert is_ip_in_cidr("149.73.50.100", "149.72.0.0/16") is False

    def test_ip_in_cidr_single_ip(self):
        """Test CIDR range matching with /32 (single IP)."""
        assert is_ip_in_cidr("10.0.0.1", "10.0.0.1/32") is True
        assert is_ip_in_cidr("10.0.0.2", "10.0.0.1/32") is False

    def test_ip_in_cidr_invalid_ip_address(self):
        """Test CIDR matching with invalid IP address."""
        with pytest.raises(ValueError):
            is_ip_in_cidr("invalid.ip.address", "192.168.1.0/24")

    def test_ip_in_cidr_invalid_cidr_range(self):
        """Test CIDR matching with invalid CIDR range."""
        with pytest.raises(ValueError):
            is_ip_in_cidr("192.168.1.5", "invalid/24")

    def test_validate_ip_address_valid(self):
        """Test IP address validation with valid IP."""
        assert validate_ip_address("192.168.1.5") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("255.255.255.255") is True

    def test_validate_ip_address_invalid(self):
        """Test IP address validation with invalid IP."""
        assert validate_ip_address("256.256.256.256") is False
        assert validate_ip_address("invalid") is False
        assert validate_ip_address("192.168.1") is False

    def test_validate_cidr_range_valid(self):
        """Test CIDR range validation with valid ranges."""
        assert validate_cidr_range("192.168.1.0/24") is True
        assert validate_cidr_range("149.72.0.0/16") is True
        assert validate_cidr_range("10.0.0.1/32") is True

    def test_validate_cidr_range_invalid(self):
        """Test CIDR range validation with invalid ranges."""
        assert validate_cidr_range("invalid/24") is False
        assert validate_cidr_range("192.168.1.0/33") is False
        assert validate_cidr_range("256.256.256.0/24") is False


class TestIPAllowlistRepository:
    """Test IP allowlist repository database operations."""

    @pytest.mark.asyncio
    async def test_get_enabled_ips_empty(self):
        """Test getting enabled IPs when none exist."""
        repo = IPAllowlistRepository()

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_enabled_ips()

            assert result == []
            mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_enabled_ips_with_data(self):
        """Test getting enabled IPs when they exist."""
        repo = IPAllowlistRepository()

        # Mock database rows
        mock_rows = [
            {"ip_address": "192.168.1.0/24"},
            {"ip_address": "10.0.0.0/8"},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_enabled_ips()

            assert result == ["192.168.1.0/24", "10.0.0.0/8"]
            mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_enabled_ips_database_error(self):
        """Test handling database error when getting IPs."""
        repo = IPAllowlistRepository()

        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = asyncpg.PostgresError("Connection failed")

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError):
                await repo.get_enabled_ips()

    @pytest.mark.asyncio
    async def test_add_ip_success(self):
        """Test adding a new IP to allowlist."""
        repo = IPAllowlistRepository()

        mock_row = {
            "id": "test-id",
            "ip_address": "192.168.1.0/24",
            "description": "Test subnet",
            "enabled": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_row

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.add_ip("192.168.1.0/24", "Test subnet")

            assert result["ip_address"] == "192.168.1.0/24"
            assert result["description"] == "Test subnet"
            assert result["enabled"] is True
            mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_ip_duplicate_error(self):
        """Test adding duplicate IP raises error."""
        repo = IPAllowlistRepository()

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = asyncpg.IntegrityConstraintViolationError("duplicate key", "statement")

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError):
                await repo.add_ip("192.168.1.0/24")

    @pytest.mark.asyncio
    async def test_disable_ip_success(self):
        """Test disabling an IP address."""
        repo = IPAllowlistRepository()

        mock_row = {
            "id": "test-id",
            "ip_address": "192.168.1.0/24",
            "enabled": False,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_row

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.disable_ip("192.168.1.0/24")

            assert result is True
            mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_disable_ip_not_found(self):
        """Test disabling non-existent IP."""
        repo = IPAllowlistRepository()

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.disable_ip("192.168.1.0/24")

            assert result is False

    @pytest.mark.asyncio
    async def test_enable_ip_success(self):
        """Test enabling an IP address."""
        repo = IPAllowlistRepository()

        mock_row = {
            "id": "test-id",
            "ip_address": "192.168.1.0/24",
            "enabled": True,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_row

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.enable_ip("192.168.1.0/24")

            assert result is True

    @pytest.mark.asyncio
    async def test_enable_ip_not_found(self):
        """Test enabling non-existent IP."""
        repo = IPAllowlistRepository()

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch("src.db.ip_allowlist_repository.get_db_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.enable_ip("192.168.1.0/24")

            assert result is False


class TestIPAllowlistManager:
    """Test IP allowlist manager with static and dynamic IPs."""

    @pytest.mark.asyncio
    async def test_initialize_with_static_ranges(self):
        """Test manager initialization with static IP ranges."""
        manager = IPAllowlistManager()

        # Mock the config attributes
        manager.config.mailgun_ip_ranges = "149.72.0.0/16,161.38.0.0/16"
        manager.config.sendgrid_ip_ranges = "168.245.0.0/16"
        manager.config.custom_allowed_ips = ""

        # Create an AsyncMock for get_enabled_ips
        async def mock_get_ips():
            return []

        with patch.object(manager, "repository") as mock_repo:
            mock_repo.get_enabled_ips = AsyncMock(return_value=[])
            await manager.initialize()

        assert len(manager.static_ranges) == 3
        assert "149.72.0.0/16" in manager.static_ranges
        assert "161.38.0.0/16" in manager.static_ranges
        assert "168.245.0.0/16" in manager.static_ranges

    @pytest.mark.asyncio
    async def test_initialize_with_dynamic_ips(self):
        """Test manager initialization loads dynamic IPs from database."""
        manager = IPAllowlistManager()

        dynamic_ips = ["10.0.0.0/8", "192.168.0.0/16"]

        manager.config.mailgun_ip_ranges = ""
        manager.config.sendgrid_ip_ranges = ""
        manager.config.custom_allowed_ips = ""

        with patch.object(manager, "repository") as mock_repo:
            mock_repo.get_enabled_ips = AsyncMock(return_value=dynamic_ips)
            await manager.initialize()

        assert manager.cached_dynamic_ips == set(dynamic_ips)
        assert manager.last_cache_refresh is not None

    @pytest.mark.asyncio
    async def test_refresh_cache(self):
        """Test cache refresh mechanism."""
        manager = IPAllowlistManager()

        dynamic_ips = ["10.0.0.0/8", "192.168.0.0/16"]

        with patch.object(manager, "repository") as mock_repo:
            mock_repo.get_enabled_ips = AsyncMock(return_value=dynamic_ips)
            await manager.refresh_cache()

        assert manager.cached_dynamic_ips == set(dynamic_ips)
        assert manager.last_cache_refresh is not None

    def test_is_ip_allowed_static_range(self):
        """Test IP allowance check with static ranges."""
        manager = IPAllowlistManager()
        manager.static_ranges = ["149.72.0.0/16"]
        manager.cached_dynamic_ips = set()

        assert manager.is_ip_allowed("149.72.50.100") is True
        assert manager.is_ip_allowed("149.73.50.100") is False

    def test_is_ip_allowed_dynamic_ips(self):
        """Test IP allowance check with dynamic IPs."""
        manager = IPAllowlistManager()
        manager.static_ranges = []
        manager.cached_dynamic_ips = {"192.168.1.0/24", "10.0.0.0/8"}

        assert manager.is_ip_allowed("192.168.1.5") is True
        assert manager.is_ip_allowed("10.0.0.1") is True
        assert manager.is_ip_allowed("172.16.0.1") is False

    def test_is_ip_allowed_both_static_and_dynamic(self):
        """Test IP allowance with both static and dynamic ranges."""
        manager = IPAllowlistManager()
        manager.static_ranges = ["149.72.0.0/16"]
        manager.cached_dynamic_ips = {"192.168.1.0/24"}

        assert manager.is_ip_allowed("149.72.50.100") is True
        assert manager.is_ip_allowed("192.168.1.5") is True
        assert manager.is_ip_allowed("172.16.0.1") is False

    def test_should_refresh_cache_new_manager(self):
        """Test cache refresh check for new manager."""
        manager = IPAllowlistManager()
        assert manager.should_refresh_cache() is True

    def test_should_refresh_cache_recent(self):
        """Test cache refresh check when recently refreshed."""
        manager = IPAllowlistManager()
        manager.last_cache_refresh = datetime.now()
        manager.cache_refresh_seconds = 300

        assert manager.should_refresh_cache() is False

    def test_should_refresh_cache_expired(self):
        """Test cache refresh check when refresh interval expired."""
        manager = IPAllowlistManager()
        manager.last_cache_refresh = datetime.now() - timedelta(seconds=301)
        manager.cache_refresh_seconds = 300

        assert manager.should_refresh_cache() is True

    def test_get_cache_status(self):
        """Test getting cache status."""
        manager = IPAllowlistManager()
        manager.static_ranges = ["149.72.0.0/16", "168.245.0.0/16"]
        manager.cached_dynamic_ips = {"192.168.1.0/24", "10.0.0.0/8"}
        manager.last_cache_refresh = datetime.now()

        status = manager.get_cache_status()

        assert status["static_ranges_count"] == 2
        assert status["cached_dynamic_ips_count"] == 2
        assert status["last_refresh"] is not None
        assert status["should_refresh"] is False

    @pytest.mark.asyncio
    async def test_cache_refresh_integration(self):
        """Test full cache refresh cycle."""
        manager = IPAllowlistManager()

        initial_ips = ["192.168.1.0/24"]
        updated_ips = ["192.168.1.0/24", "10.0.0.0/8"]

        with patch.object(manager, "repository") as mock_repo:
            # First refresh returns one IP
            mock_repo.get_enabled_ips = AsyncMock(return_value=initial_ips)
            await manager.refresh_cache()
            assert len(manager.cached_dynamic_ips) == 1

            # Second refresh returns updated list
            mock_repo.get_enabled_ips = AsyncMock(return_value=updated_ips)
            await manager.refresh_cache()
            assert len(manager.cached_dynamic_ips) == 2

    def test_is_ip_allowed_validates_order(self):
        """Test that IP validation checks static ranges first."""
        manager = IPAllowlistManager()
        manager.static_ranges = ["149.72.0.0/16"]
        manager.cached_dynamic_ips = {"10.0.0.0/8"}

        # Should match static range
        assert manager.is_ip_allowed("149.72.50.100") is True

        # Should match dynamic IP
        assert manager.is_ip_allowed("10.0.0.1") is True

        # Should not match either
        assert manager.is_ip_allowed("172.16.0.1") is False
