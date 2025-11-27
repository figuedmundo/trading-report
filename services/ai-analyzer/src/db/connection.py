"""
Async PostgreSQL connection pool management.

Provides connection pooling and transaction handling for database operations.
"""

import asyncpg
from typing import Optional
from contextlib import asynccontextmanager
from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> asyncpg.Pool:
    """
    Initialize PostgreSQL connection pool.

    Returns:
        asyncpg.Pool connection pool

    Raises:
        DatabaseError: If connection fails
    """
    global _pool

    if _pool is not None:
        return _pool

    config = get_config()
    database_url = config.database_url

    if not database_url:
        raise DatabaseError(
            "DATABASE_URL not configured",
            context={"missing_var": "DATABASE_URL"}
        )

    try:
        logger.info("Initializing database connection pool")
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20,
            command_timeout=10,
        )
        logger.info("Database connection pool initialized successfully")
        return _pool

    except Exception as e:
        raise DatabaseError(
            f"Failed to initialize database connection pool: {str(e)}",
            context={"error": str(e)}
        )


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _pool

    if _pool is not None:
        logger.info("Closing database connection pool")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


def get_db_pool() -> asyncpg.Pool:
    """
    Get the current connection pool.

    Returns:
        asyncpg.Pool connection pool

    Raises:
        DatabaseError: If pool not initialized
    """
    global _pool

    if _pool is None:
        raise DatabaseError(
            "Database connection pool not initialized",
            context={"pool": "uninitialized"}
        )

    return _pool


@asynccontextmanager
async def get_db_connection():
    """
    Get a database connection from the pool.

    Usage:
        async with get_db_connection() as conn:
            await conn.execute(...)

    Yields:
        asyncpg connection

    Raises:
        DatabaseError: If connection acquisition fails
    """
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            yield conn
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to acquire database connection: {str(e)}",
            context={"error": str(e)}
        )
