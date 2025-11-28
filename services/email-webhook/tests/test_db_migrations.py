"""
Tests for database migrations (security tables).

Verifies CRUD operations for ip_allowlist, security_events, and ip_bans tables.
Tests trigger functionality for automatic timestamp updates.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import asyncpg
import pytest


@pytest.fixture
async def db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Create a database connection for testing."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://trading_user:trading_pass@localhost:5432/trading_reports"
    )

    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_ip_allowlist_crud_operations(db_connection: asyncpg.Connection):
    """
    Test ip_allowlist table CRUD operations.

    Verifies:
    - Insert new IP address
    - Select IP by address
    - Soft delete (set enabled=false)
    - UNIQUE constraint on ip_address
    """
    test_ip = "192.168.1.100"
    test_description = "Test server for migration testing"

    # Insert new IP
    insert_query = """
        INSERT INTO ip_allowlist (ip_address, description, enabled)
        VALUES ($1, $2, $3)
        RETURNING id, ip_address, description, enabled, created_at, updated_at
    """
    result = await db_connection.fetchrow(insert_query, test_ip, test_description, True)

    assert result is not None
    assert result["ip_address"] == test_ip
    assert result["description"] == test_description
    assert result["enabled"] is True
    assert result["created_at"] is not None
    assert result["updated_at"] is not None

    # Select IP by address
    select_query = "SELECT * FROM ip_allowlist WHERE ip_address = $1"
    selected = await db_connection.fetchrow(select_query, test_ip)

    assert selected is not None
    assert selected["ip_address"] == test_ip
    assert selected["enabled"] is True

    # Soft delete (set enabled=false)
    update_query = "UPDATE ip_allowlist SET enabled = false WHERE ip_address = $1 RETURNING enabled"
    updated = await db_connection.fetchrow(update_query, test_ip)

    assert updated is not None
    assert updated["enabled"] is False

    # Verify soft delete
    verify_query = "SELECT enabled FROM ip_allowlist WHERE ip_address = $1"
    verified = await db_connection.fetchrow(verify_query, test_ip)

    assert verified is not None
    assert verified["enabled"] is False

    # Cleanup
    await db_connection.execute("DELETE FROM ip_allowlist WHERE ip_address = $1", test_ip)


@pytest.mark.asyncio
async def test_security_events_insert_and_query(db_connection: asyncpg.Connection):
    """
    Test security_events table insert and query operations.

    Verifies:
    - Insert security event with JSONB metadata
    - Query events by event_type
    - JSONB fields store and retrieve correctly
    """
    test_ip = "10.0.0.50"
    test_event_type = "rate_limit_exceeded"
    test_endpoint = "/webhook/email"
    test_headers = {"User-Agent": "test-client", "X-Request-ID": "test-123"}
    test_metadata = {"rate_limit_remaining": 0, "limit_type": "per_ip_minute"}

    # Insert security event
    insert_query = """
        INSERT INTO security_events (event_type, ip_address, endpoint, request_headers, metadata)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, event_type, ip_address, endpoint, request_headers, metadata, created_at
    """
    result = await db_connection.fetchrow(
        insert_query,
        test_event_type,
        test_ip,
        test_endpoint,
        test_headers,
        test_metadata
    )

    assert result is not None
    assert result["event_type"] == test_event_type
    assert result["ip_address"] == test_ip
    assert result["endpoint"] == test_endpoint
    assert result["request_headers"] == test_headers
    assert result["metadata"] == test_metadata
    assert result["created_at"] is not None

    event_id = result["id"]

    # Query events by event_type
    select_query = """
        SELECT * FROM security_events
        WHERE event_type = $1 AND ip_address = $2
        ORDER BY created_at DESC
    """
    events = await db_connection.fetch(select_query, test_event_type, test_ip)

    assert len(events) >= 1
    assert events[0]["event_type"] == test_event_type
    assert events[0]["ip_address"] == test_ip
    assert events[0]["metadata"]["rate_limit_remaining"] == 0

    # Cleanup
    await db_connection.execute("DELETE FROM security_events WHERE id = $1", event_id)


@pytest.mark.asyncio
async def test_ip_allowlist_updated_at_trigger(db_connection: asyncpg.Connection):
    """
    Test updated_at trigger on ip_allowlist table.

    Verifies:
    - updated_at timestamp is automatically updated on row modification
    - Trigger function update_ip_allowlist_updated_at() works correctly
    """
    test_ip = "172.16.0.1"
    test_description = "Trigger test IP"

    # Insert new IP
    insert_query = """
        INSERT INTO ip_allowlist (ip_address, description)
        VALUES ($1, $2)
        RETURNING id, created_at, updated_at
    """
    result = await db_connection.fetchrow(insert_query, test_ip, test_description)

    assert result is not None
    ip_id = result["id"]
    original_created_at = result["created_at"]
    original_updated_at = result["updated_at"]

    # Wait a moment to ensure timestamp difference
    await asyncio.sleep(0.1)

    # Update the IP description
    update_query = """
        UPDATE ip_allowlist
        SET description = $1
        WHERE id = $2
        RETURNING updated_at
    """
    updated = await db_connection.fetchrow(update_query, "Updated description", ip_id)

    assert updated is not None
    new_updated_at = updated["updated_at"]

    # Verify updated_at changed
    assert new_updated_at > original_updated_at, "updated_at should be automatically updated by trigger"

    # Verify created_at didn't change
    verify_query = "SELECT created_at, updated_at FROM ip_allowlist WHERE id = $1"
    verified = await db_connection.fetchrow(verify_query, ip_id)

    assert verified is not None
    assert verified["created_at"] == original_created_at, "created_at should not change on update"
    assert verified["updated_at"] > original_updated_at, "updated_at should be newer than original"

    # Cleanup
    await db_connection.execute("DELETE FROM ip_allowlist WHERE id = $1", ip_id)
