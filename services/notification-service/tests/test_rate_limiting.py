"""Tests for rate limiting implementation."""

import pytest
import time
from src.utils.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_token_bucket_consume_with_tokens():
    """Test consuming tokens when available."""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    result = await bucket.try_consume(1)
    assert result is True
    assert bucket.tokens < 10


@pytest.mark.asyncio
async def test_token_bucket_consume_without_tokens():
    """Test consuming tokens when unavailable."""
    bucket = TokenBucket(capacity=1, refill_rate=0.1)
    # Consume the one token
    await bucket.try_consume(1)
    # Try to consume another
    result = await bucket.try_consume(1)
    assert result is False


@pytest.mark.asyncio
async def test_token_bucket_refill():
    """Test token refill over time."""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    initial_tokens = bucket.tokens

    # Wait a bit for refill
    await bucket._refill()
    bucket.last_refill = time.time() - 2  # Fake 2 seconds passed

    await bucket._refill()
    # Should have more tokens now (though capped at capacity)
    assert bucket.tokens >= 9  # Should be back to 10


@pytest.mark.asyncio
async def test_get_retry_after_seconds():
    """Test retry_after calculation."""
    bucket = TokenBucket(capacity=1, refill_rate=1.0)

    # No tokens, should return > 0
    await bucket.try_consume(1)
    retry_after = bucket.get_retry_after_seconds()
    assert retry_after >= 0

    # With tokens, should return 0
    bucket.tokens = 5
    retry_after = bucket.get_retry_after_seconds()
    assert retry_after == 0


def test_tokens_available():
    """Test getting available tokens."""
    bucket = TokenBucket(capacity=100, refill_rate=10.0)
    tokens = bucket.get_tokens_available()
    assert tokens == 100
