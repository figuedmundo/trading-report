"""
Database connection pooling and management.

Handles PostgreSQL connection lifecycle using psycopg2 connection pooling.
Provides safe context managers for database operations.
"""

import psycopg2
from psycopg2 import pool
import logging
from typing import Optional
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config

logger = logging.getLogger(__name__)

# Global connection pool instance
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def init_connection_pool() -> None:
    """
    Initialize PostgreSQL connection pool.

    Should be called on application startup.
    Raises exception if connection cannot be established.
    """
    global _connection_pool

    try:
        config = get_config()
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=config.database_url,
        )
        logger.info("Database connection pool initialized")
    except psycopg2.Error as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        _connection_pool = None
        raise


def close_connection_pool() -> None:
    """
    Close all connections in the pool.

    Should be called on application shutdown.
    """
    global _connection_pool

    if _connection_pool is not None:
        try:
            _connection_pool.closeall()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
        finally:
            _connection_pool = None


def get_db_pool() -> Optional[pool.ThreadedConnectionPool]:
    """
    Get the current connection pool.

    Returns None if pool not initialized.
    """
    return _connection_pool


def get_db_connection():
    """
    Get a single database connection from the pool.

    Returns connection object that should be returned to pool via putconn().
    Raises exception if pool not initialized.
    """
    pool_instance = get_db_pool()
    if pool_instance is None:
        raise RuntimeError("Connection pool not initialized")
    return pool_instance.getconn()


def return_db_connection(conn) -> None:
    """
    Return a connection to the pool for reuse.

    Should be called after connection is no longer needed.
    """
    pool_instance = get_db_pool()
    if pool_instance is not None and conn is not None:
        try:
            pool_instance.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
