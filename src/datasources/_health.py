"""
Health Check Utility for DataSource Adapters

Provides standardized health check probing that avoids common issues:
- Base URL 403s (probes real endpoints instead)
- DNS failures vs HTTP errors
- Authentication requirements (401/404 treated as reachable)
"""

from typing import Callable, List, Optional, Tuple, Any
import asyncio


async def probe_any(
    http_get: Callable,
    urls: List[str],
    ok_under_500: bool = True,
    timeout: float = 8.0,
) -> Tuple[bool, Optional[str]]:
    """
    Probe multiple URLs and return True if any are reachable.

    This helper addresses common health check issues:
    - Base URLs that return 403 (use real endpoint URLs instead)
    - Authentication-required APIs (401/404 indicates reachability)
    - DNS vs HTTP errors (distinguishes connectivity from access)

    Args:
        http_get: Async function that takes (url, timeout) and returns (status, content, headers)
        urls: List of URLs to try (stops at first success)
        ok_under_500: If True, accepts any 200-499 status (including 401/404)
                     If False, only accepts 200-299 status
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_reachable, successful_url or None)

    Example:
        >>> async def get(url, timeout):
        ...     return await some_http_client.get(url, timeout=timeout)
        >>> is_healthy, url = await probe_any(get, [
        ...     "https://example.com/api/v1/health",
        ...     "https://example.com/api/v1/status",
        ... ])
    """
    for url in urls:
        try:
            status, _, _ = await http_get(url, timeout=timeout)

            if ok_under_500:
                # Accept any response indicating host is reachable
                if 200 <= status < 500:
                    return True, url
            else:
                # Only accept successful responses
                if 200 <= status < 300:
                    return True, url

        except (ConnectionRefusedError, OSError) as e:
            # DNS/connectivity error - try next URL
            continue
        except asyncio.TimeoutError:
            # Timeout - try next URL
            continue
        except Exception as e:
            # Other errors - try next URL
            continue

    # None of the URLs were reachable
    return False, None


async def probe_with_fallback(
    http_get: Callable,
    primary_urls: List[str],
    fallback_urls: List[str],
    ok_under_500: bool = True,
    timeout: float = 8.0,
) -> Tuple[bool, Optional[str]]:
    """
    Probe primary URLs first, fall back to secondary URLs if all fail.

    Useful for adapters where:
    - Primary endpoints are the "real" API paths
    - Fallback endpoints are base URLs or health check endpoints

    Args:
        http_get: Async function that takes (url, timeout) and returns (status, content, headers)
        primary_urls: Preferred URLs to check first
        fallback_urls: Backup URLs if primary all fail
        ok_under_500: Accept 401/404 as "reachable"
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_reachable, successful_url or None)

    Example:
        >>> is_healthy, url = await probe_with_fallback(
        ...     http_get=self.http_get,
        ...     primary_urls=["https://api.example.com/v1/data"],
        ...     fallback_urls=["https://api.example.com/", "https://example.com/health"],
        ... )
    """
    # Try primary URLs first
    is_reachable, url = await probe_any(http_get, primary_urls, ok_under_500, timeout)

    if is_reachable:
        return True, url

    # Fall back to secondary URLs
    return await probe_any(http_get, fallback_urls, ok_under_500, timeout)
