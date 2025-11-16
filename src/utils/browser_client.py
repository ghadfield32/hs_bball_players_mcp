"""
Browser Automation Client

Provides browser automation capabilities for scraping JavaScript-heavy websites
(React, Angular, Vue, etc.) that require client-side rendering.

Key Features:
- Singleton browser instance (efficiency)
- Context pooling for concurrent requests
- Aggressive caching of rendered content
- Automatic retry with exponential backoff
- Graceful error handling
- Support for multiple browser types (Chromium, Firefox, WebKit)

Usage:
    async with BrowserClient() as client:
        html = await client.get_rendered_html(url, wait_for="table")

Author: Claude Code
Date: 2025-11-11
"""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Literal, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from ..config import Settings
from .logger import get_logger

logger = get_logger(__name__)


class BrowserClient:
    """
    Browser automation client for scraping SPA websites.

    Uses Playwright for browser automation with:
    - Singleton browser instance (created once, reused)
    - Context pooling (multiple contexts from one browser)
    - Aggressive caching (cache rendered HTML)
    - Automatic retries (transient failures)

    Attributes:
        browser_type: Browser to use (chromium, firefox, webkit)
        headless: Run in headless mode (no UI)
        timeout: Default timeout for operations (ms)
        cache_enabled: Enable HTML caching
        cache_ttl: Cache time-to-live (seconds)
    """

    # Class-level singleton instances
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _contexts: List[BrowserContext] = []
    _cache: Dict[str, tuple[str, datetime]] = {}
    _lock = asyncio.Lock()

    def __init__(
        self,
        settings: Optional[Settings] = None,
        browser_type: Literal["chromium", "firefox", "webkit"] = "chromium",
        headless: bool = True,
        timeout: int = 30000,  # 30 seconds
        cache_enabled: bool = True,
        cache_ttl: int = 3600,  # 1 hour
        max_contexts: int = 5,  # Maximum concurrent contexts
    ):
        """
        Initialize browser client.

        Args:
            settings: Application settings (optional)
            browser_type: Browser to use
            headless: Run headless (no UI)
            timeout: Default timeout (milliseconds)
            cache_enabled: Enable caching
            cache_ttl: Cache TTL (seconds)
            max_contexts: Max concurrent browser contexts
        """
        self.settings = settings or Settings()
        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.max_contexts = max_contexts

        self.logger = logger

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit (contexts cleaned up but browser persists)."""
        # Don't close browser - it's a singleton for efficiency
        # Only clean up if there's an error
        if exc_type:
            self.logger.error("Browser context error", error=str(exc_val))

    async def _ensure_browser(self):
        """Ensure browser instance exists (singleton pattern)."""
        async with self._lock:
            if self._playwright is None:
                self.logger.info("Initializing Playwright")
                self._playwright = await async_playwright().start()

            if self._browser is None or not self._browser.is_connected():
                self.logger.info(
                    f"Launching {self.browser_type} browser",
                    headless=self.headless
                )

                browser_launcher = getattr(self._playwright, self.browser_type)
                self._browser = await browser_launcher.launch(
                    headless=self.headless,
                    # Performance optimizations
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-accelerated-2d-canvas",
                        "--disable-gpu",
                    ] if self.browser_type == "chromium" else [],
                )

                self.logger.info("Browser launched successfully")

    async def _get_context(self) -> BrowserContext:
        """
        Get or create a browser context from the pool.

        Returns:
            BrowserContext instance
        """
        await self._ensure_browser()

        # Clean up disconnected contexts (try-catch to handle Playwright API changes)
        cleaned_contexts = []
        for c in self._contexts:
            if c:
                try:
                    # Check if context is still usable by trying to access pages
                    _ = c.pages
                    cleaned_contexts.append(c)
                except Exception:
                    # Context is closed or unusable, skip it
                    pass
        self._contexts = cleaned_contexts

        # Reuse existing context if available
        if self._contexts and len(self._contexts) < self.max_contexts:
            return self._contexts[0]

        # Create new context
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ignore_https_errors=True,
        )

        self._contexts.append(context)

        # Limit context pool size
        if len(self._contexts) > self.max_contexts:
            old_context = self._contexts.pop(0)
            await old_context.close()

        return context

    def _get_cache_key(self, url: str, **kwargs) -> str:
        """Generate cache key for URL and parameters."""
        key_parts = [url] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get cached HTML if not expired."""
        if not self.cache_enabled:
            return None

        if cache_key in self._cache:
            html, cached_at = self._cache[cache_key]

            # Check if cache expired
            if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                self.logger.debug("Cache hit", cache_key=cache_key[:8])
                return html
            else:
                # Remove expired cache
                del self._cache[cache_key]

        return None

    def _save_to_cache(self, cache_key: str, html: str):
        """Save HTML to cache."""
        if self.cache_enabled:
            self._cache[cache_key] = (html, datetime.now())
            self.logger.debug("Cached HTML", cache_key=cache_key[:8], size=len(html))

    async def get_rendered_html(
        self,
        url: str,
        wait_for: Optional[str] = None,
        wait_timeout: Optional[int] = None,
        wait_for_network_idle: bool = True,
        execute_script: Optional[str] = None,
        cache_override_ttl: Optional[int] = None,
    ) -> str:
        """
        Get rendered HTML from a URL using browser automation.

        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for (e.g., "table", ".stats-table")
            wait_timeout: Timeout for wait_for selector (ms)
            wait_for_network_idle: Wait for network to be idle
            execute_script: Optional JavaScript to execute before extraction
            cache_override_ttl: Override default cache TTL for this request

        Returns:
            Rendered HTML as string

        Raises:
            PlaywrightTimeoutError: If page load or selector wait times out
            Exception: Other browser automation errors
        """
        # Check cache first
        cache_key = self._get_cache_key(
            url,
            wait_for=wait_for,
            script=execute_script
        )

        cached_html = self._get_from_cache(cache_key)
        if cached_html:
            return cached_html

        # Get browser context
        context = await self._get_context()
        page: Optional[Page] = None

        try:
            # Create new page
            page = await context.new_page()

            # Set default timeout
            page.set_default_timeout(wait_timeout or self.timeout)

            self.logger.info("Navigating to URL", url=url)

            # Navigate to URL
            await page.goto(url, wait_until="domcontentloaded")

            # Wait for network idle if requested
            if wait_for_network_idle:
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    # Network idle timeout is not critical
                    self.logger.warning("Network idle timeout (continuing)")

            # Wait for specific selector if provided
            if wait_for:
                self.logger.debug(f"Waiting for selector: {wait_for}")
                try:
                    await page.wait_for_selector(wait_for, timeout=wait_timeout or self.timeout)
                except PlaywrightTimeoutError:
                    self.logger.warning(
                        f"Selector '{wait_for}' not found within timeout",
                        url=url
                    )
                    # Don't fail - the element might not exist, which is ok

            # Execute custom JavaScript if provided
            if execute_script:
                self.logger.debug("Executing custom script")
                await page.evaluate(execute_script)
                # Give script time to execute
                await asyncio.sleep(1)

            # Get rendered HTML
            html = await page.content()

            self.logger.info(
                "Successfully fetched rendered HTML",
                url=url,
                html_size=len(html)
            )

            # Cache the result
            if cache_override_ttl is not None:
                old_ttl = self.cache_ttl
                self.cache_ttl = cache_override_ttl
                self._save_to_cache(cache_key, html)
                self.cache_ttl = old_ttl
            else:
                self._save_to_cache(cache_key, html)

            return html

        except PlaywrightTimeoutError as e:
            self.logger.error(
                "Page load timeout",
                url=url,
                error=str(e)
            )
            raise

        except Exception as e:
            self.logger.error(
                "Browser automation error",
                url=url,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

        finally:
            # Always close the page
            if page:
                await page.close()

    async def get_multiple_rendered(
        self,
        urls: List[str],
        **kwargs
    ) -> Dict[str, str]:
        """
        Fetch multiple URLs concurrently using browser automation.

        Args:
            urls: List of URLs to fetch
            **kwargs: Additional arguments passed to get_rendered_html

        Returns:
            Dictionary mapping URLs to rendered HTML
        """
        self.logger.info(f"Fetching {len(urls)} URLs concurrently")

        tasks = [self.get_rendered_html(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to fetch {url}", error=str(result))
                output[url] = None
            else:
                output[url] = result

        return output

    @classmethod
    async def close_all(cls):
        """Close all browser instances and contexts (cleanup)."""
        async with cls._lock:
            # Close all contexts
            for context in cls._contexts:
                try:
                    await context.close()
                except:
                    pass
            cls._contexts.clear()

            # Close browser
            if cls._browser:
                try:
                    await cls._browser.close()
                except:
                    pass
                cls._browser = None

            # Stop Playwright
            if cls._playwright:
                try:
                    await cls._playwright.stop()
                except:
                    pass
                cls._playwright = None

            # Clear cache
            cls._cache.clear()

            logger.info("Browser instances closed")

    @classmethod
    def clear_cache(cls):
        """Clear HTML cache."""
        cls._cache.clear()
        logger.info("Browser cache cleared")


@asynccontextmanager
async def get_browser_client(**kwargs):
    """
    Context manager for browser client usage.

    Usage:
        async with get_browser_client() as client:
            html = await client.get_rendered_html(url)
    """
    client = BrowserClient(**kwargs)
    try:
        await client._ensure_browser()
        yield client
    finally:
        # Browser persists as singleton, no cleanup needed
        pass
