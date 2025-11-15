#!/usr/bin/env python3
"""
PSAL Website Browser Automation Analysis
Tests Playwright with various wait strategies to see when data loads
"""

import asyncio
from playwright.async_api import async_playwright


async def analyze_psal_with_browser():
    """Analyze PSAL website with browser automation."""

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001"

    print(f"[...] Launching browser for {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[...] Navigating to page...")
        try:
            # Navigate and wait for networkidle (all network requests done)
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print(f"[OK] Page loaded (network idle)")

            # Wait additional time for AJAX to complete
            print(f"[...] Waiting 5 seconds for AJAX data loading...")
            await page.wait_for_timeout(5000)

            # Get rendered HTML
            html = await page.content()
            print(f"[OK] HTML captured ({len(html)} chars)\n")

            # Check for tables
            tables = await page.locator('table').all()
            print(f"[INFO] Found {len(tables)} <table> elements")

            for i, table in enumerate(tables, 1):
                classes = await table.get_attribute('class')
                print(f"  Table {i}: class='{classes}'")

                # Count rows
                rows = await table.locator('tr').all()
                print(f"           rows={len(rows)}")

                # Show first row content if more than 1 row
                if len(rows) > 1:
                    first_row = rows[0]
                    cells = await first_row.locator('th, td').all()
                    headers = []
                    for cell in cells:
                        text = await cell.inner_text()
                        headers.append(text.strip())
                    print(f"           headers={headers[:10]}")

                    # Show second row (first data row)
                    if len(rows) > 1:
                        data_row = rows[1]
                        cells = await data_row.locator('td').all()
                        data = []
                        for cell in cells:
                            text = await cell.inner_text()
                            data.append(text.strip())
                        print(f"           first_data={data[:10]}")

            # Check for divs with stat data
            print(f"\n[INFO] Checking for data containers...")
            stat_divs = await page.locator('div[class*="stat"]').all()
            print(f"  Divs with 'stat' in class: {len(stat_divs)}")

            leader_divs = await page.locator('div[class*="leader"]').all()
            print(f"  Divs with 'leader' in class: {len(leader_divs)}")

            # Check page title
            title = await page.title()
            print(f"\n[INFO] Page title: {title}")

            # Get body text (first 800 chars)
            body_text = await page.locator('body').inner_text()
            print(f"\n[INFO] Body text (first 800 chars):")
            print(body_text[:800])

            # Show HTML snippet
            print(f"\n[DEBUG] First 2000 chars of HTML:")
            print("=" * 80)
            print(html[:2000])
            print("=" * 80)

        except Exception as e:
            print(f"\n[X] Error: {e}")
            print(f"[X] Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()
            print("\n[OK] Browser closed")


if __name__ == "__main__":
    asyncio.run(analyze_psal_with_browser())
