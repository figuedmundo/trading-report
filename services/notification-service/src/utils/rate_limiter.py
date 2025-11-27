"""
Token bucket rate limiter implementation.

Implements token bucket algorithm for per-channel rate limiting.
"""

import time
import math
from typing import Optional


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Max tokens in bucket (e.g., 100 for 100 emails/hour)
            refill_rate: Tokens per second (e.g., 100/3600 = 0.0278 for 100/hour)
        """
        self.capacity = capacity
        self.tokens = float(capacity)  # Start full
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    async def try_consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens; return True if successful.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if rate limited
        """
        await self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

    def get_retry_after_seconds(self) -> int:
        """
        Calculate seconds until next token available.

        Returns:
            Seconds to wait for next token
        """
        if self.tokens >= 1:
            return 0

        needed = 1 - self.tokens
        return int(math.ceil(needed / self.refill_rate))

    def get_tokens_available(self) -> int:
        """
        Get current number of available tokens (without refilling).

        Returns:
            Number of tokens available
        """
        return int(self.tokens)
