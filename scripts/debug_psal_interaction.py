#!/usr/bin/env python3
"""
PSAL Website Interaction Analysis
Finds dropdowns, buttons, and interactive elements that might trigger data loading
"""

import asyncio
from playwright.async_api import async_playwright


async def analyze_psal_interactions():
    """Analyze PSAL website interactive elements."""

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001"

    print(f"[...] Launching browser for {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[...] Navigating to page...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print(f"[OK] Page loaded\n")

            # Find all select/dropdown elements
            selects = await page.locator('select').all()
            print(f"[INFO] Found {len(selects)} <select> elements:")
            for i, select in enumerate(selects, 1):
                name = await select.get_attribute('name')
                id_attr = await select.get_attribute('id')
                # Get options
                options = await select.locator('option').all()
                option_texts = []
                for opt in options[:5]:  # First 5 options
                    text = await opt.inner_text()
                    value = await opt.get_attribute('value')
                    option_texts.append(f"{text}={value}")
                print(f"  Select {i}: name='{name}' id='{id_attr}'")
                print(f"           options (first 5): {option_texts}")

            # Find all buttons
            buttons = await page.locator('button, input[type="button"], input[type="submit"]').all()
            print(f"\n[INFO] Found {len(buttons)} button elements:")
            for i, button in enumerate(buttons[:10], 1):
                text = await button.inner_text()
                value = await button.get_attribute('value')
                print(f"  Button {i}: text='{text}' value='{value}'")

            # Try clicking first select if it exists and selecting an option
            if len(selects) > 0:
                print(f"\n[...] Attempting to interact with first select...")
                first_select = selects[0]

                # Get all options
                options = await first_select.locator('option').all()
                if len(options) > 1:
                    # Select second option (first is usually placeholder)
                    option_value = await options[1].get_attribute('value')
                    option_text = await options[1].inner_text()
                    print(f"[...] Selecting option: '{option_text}' (value='{option_value}')")

                    await first_select.select_option(option_value)

                    # Wait for data to load
                    print(f"[...] Waiting 5 seconds for data to load...")
                    await page.wait_for_timeout(5000)

                    # Check tables again
                    tables = await page.locator('table').all()
                    print(f"[OK] Now found {len(tables)} <table> elements")

                    for i, table in enumerate(tables, 1):
                        rows = await table.locator('tr').all()
                        if len(rows) > 2:  # Has data rows
                            print(f"  Table {i}: {len(rows)} rows (HAS DATA!)")

                            # Show headers
                            header_row = rows[0]
                            cells = await header_row.locator('th, td').all()
                            headers = []
                            for cell in cells:
                                text = await cell.inner_text()
                                headers.append(text.strip())
                            print(f"           headers={headers[:10]}")

                            # Show first data row
                            if len(rows) > 1:
                                data_row = rows[1]
                                cells = await data_row.locator('td').all()
                                data = []
                                for cell in cells:
                                    text = await cell.inner_text()
                                    data.append(text.strip())
                                print(f"           first_data={data[:10]}")

            # Done analyzing
            print(f"\n[OK] Analysis complete")

        except Exception as e:
            print(f"\n[X] Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()
            print("\n[OK] Browser closed")


if __name__ == "__main__":
    asyncio.run(analyze_psal_interactions())
