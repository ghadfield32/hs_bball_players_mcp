#!/usr/bin/env python3
"""
Simple EYBL Website Inspector - No project imports
"""

import asyncio
from playwright.async_api import async_playwright


async def inspect_eybl():
    """Inspect EYBL website structure using playwright directly."""
    url = "https://nikeeyb.com/cumulative-season-stats"

    print(f"[...] Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[...] Navigating to: {url}")

        try:
            # Navigate to page
            await page.goto(url, wait_until='networkidle', timeout=30000)

            print(f"[OK] Page loaded!\n")

            # Wait a bit for React to render
            await page.wait_for_timeout(3000)

            # Check for tables
            tables = await page.locator('table').all()
            print(f"[INFO] Found {len(tables)} <table> elements")

            if tables:
                for i, table in enumerate(tables, 1):
                    classes = await table.get_attribute('class')
                    print(f"  Table {i}: class='{classes}'")

                    # Count rows
                    rows = await table.locator('tr').all()
                    print(f"           rows={len(rows)}")
            else:
                print("  [!] NO <table> ELEMENTS FOUND\n")

            # Check page title
            title = await page.title()
            print(f"\n[INFO] Page title: {title}")

            # Get body text (first 500 chars)
            body_text = await page.locator('body').inner_text()
            print(f"\n[INFO] Body text (first 500 chars):")
            print(body_text[:500])

            # Check for common React table elements
            print(f"\n[INFO] Checking for React/Material-UI components...")

            mui_tables = await page.locator('[class*="MuiTable"]').all()
            print(f"  MuiTable elements: {len(mui_tables)}")

            data_grids = await page.locator('[class*="MuiDataGrid"]').all()
            print(f"  MuiDataGrid elements: {len(data_grids)}")

            divs_with_table = await page.locator('div[class*="table"]').all()
            print(f"  Divs with 'table' in class: {len(divs_with_table)}")

            # Get HTML snippet
            html = await page.content()
            print(f"\n[INFO] HTML length: {len(html)} characters")
            print(f"\n[DEBUG] First 1000 chars of HTML:")
            print("=" * 80)
            print(html[:1000])
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
    asyncio.run(inspect_eybl())
