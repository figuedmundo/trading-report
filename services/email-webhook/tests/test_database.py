"""
Tests for Task Group 2: Environment Configuration & Database Connectivity

Tests database connection pooling, environment variable loading, and health checks
that verify database connectivity.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from main import app
    return TestClient(app)


class TestDatabaseConfiguration:
    """Test database environment configuration."""

    def test_database_url_configured(self):
        """Test that DATABASE_URL environment variable is loaded."""
        from config import get_config

        config = get_config()
        assert config.database_url is not None
        assert len(config.database_url) > 0

    def test_database_url_has_correct_format(self):
        """Test that DATABASE_URL follows PostgreSQL connection string format."""
        from config import get_config

        config = get_config()
        # Should start with postgresql:// or postgres://
        assert config.database_url.startswith("postgresql://") or config.database_url.startswith("postgres://")

    def test_rate_limit_configuration_defaults(self):
        """Test that rate limit configuration has sensible defaults."""
        from config import get_config

        config = get_config()
        assert config.rate_limit_per_second >= 1
        assert config.rate_limit_per_hour >= 100

    def test_log_level_configuration(self):
        """Test that log level configuration is set."""
        from config import get_config

        config = get_config()
        assert config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class TestConnectionPoolInitialization:
    """Test database connection pool initialization and lifecycle."""

    @patch("database.psycopg2.pool.ThreadedConnectionPool")
    @patch("database.get_config")
    def test_pool_initializes_with_min_max_connections(self, mock_get_config, mock_pool_class):
        """Test that connection pool initializes with correct min/max connections."""
        from database import init_connection_pool, get_db_pool, _connection_pool
        import database as db_module

        mock_config = MagicMock()
        mock_config.database_url = "postgresql://user:pass@localhost/db"
        mock_get_config.return_value = mock_config

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        # Clear and reinitialize
        db_module._connection_pool = None

        with patch.object(db_module, "_connection_pool", None):
            init_connection_pool()

            # Verify ThreadedConnectionPool was called with correct parameters
            mock_pool_class.assert_called_once()
            call_kwargs = mock_pool_class.call_args[1]
            assert call_kwargs.get("minconn") == 2
            assert call_kwargs.get("maxconn") == 10

    @patch("database.psycopg2.pool.ThreadedConnectionPool")
    @patch("database.get_config")
    def test_pool_creation_uses_database_url(self, mock_get_config, mock_pool_class):
        """Test that connection pool uses DATABASE_URL from config."""
        from database import init_connection_pool
        import database as db_module

        mock_config = MagicMock()
        mock_config.database_url = "postgresql://testuser:testpass@testhost:5432/testdb"
        mock_get_config.return_value = mock_config

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        db_module._connection_pool = None

        with patch.object(db_module, "_connection_pool", None):
            init_connection_pool()

            # Verify the database URL was passed to pool creation
            call_kwargs = mock_pool_class.call_args[1]
            assert call_kwargs.get("dsn") == "postgresql://testuser:testpass@testhost:5432/testdb"

    @patch("database.psycopg2.pool.ThreadedConnectionPool")
    @patch("database.get_config")
    def test_pool_connection_management(self, mock_get_config, mock_pool_class):
        """Test that connection pool manages connections correctly."""
        from database import get_db_pool, get_db_connection, return_db_connection, init_connection_pool
        import database as db_module

        mock_config = MagicMock()
        mock_config.database_url = "postgresql://user:pass@localhost/db"
        mock_get_config.return_value = mock_config

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db_module._connection_pool = None

        with patch.object(db_module, "_connection_pool", None):
            init_connection_pool()

            # Get a connection
            conn = get_db_connection()
            assert conn is not None
            mock_pool.getconn.assert_called()

            # Return the connection
            return_db_connection(conn)
            mock_pool.putconn.assert_called_with(conn)

    def test_get_db_pool_returns_none_before_initialization(self):
        """Test that get_db_pool returns None before pool is initialized."""
        from database import get_db_pool
        import database as db_module

        with patch.object(db_module, "_connection_pool", None):
            pool = get_db_pool()
            assert pool is None

    @patch("database.psycopg2.pool.ThreadedConnectionPool")
    @patch("database.get_config")
    def test_get_db_pool_returns_pool_after_initialization(self, mock_get_config, mock_pool_class):
        """Test that get_db_pool returns the pool after initialization."""
        from database import init_connection_pool, get_db_pool
        import database as db_module

        mock_config = MagicMock()
        mock_config.database_url = "postgresql://user:pass@localhost/db"
        mock_get_config.return_value = mock_config

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        db_module._connection_pool = None

        with patch.object(db_module, "_connection_pool", None):
            init_connection_pool()
            pool = get_db_pool()
            assert pool is not None


class TestDatabaseHealthCheck:
    """Test health check endpoint database connectivity verification."""

    def test_health_check_queries_database(self, client):
        """Test that health check endpoint executes a database query."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.close.return_value = None

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 200
            # Verify cursor.execute was called (database query)
            mock_cursor.execute.assert_called_once()

    def test_health_check_returns_connected_on_successful_query(self, client):
        """Test that health check returns database status as 'connected'."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.close.return_value = None

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["database"] == "connected"

    def test_health_check_returns_disconnected_on_query_failure(self, client):
        """Test that health check returns database status as 'disconnected' on error."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Connection refused")
        mock_cursor.close.return_value = None

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["database"] == "disconnected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
