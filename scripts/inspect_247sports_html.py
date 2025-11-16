"""
Inspect 247Sports HTML to find the right selector

Fetches the page and saves the HTML to examine what elements are actually present.

Usage:
    python scripts/inspect_247sports_html.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Fetch 247Sports page and inspect HTML."""
    from playwright.async_api import async_playwright

    url = "https://247sports.com/season/2025-basketball/compositerecruitrankings/"

    playwright = None
    browser = None
    context = None
    page = None

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        logger.info(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait longer for React to render
        logger.info("Waiting 20 seconds for React to render...")
        await asyncio.sleep(20)

        # Get HTML
        html = await page.content()
        logger.info(f"Got {len(html)} bytes of HTML")

        # Save to file
        output_path = Path("data/debug/247sports_rankings.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML saved to {output_path}")

        # Check for different selectors
        logger.info("\nChecking for various selectors:")

        selectors_to_check = [
            "table",
            "div[class*='rankings']",
            "div[class*='recruit']",
            "div[class*='list']",
            "div[class*='player']",
            "[data-test-id]",
            ".rankings-page",
            ".player-row",
            "article",
        ]

        for selector in selectors_to_check:
            try:
                element = await page.wait_for_selector(selector, timeout=1000)
                if element:
                    logger.info(f"  ✓ Found: {selector}")
            except:
                logger.info(f"  ✗ Not found: {selector}")

        # Get page title
        title = await page.title()
        logger.info(f"\nPage title: {title}")

        # Take screenshot
        screenshot_path = Path("data/debug/247sports_rankings.png")
        await page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot saved to {screenshot_path}")

    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


if __name__ == '__main__':
    asyncio.run(main())
