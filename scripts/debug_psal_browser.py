"""
PSAL Browser Debugging Script

Systematically debugs what's happening when we load the PSAL leaders page
with browser automation. Captures screenshots, HTML, and page structure.

Usage:
    python scripts/debug_psal_browser.py

Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser_client import BrowserClient
from src.config import get_settings


async def debug_psal_page():
    """Debug PSAL leaders page with browser automation."""
    print("=" * 80)
    print("PSAL BROWSER DEBUGGING")
    print("=" * 80)

    settings = get_settings()
    browser_client = BrowserClient(
        settings=settings,
        browser_type="chromium",
        headless=False,  # Show browser for debugging
        timeout=90000,  # 90 seconds
    )

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001#001/Basketball"
    print(f"\nTarget URL: {url}")
    print("(includes hash fragment #001/Basketball to trigger JavaScript)")
    print("\nStep 1: Loading page without waiting for specific selectors...")

    try:
        # Step 1: Load page and wait for basic load
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            print(f"\n[1.1] Navigating to {url}...")
            await page.goto(url, wait_until="networkidle", timeout=90000)

            print(f"[1.2] Page loaded successfully!")
            print(f"[1.3] Page title: {await page.title()}")

            # Step 2: Wait a bit for JavaScript to execute
            print(f"\n[2.1] Waiting 5 seconds for JavaScript to execute...")
            await asyncio.sleep(5)

            # Step 3: Check page structure
            print(f"\n[3] Analyzing page structure...")

            # Check for tables
            tables = await page.query_selector_all("table")
            print(f"[3.1] Found {len(tables)} <table> elements")

            if tables:
                for i, table in enumerate(tables[:5], 1):
                    # Get table attributes
                    classes = await table.get_attribute("class")
                    table_id = await table.get_attribute("id")
                    print(f"\n  Table {i}:")
                    print(f"    Classes: {classes or 'None'}")
                    print(f"    ID: {table_id or 'None'}")

                    # Count rows
                    rows = await table.query_selector_all("tr")
                    print(f"    Rows: {len(rows)}")

                    # Get first row content
                    if rows:
                        first_row_html = await rows[0].inner_html()
                        print(f"    First row preview: {first_row_html[:100]}...")

            # Check for divs with stat data
            print(f"\n[3.2] Checking for stat divs...")
            stat_divs = await page.query_selector_all("div[class*='stat']")
            print(f"Found {len(stat_divs)} divs with 'stat' in class")

            leader_divs = await page.query_selector_all("div[class*='leader']")
            print(f"Found {len(leader_divs)} divs with 'leader' in class")

            # Check for iframes
            print(f"\n[3.3] Checking for iframes...")
            iframes = await page.query_selector_all("iframe")
            print(f"Found {len(iframes)} iframes")

            if iframes:
                for i, iframe in enumerate(iframes, 1):
                    src = await iframe.get_attribute("src")
                    print(f"  Iframe {i}: {src}")

            # Step 4: Check network activity
            print(f"\n[4] Checking for API calls...")
            print("(Network monitoring would require capturing during page load)")

            # Step 5: Save artifacts
            print(f"\n[5] Saving debug artifacts...")

            # Save screenshot
            screenshot_path = "data/debug/psal_browser_debug.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[5.1] Screenshot saved: {screenshot_path}")

            # Save HTML
            html = await page.content()
            html_path = "data/debug/psal_browser_debug.html"
            with open(html_path, "w", encoding='utf-8') as f:
                f.write(html)
            print(f"[5.2] HTML saved: {html_path}")
            print(f"[5.3] HTML length: {len(html)} characters")

            # Step 6: Try to find stat data using various selectors
            print(f"\n[6] Testing various selectors for stat data...")

            selectors_to_test = [
                ("table", "Any table"),
                ("table:not(.feedTable)", "Tables excluding feedTable class"),
                ("table[id*='grid']", "Tables with 'grid' in ID"),
                ("table[id*='stat']", "Tables with 'stat' in ID"),
                ("div[id*='stat']", "Divs with 'stat' in ID"),
                ("div[class*='stat']", "Divs with 'stat' in class"),
                ("#divPlayerStats", "Div with ID 'divPlayerStats'"),
                ("#divLeaders", "Div with ID 'divLeaders'"),
                (".player-stats", "Class 'player-stats'"),
                ("[data-stats]", "Elements with data-stats attribute"),
            ]

            for selector, description in selectors_to_test:
                try:
                    elements = await page.query_selector_all(selector)
                    print(f"  {selector:<35} -> {len(elements)} elements ({description})")
                except Exception as e:
                    print(f"  {selector:<35} -> ERROR: {e}")

            # Step 7: Execute JavaScript to check page state
            print(f"\n[7] Executing JavaScript checks...")

            # Check if jQuery is available
            has_jquery = await page.evaluate("typeof $ !== 'undefined'")
            print(f"[7.1] jQuery available: {has_jquery}")

            # Check for specific JavaScript variables
            has_web_service_url = await page.evaluate(
                "typeof WEB_SERVICE_URL !== 'undefined'"
            )
            print(f"[7.2] WEB_SERVICE_URL defined: {has_web_service_url}")

            if has_web_service_url:
                web_service_url = await page.evaluate("WEB_SERVICE_URL")
                print(f"[7.3] WEB_SERVICE_URL value: {web_service_url}")

            # Check if Top_Player object exists
            has_top_player = await page.evaluate(
                "typeof Top_Player !== 'undefined'"
            )
            print(f"[7.4] Top_Player object defined: {has_top_player}")

            # Step 8: Try scrolling to trigger lazy loading
            print(f"\n[8] Trying to trigger lazy loading...")
            print("[8.1] Scrolling to bottom...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Check if more tables appeared
            tables_after_scroll = await page.query_selector_all("table")
            print(f"[8.2] Tables after scroll: {len(tables_after_scroll)}")

            # Step 9: Check dropdown selections
            print(f"\n[9] Checking for dropdowns that might control stat display...")
            selects = await page.query_selector_all("select")
            print(f"[9.1] Found {len(selects)} select dropdowns")

            if selects:
                for i, select in enumerate(selects[:3], 1):
                    select_id = await select.get_attribute("id")
                    print(f"\n  Select {i} (ID: {select_id}):")

                    # Get options
                    options = await select.query_selector_all("option")
                    print(f"    Options: {len(options)}")

                    for option in options[:5]:
                        value = await option.get_attribute("value")
                        text = await option.inner_text()
                        print(f"      - {text} (value={value})")

            # Step 10: Summary and recommendations
            print("\n" + "=" * 80)
            print("DEBUG SUMMARY")
            print("=" * 80)

            print(f"\nPage loaded: YES")
            print(f"Tables found: {len(tables)}")
            print(f"Iframes found: {len(iframes)}")
            print(f"JavaScript framework: {'jQuery' if has_jquery else 'Unknown'}")

            print("\n" + "=" * 80)
            print("RECOMMENDATIONS")
            print("=" * 80)

            if len(tables) == 0:
                print("\n1. NO TABLES FOUND - Stats may be in divs or require interaction")
                print("2. Check saved HTML for actual structure")
                print("3. May need to trigger dropdown or button to load stats")
            elif len(tables) > 0:
                print(f"\n1. {len(tables)} tables found - check if they contain stat data")
                print("2. May need to filter out feedback/form tables")
                print("3. Check saved screenshot to see actual page state")

            if len(selects) > 0:
                print(f"\n4. {len(selects)} dropdowns found - may need to select options to load stats")

            print("\nNext steps:")
            print("1. Review saved screenshot: data/debug/psal_browser_debug.png")
            print("2. Review saved HTML: data/debug/psal_browser_debug.html")
            print("3. Look for the correct selector or interaction needed")

            # Keep browser open for manual inspection
            print("\n" + "=" * 80)
            print("Browser will stay open for 30 seconds for manual inspection...")
            print("Press Ctrl+C to close early")
            print("=" * 80)

            try:
                await asyncio.sleep(30)
            except KeyboardInterrupt:
                print("\nClosing browser...")

            await browser.close()

    except Exception as e:
        print(f"\nERROR during debugging: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_psal_page())
