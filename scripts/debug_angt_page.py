"""
Debug ANGT Stats Page Structure

Inspects the actual HTML structure of the ANGT stats page to understand
why the adapter isn't finding the stats table.

Usage:
    python scripts/debug_angt_page.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - ANGT Debugging
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))


async def debug_angt_page():
    """Inspect ANGT stats page structure."""
    print("=" * 80)
    print("ANGT STATS PAGE DEBUG")
    print("=" * 80)

    stats_url = "https://www.euroleaguebasketball.net/ngt/stats?size=1000&statistic=PIR&statisticMode=perGame"

    print(f"\nFetching: {stats_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load page
        print("Loading page...")
        await page.goto(stats_url, wait_until="networkidle", timeout=60000)

        # Wait for potential React rendering
        print("Waiting 5 seconds for React rendering...")
        await asyncio.sleep(5)

        # Get HTML
        html = await page.content()

        # Save HTML for inspection
        output_file = Path(__file__).parent.parent / "data" / "debug" / "angt_stats.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html, encoding='utf-8')
        print(f"\nSaved HTML to: {output_file}")

        # Analyze structure
        print("\n" + "=" * 80)
        print("HTML STRUCTURE ANALYSIS")
        print("=" * 80)

        # Check for various elements
        checks = {
            "table": await page.query_selector("table"),
            "div[class*='table']": await page.query_selector("div[class*='table']"),
            "div[class*='stats']": await page.query_selector("div[class*='stats']"),
            "div[class*='players']": await page.query_selector("div[class*='players']"),
            "tbody": await page.query_selector("tbody"),
            "tr": await page.query_selector("tr"),
        }

        for selector, element in checks.items():
            status = "FOUND" if element else "NOT FOUND"
            print(f"{selector:30} {status}")

        # Check page title
        title = await page.title()
        print(f"\nPage Title: {title}")

        # Check for error messages
        error_selectors = [
            "div[class*='error']",
            "div[class*='404']",
            "div[class*='not-found']"
        ]

        for selector in error_selectors:
            error = await page.query_selector(selector)
            if error:
                text = await error.text_content()
                print(f"\nERROR FOUND: {text}")

        # Get all links on page (to understand structure)
        links = await page.query_selector_all("a")
        print(f"\nTotal links on page: {len(links)}")

        # Check if page is blank/minimal
        body = await page.query_selector("body")
        if body:
            body_text = await body.text_content()
            text_length = len(body_text.strip()) if body_text else 0
            print(f"Body text length: {text_length} characters")

            if text_length < 100:
                print("\nWARNING: Page appears nearly blank!")
                print(f"Body text: {body_text[:200] if body_text else 'None'}")

        await browser.close()

    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)
    print(f"\nNext steps:")
    print(f"1. Open {output_file} in a browser to inspect HTML")
    print(f"2. Look for table/data structures")
    print(f"3. Update ANGT adapter selectors based on findings")


if __name__ == "__main__":
    asyncio.run(debug_angt_page())
