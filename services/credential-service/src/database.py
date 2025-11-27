"""
Database connection pooling and credential repository operations.

Handles PostgreSQL connection lifecycle using psycopg2 connection pooling.
Provides functions for CRUD operations on credentials table.
"""

import psycopg2
from psycopg2 import pool, extras
import logging
from typing import Optional, List, Dict, Any
import sys
import os
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config
from encryption import encrypt, decrypt

logger = logging.getLogger(__name__)

# Global connection pool instance
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def init_connection_pool() -> None:
    """
    Initialize PostgreSQL connection pool.

    Should be called on application startup.

    Raises:
        psycopg2.Error: If connection cannot be established
    """
    global _connection_pool

    try:
        config = get_config()
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=config.database_url,
        )
        logger.info('Database connection pool initialized')
    except psycopg2.Error as e:
        logger.error(f'Failed to initialize connection pool: {e}')
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
            logger.info('Database connection pool closed')
        except Exception as e:
            logger.error(f'Error closing connection pool: {e}')
        finally:
            _connection_pool = None


def get_db_pool() -> Optional[pool.ThreadedConnectionPool]:
    """
    Get the current connection pool.

    Returns:
        Optional[pool.ThreadedConnectionPool]: Pool instance or None if not initialized
    """
    return _connection_pool


def get_db_connection():
    """
    Get a single database connection from the pool.

    Returns:
        Connection object that should be returned to pool via return_db_connection()

    Raises:
        RuntimeError: If pool not initialized
    """
    pool_instance = get_db_pool()
    if pool_instance is None:
        raise RuntimeError('Connection pool not initialized')
    return pool_instance.getconn()


def return_db_connection(conn) -> None:
    """
    Return a connection to the pool for reuse.

    Should be called after connection is no longer needed.

    Args:
        conn: Connection object to return
    """
    pool_instance = get_db_pool()
    if pool_instance is not None and conn is not None:
        try:
            pool_instance.putconn(conn)
        except Exception as e:
            logger.error(f'Error returning connection to pool: {e}')


# Credential Repository Functions

def create_credential(
    domain: str,
    username: str,
    password: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a new credential with encrypted password.

    Args:
        domain: Portal domain (must be unique)
        username: Portal username
        password: Portal password (will be encrypted)
        metadata: Optional portal-specific metadata (JSON)

    Returns:
        Dict with credential data including id, domain, username, created_at

    Raises:
        psycopg2.IntegrityError: If domain already exists
        Exception: On encryption or database errors
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

        # Encrypt the password
        encrypted_data = encrypt(password)

        # Insert credential
        cursor.execute(
            '''
            INSERT INTO credentials (domain, username, encrypted_data, metadata, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, domain, username, is_active, metadata, created_at, updated_at
            ''',
            (domain, username, encrypted_data, metadata or {})
        )

        result = cursor.fetchone()
        conn.commit()

        logger.info(f'Credential created for domain: {domain}')
        return dict(result) if result else {}

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        logger.error(f'Credential already exists for domain {domain}: {e}')
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f'Failed to create credential: {e}')
        raise
    finally:
        if cursor:
            cursor.close()
        return_db_connection(conn)


def get_credential_by_domain(domain: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve active credential by domain with decrypted password.

    Updates last_used_at timestamp.

    Args:
        domain: Portal domain to look up

    Returns:
        Dict with credential data including decrypted password, or None if not found

    Raises:
        Exception: On decryption or database errors
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

        cursor.execute(
            '''
            SELECT id, domain, username, encrypted_data, metadata, is_active, created_at, updated_at, last_used_at
            FROM credentials
            WHERE domain = %s AND is_active = true
            LIMIT 1
            ''',
            (domain,)
        )

        result = cursor.fetchone()

        if not result:
            logger.warning(f'No active credential found for domain: {domain}')
            return None

        # Decrypt the password
        try:
            decrypted_password = decrypt(result['encrypted_data'])
        except Exception as e:
            logger.error(f'Failed to decrypt credential for domain {domain}: {e}')
            raise

        # Update last_used_at
        try:
            cursor.execute(
                'UPDATE credentials SET last_used_at = NOW() WHERE id = %s',
                (result['id'],)
            )
            conn.commit()
        except Exception as e:
            logger.error(f'Failed to update last_used_at for credential {result["id"]}: {e}')
            conn.rollback()

        # Return credential with decrypted password
        credential = dict(result)
        credential['password'] = decrypted_password
        del credential['encrypted_data']  # Don't include encrypted data in response

        return credential

    except Exception as e:
        logger.error(f'Failed to retrieve credential for domain {domain}: {e}')
        raise
    finally:
        if cursor:
            cursor.close()
        return_db_connection(conn)


def get_credential_by_id(credential_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve credential by ID with decrypted password.

    Args:
        credential_id: UUID of credential

    Returns:
        Dict with credential data including decrypted password, or None if not found

    Raises:
        Exception: On decryption or database errors
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

        cursor.execute(
            '''
            SELECT id, domain, username, encrypted_data, metadata, is_active, created_at, updated_at, last_used_at
            FROM credentials
            WHERE id = %s
            ''',
            (credential_id,)
        )

        result = cursor.fetchone()

        if not result:
            logger.warning(f'Credential not found with id: {credential_id}')
            return None

        # Decrypt the password
        try:
            decrypted_password = decrypt(result['encrypted_data'])
        except Exception as e:
            logger.error(f'Failed to decrypt credential {credential_id}: {e}')
            raise

        # Update last_used_at
        try:
            cursor.execute(
                'UPDATE credentials SET last_used_at = NOW() WHERE id = %s',
                (credential_id,)
            )
            conn.commit()
        except Exception as e:
            logger.error(f'Failed to update last_used_at for credential {credential_id}: {e}')
            conn.rollback()

        # Return credential with decrypted password
        credential = dict(result)
        credential['password'] = decrypted_password
        del credential['encrypted_data']

        return credential

    except Exception as e:
        logger.error(f'Failed to retrieve credential {credential_id}: {e}')
        raise
    finally:
        if cursor:
            cursor.close()
        return_db_connection(conn)


def update_credential(
    credential_id: str,
    username: str,
    password: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Update credential with new encrypted password.

    Args:
        credential_id: UUID of credential to update
        username: New username
        password: New password (will be encrypted)
        metadata: Optional new metadata

    Returns:
        Dict with updated credential data

    Raises:
        Exception: On encryption or database errors
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

        # Get old credential for logging
        cursor.execute('SELECT username FROM credentials WHERE id = %s', (credential_id,))
        old_cred = cursor.fetchone()
        old_username = old_cred['username'] if old_cred else None

        # Encrypt new password
        encrypted_data = encrypt(password)

        # Update credential
        cursor.execute(
            '''
            UPDATE credentials
            SET username = %s, encrypted_data = %s, metadata = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, domain, username, is_active, metadata, created_at, updated_at
            ''',
            (username, encrypted_data, metadata or {}, credential_id)
        )

        result = cursor.fetchone()
        conn.commit()

        logger.info(f'Credential updated: {credential_id}')
        return dict(result) if result else {}

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f'Failed to update credential {credential_id}: {e}')
        raise
    finally:
        if cursor:
            cursor.close()
        return_db_connection(conn)


def delete_credential(credential_id: str) -> bool:
    """
    Delete (deactivate) credential by marking as inactive.

    This is a logical delete to preserve audit trail.

    Args:
        credential_id: UUID of credential to delete

    Returns:
        bool: True if deleted, False if not found

    Raises:
        Exception: On database errors
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE credentials SET is_active = false, updated_at = NOW() WHERE id = %s',
            (credential_id,)
        )

        rows_affected = cursor.rowcount
        conn.commit()

        if rows_affected > 0:
            logger.warning(f'Credential deactivated: {credential_id}')
            return True
        else:
            logger.warning(f'Credential not found: {credential_id}')
            return False

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f'Failed to delete credential {credential_id}: {e}')
        raise
    finally:
        if cursor:
            cursor.close()
        return_db_connection(conn)


def list_all_credentials() -> List[Dict[str, Any]]:
    """
    List all credentials (without passwords for security).

    Args:
        None

    Returns:
        List of dicts with credential metadata (no encrypted_data)

    Raises:
        Exception: On database errors
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)

        cursor.execute(
            '''
            SELECT id, domain, username, is_active, metadata, created_at, updated_at, last_used_at
            FROM credentials
            ORDER BY created_at DESC
            '''
        )

        results = cursor.fetchall()
        return [dict(row) for row in results]

    except Exception as e:
        logger.error(f'Failed to list credentials: {e}')
        raise
    finally:
        if cursor:
            cursor.close()
        return_db_connection(conn)
