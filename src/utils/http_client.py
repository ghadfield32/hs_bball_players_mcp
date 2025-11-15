"""
HTTP Client Wrapper

Provides robust HTTP client with retry logic, timeout handling,
and integration with rate limiting and caching.
"""

import asyncio
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings
from ..services.cache import get_cache
from ..services.rate_limiter import get_rate_limiter
from .logger import get_logger

logger = get_logger(__name__)


class HTTPClient:
    """
    HTTP client with retry logic, rate limiting, and caching.

    Provides a robust interface for making HTTP requests to data sources.
    """

    def __init__(self, source: str):
        """
        Initialize HTTP client for a specific data source.

        Args:
            source: Data source identifier
        """
        self.source = source
        self.settings = get_settings()
        self.rate_limiter = get_rate_limiter()
        self.cache_service = get_cache()

        # Build headers with browser-like defaults
        default_headers = {
            "User-Agent": self.settings.http_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Add per-source header overrides (e.g., Referer for specific sources)
        source_specific = self.settings.http_source_headers.get(source, {})
        merged_headers = {**default_headers, **source_specific}

        # Create httpx client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.http_timeout),
            headers=merged_headers,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

        logger.info(f"HTTP client initialized for {source}")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic for network errors and rate limits.

        Retries on:
        - Network/timeout errors (3 attempts)
        - 429 (rate limit), 500, 502, 503, 504 (server errors) - 3 attempts with backoff

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On HTTP errors after retries
        """
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.debug(
                    f"Making {method} request to {url}",
                    attempt=attempt + 1,
                    source=self.source,
                )

                response = await self.client.request(method, url, **kwargs)

                # Check if we should retry on status code
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_attempts - 1:
                        backoff_time = self.settings.http_retry_backoff ** attempt
                        logger.warning(
                            f"Retryable HTTP error: {method} {url}",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            backoff_seconds=backoff_time,
                            source=self.source,
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    # Last attempt, raise the error
                    response.raise_for_status()

                # Success or non-retryable error
                response.raise_for_status()

                logger.debug(
                    f"Request successful: {method} {url}",
                    status_code=response.status_code,
                    source=self.source,
                )
                return response

            except httpx.HTTPStatusError as e:
                if attempt == max_attempts - 1:
                    logger.error(
                        f"HTTP error: {method} {url}",
                        status_code=e.response.status_code,
                        source=self.source,
                        error=str(e),
                    )
                    raise
                # Will retry if status code is retryable

            except (httpx.NetworkError, httpx.TimeoutException) as e:
                if attempt < max_attempts - 1:
                    backoff_time = self.settings.http_retry_backoff ** attempt
                    logger.warning(
                        f"Network/timeout error: {method} {url}",
                        attempt=attempt + 1,
                        backoff_seconds=backoff_time,
                        source=self.source,
                        error=str(e),
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                logger.error(
                    f"Network/timeout error after retries: {method} {url}",
                    source=self.source,
                    error=str(e),
                )
                raise

            except Exception as e:
                logger.error(
                    f"Unexpected error: {method} {url}",
                    source=self.source,
                    error=str(e),
                )
                raise

        # Should not reach here, but for type checking
        raise RuntimeError(f"Request failed after {max_attempts} attempts")

    async def get(
        self,
        url: str,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make GET request with rate limiting and caching.

        Args:
            url: Request URL
            use_cache: Whether to use cache
            cache_ttl: Cache TTL in seconds (None = use default)
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response
        """
        # Check cache first
        if use_cache:
            cached_html = await self.cache_service.get_raw_html(url)
            if cached_html is not None:
                logger.debug(f"Cache hit for {url}", source=self.source)
                # Create mock response from cached HTML
                return httpx.Response(
                    status_code=200,
                    content=cached_html.encode("utf-8"),
                    request=httpx.Request("GET", url),
                )

        # Acquire rate limit permission
        await self.rate_limiter.acquire(self.source, tokens=1)

        # Make request
        response = await self._make_request("GET", url, **kwargs)

        # Cache response if successful
        if use_cache and response.status_code == 200:
            ttl = cache_ttl if cache_ttl is not None else 3600
            await self.cache_service.set_raw_html(url, response.text, ttl=ttl)
            logger.debug(f"Cached response for {url}", ttl=ttl, source=self.source)

        return response

    async def post(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make POST request with rate limiting.

        Args:
            url: Request URL
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response
        """
        # Acquire rate limit permission
        await self.rate_limiter.acquire(self.source, tokens=1)

        # Make request
        return await self._make_request("POST", url, **kwargs)

    async def get_text(
        self,
        url: str,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        GET request returning text content.

        Args:
            url: Request URL
            use_cache: Whether to use cache
            cache_ttl: Cache TTL in seconds
            **kwargs: Additional arguments for httpx

        Returns:
            Response text content
        """
        response = await self.get(url, use_cache=use_cache, cache_ttl=cache_ttl, **kwargs)
        return response.text

    async def get_json(
        self,
        url: str,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        """
        GET request returning JSON content.

        Args:
            url: Request URL
            use_cache: Whether to use cache
            cache_ttl: Cache TTL in seconds
            **kwargs: Additional arguments for httpx

        Returns:
            Parsed JSON response
        """
        response = await self.get(url, use_cache=use_cache, cache_ttl=cache_ttl, **kwargs)
        return response.json()

    async def batch_get(
        self,
        urls: list[str],
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        max_concurrent: int = 5,
        **kwargs: Any,
    ) -> list[httpx.Response]:
        """
        Make multiple GET requests with concurrency control.

        Args:
            urls: List of URLs to fetch
            use_cache: Whether to use cache
            cache_ttl: Cache TTL in seconds
            max_concurrent: Maximum concurrent requests
            **kwargs: Additional arguments for httpx

        Returns:
            List of responses (in same order as URLs)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url: str) -> httpx.Response:
            async with semaphore:
                return await self.get(url, use_cache=use_cache, cache_ttl=cache_ttl, **kwargs)

        logger.info(
            f"Batch fetching {len(urls)} URLs",
            max_concurrent=max_concurrent,
            source=self.source,
        )

        tasks = [fetch_with_semaphore(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any errors
        error_count = sum(1 for r in responses if isinstance(r, Exception))
        if error_count > 0:
            logger.warning(
                f"Batch fetch completed with errors",
                total=len(urls),
                errors=error_count,
                source=self.source,
            )

        return responses


def create_http_client(source: str) -> HTTPClient:
    """
    Create HTTP client for a data source.

    Args:
        source: Data source identifier

    Returns:
        HTTPClient instance
    """
    return HTTPClient(source)
