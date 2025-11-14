"""
Browser Automation Utilities

Provides headless browser support for sources that require JavaScript rendering
or block automated requests (Cloudflare, JavaScript challenges, etc.).

Usage:
    from src.utils.browser import fetch_with_playwright

    # Fetch fully rendered HTML (passes Cloudflare/JS challenges)
    status, html, headers = await fetch_with_playwright(url)

Installation:
    pip install playwright
    playwright install chromium

Optional Dependency:
    This module gracefully handles missing Playwright - imports will fail with
    a clear error message if the library is not installed.
"""

import asyncio
import contextlib
from typing import Dict, Tuple

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None  # Optional import - gracefully handle missing library


@contextlib.asynccontextmanager
async def _launch_browser():
    """
    Context manager for browser lifecycle.

    Raises:
        RuntimeError: If Playwright is not installed
    """
    if async_playwright is None:
        raise RuntimeError(
            "Playwright not installed. To enable browser automation, run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


async def fetch_with_playwright(
    url: str,
    timeout_ms: int = 20000,
    wait_until: str = "networkidle",
) -> Tuple[int, str, Dict[str, str]]:
    """
    Fetch fully rendered HTML using headless Chromium.

    This bypasses JavaScript challenges, Cloudflare protection, and other
    anti-bot measures by using a real browser.

    Args:
        url: URL to fetch
        timeout_ms: Request timeout in milliseconds (default: 20 seconds)
        wait_until: Wait condition - "networkidle" (default), "load", or "domcontentloaded"

    Returns:
        Tuple of (status_code, html_content, response_headers)

    Raises:
        RuntimeError: If Playwright is not installed
        playwright.async_api.TimeoutError: If page load times out

    Example:
        >>> status, html, headers = await fetch_with_playwright("https://www.osaa.org")
        >>> if status == 200:
        ...     soup = BeautifulSoup(html, "lxml")
    """
    async with _launch_browser() as browser:
        # Create isolated browser context (like incognito mode)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        # Navigate to page and wait for specified condition
        response = await page.goto(url, timeout=timeout_ms, wait_until=wait_until)

        # Extract response details
        status = response.status if response else 200
        headers = dict(response.headers) if response else {}

        # Get fully rendered HTML (after JavaScript execution)
        content = await page.content()

        # Clean up
        await context.close()

        return status, content, headers


async def is_playwright_available() -> bool:
    """
    Check if Playwright is installed and Chromium is available.

    Returns:
        True if Playwright + Chromium are available, False otherwise

    Example:
        >>> if await is_playwright_available():
        ...     use_browser_path()
        ... else:
        ...     use_http_path()
    """
    if async_playwright is None:
        return False

    try:
        # Quick test: try to launch browser
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            await browser.close()
        return True
    except Exception:
        return False
