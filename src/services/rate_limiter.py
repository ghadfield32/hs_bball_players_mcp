"""
Rate Limiting Service

Implements token bucket algorithm with per-source rate limits to ensure
we never hit actual API limits. Uses aggressive safety margins.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..config import get_settings
from ..models import DataSourceType, RateLimitStatus
from ..utils.logger import get_logger, get_metrics

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Implements classic token bucket algorithm with refill rate.
    """

    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float  # Current tokens
    last_refill: float  # Last refill timestamp

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (burst capacity)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if insufficient tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait
        """
        self.refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate

    @property
    def available_tokens(self) -> int:
        """Get current available tokens."""
        self.refill()
        return int(self.tokens)


class RateLimiter:
    """
    Per-source rate limiter with token bucket algorithm.

    Manages rate limits for multiple data sources simultaneously,
    ensuring we never exceed configured limits.
    """

    def __init__(self):
        """Initialize rate limiter."""
        self.settings = get_settings()
        self.buckets: dict[str, TokenBucket] = {}
        self.request_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._setup_buckets()

        logger.info("Rate limiter initialized", sources=len(self.buckets))

    def _setup_buckets(self) -> None:
        """Set up token buckets for all data sources."""
        # Map data source types to their rate limits
        source_limits = {
            DataSourceType.EYBL: self.settings.rate_limit_eybl,
            DataSourceType.FIBA: self.settings.rate_limit_fiba,
            DataSourceType.PSAL: self.settings.rate_limit_psal,
            DataSourceType.MN_HUB: self.settings.rate_limit_mn_hub,
            DataSourceType.GRIND_SESSION: self.settings.rate_limit_grind_session,
            DataSourceType.OTE: self.settings.rate_limit_ote,
            DataSourceType.ANGT: self.settings.rate_limit_angt,
            DataSourceType.OSBA: self.settings.rate_limit_osba,
            DataSourceType.PLAYHQ: self.settings.rate_limit_playhq,
            # Stats Adapters (High Priority)
            DataSourceType.BOUND: self.settings.rate_limit_bound,
            DataSourceType.SBLIVE: self.settings.rate_limit_sblive,
            DataSourceType.THREE_SSB: self.settings.rate_limit_three_ssb,
            DataSourceType.WSN: self.settings.rate_limit_wsn,
            # Fixtures Adapters
            DataSourceType.RANKONE: self.settings.rate_limit_rankone,
            DataSourceType.FHSAA: self.settings.rate_limit_fhsaa,
            DataSourceType.HHSAA: self.settings.rate_limit_hhsaa,
        }

        for source_type, limit_per_minute in source_limits.items():
            # Convert per-minute limit to per-second refill rate
            refill_rate = limit_per_minute / 60.0

            # Use capacity = limit to allow bursts up to the full limit
            # but average rate is still constrained
            self.buckets[source_type.value] = TokenBucket(
                capacity=limit_per_minute, refill_rate=refill_rate
            )

            logger.debug(
                f"Rate limit configured for {source_type.value}",
                limit_per_minute=limit_per_minute,
                refill_rate=refill_rate,
            )

    async def acquire(
        self, source: str, tokens: int = 1, timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire permission to make request(s).

        Blocks until tokens are available or timeout is reached.

        Args:
            source: Data source identifier
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if acquired, False if timeout

        Raises:
            ValueError: If source not configured
        """
        if source not in self.buckets:
            logger.warning(f"Rate limit not configured for source: {source}, using default")
            # Use default bucket
            if "default" not in self.buckets:
                self.buckets["default"] = TokenBucket(
                    capacity=self.settings.rate_limit_default,
                    refill_rate=self.settings.rate_limit_default / 60.0,
                )
            source = "default"

        bucket = self.buckets[source]
        start_time = time.time()

        async with self.locks[source]:
            while True:
                if bucket.consume(tokens):
                    # Record request
                    self.request_history[source].append(datetime.utcnow())
                    get_metrics().record_datasource_request(source, success=True)

                    logger.debug(
                        f"Rate limit acquired for {source}",
                        tokens=tokens,
                        available=bucket.available_tokens,
                    )
                    return True

                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        logger.warning(
                            f"Rate limit timeout for {source}",
                            timeout=timeout,
                            tokens_requested=tokens,
                        )
                        get_metrics().record_rate_limit_hit()
                        return False

                # Wait before retry
                wait_time = min(bucket.get_wait_time(tokens), 1.0)  # Max 1 second wait
                logger.debug(
                    f"Rate limit waiting for {source}", wait_seconds=wait_time, tokens=tokens
                )
                await asyncio.sleep(wait_time)

    def get_status(self, source: str) -> Optional[RateLimitStatus]:
        """
        Get current rate limit status for a source.

        Args:
            source: Data source identifier

        Returns:
            RateLimitStatus or None if source not found
        """
        if source not in self.buckets:
            return None

        bucket = self.buckets[source]
        bucket.refill()

        # Get requests in current minute window
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = [
            ts for ts in self.request_history[source] if ts >= one_minute_ago
        ]

        # Calculate when window resets (next minute boundary)
        window_reset = now + timedelta(minutes=1)
        window_reset = window_reset.replace(second=0, microsecond=0)

        # Convert source string to DataSourceType
        try:
            source_type = DataSourceType(source)
        except ValueError:
            source_type = DataSourceType.UNKNOWN

        return RateLimitStatus(
            source_type=source_type,
            requests_made=len(recent_requests),
            requests_allowed=bucket.capacity,
            window_reset_at=window_reset,
            is_limited=bucket.available_tokens < 1,
        )

    def get_all_statuses(self) -> dict[str, RateLimitStatus]:
        """
        Get rate limit status for all sources.

        Returns:
            Dictionary mapping source to RateLimitStatus
        """
        return {source: self.get_status(source) for source in self.buckets.keys()}

    def reset_source(self, source: str) -> bool:
        """
        Reset rate limit for a specific source.

        Args:
            source: Data source identifier

        Returns:
            True if reset, False if source not found
        """
        if source not in self.buckets:
            return False

        bucket = self.buckets[source]
        bucket.tokens = bucket.capacity
        bucket.last_refill = time.time()
        self.request_history[source].clear()

        logger.info(f"Rate limit reset for {source}")
        return True

    def reset_all(self) -> None:
        """Reset rate limits for all sources."""
        for source in self.buckets.keys():
            self.reset_source(source)
        logger.info("All rate limits reset")


# Global rate limiter instance
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()
    return _rate_limiter_instance


async def rate_limit_decorator(source: str):
    """
    Decorator to apply rate limiting to async functions.

    Args:
        source: Data source identifier

    Example:
        @rate_limit_decorator("eybl")
        async def fetch_data():
            ...
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            await limiter.acquire(source)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
