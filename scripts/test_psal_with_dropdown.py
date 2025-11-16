"""
Test PSAL with Dropdown Interaction

Tests loading PSAL stats by properly selecting the current season
from the dropdown and waiting for API response.

Usage:
    python scripts/test_psal_with_dropdown.py

Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright


async def test_psal_with_dropdowns():
    """Test PSAL page with proper dropdown interaction."""
    print("=" * 80)
    print("PSAL DROPDOWN INTERACTION TEST")
    print("=" * 80)

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001#001/Basketball"
    print(f"\nTarget URL: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("\n[1] Loading page...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        print(f"[OK] Page loaded: {await page.title()}")

        # Wait for dropdowns to appear
        print("\n[2] Waiting for dropdowns to load...")
        await page.wait_for_selector("#drpSeason", timeout=10000)
        await page.wait_for_selector("#drpCategor", timeout=10000)
        await page.wait_for_selector("#drpLeague", timeout=10000)
        print("[OK] Dropdowns loaded")

        # Check current selections
        print("\n[3] Checking default selections...")
        current_season = await page.locator("#drpSeason").input_value()
        current_category = await page.locator("#drpCategor").input_value()
        current_league = await page.locator("#drpLeague").input_value()

        print(f"  Season: {current_season}")
        print(f"  Category: {current_category}")
        print(f"  League: {current_league}")

        # Select current season (2024-2025)
        print("\n[4] Selecting 2024-2025 season...")
        await page.select_option("#drpSeason", value="2025")
        print("[OK] Season selected")

        # Select Points category (value=1)
        print("\n[5] Selecting Points category...")
        await page.select_option("#drpCategor", value="1")
        print("[OK] Category selected")

        # Wait for API call to complete
        print("\n[6] Waiting for stats to load (10 seconds)...")
        await asyncio.sleep(10)

        # Check if table has data
        print("\n[7] Checking for stat data...")
        table_html = await page.locator("#top_player_list").inner_html()

        if "No records found" in table_html:
            print("[FAIL] Still shows 'No records found'")
            print("\nTable HTML:")
            print(table_html[:500])
        else:
            print("[OK] Stats loaded!")

            # Count rows
            rows = await page.locator("#top_player_list table tbody tr").count()
            print(f"[OK] Found {rows} rows in stats table")

            # Get first few players
            if rows > 2:  # Skip header rows
                print("\nTop 5 Players:")
                for i in range(2, min(7, rows)):  # Skip header, get 5 players
                    row = page.locator("#top_player_list table tbody tr").nth(i)
                    cells = await row.locator("td").all_text_contents()
                    if len(cells) >= 5:
                        rank = cells[0] if len(cells) > 0 else "?"
                        player = cells[1] if len(cells) > 1 else "?"
                        grade = cells[2] if len(cells) > 2 else "?"
                        school = cells[3] if len(cells) > 3 else "?"
                        points = cells[4] if len(cells) > 4 else "?"
                        print(f"  {rank}. {player:<25} Grade {grade:<3} {school:<30} {points} pts")

        # Save screenshot
        print("\n[8] Saving screenshot...")
        await page.screenshot(path="data/debug/psal_with_dropdowns.png", full_page=True)
        print("[OK] Screenshot saved: data/debug/psal_with_dropdowns.png")

        # Save HTML
        html = await page.content()
        with open("data/debug/psal_with_dropdowns.html", "w", encoding='utf-8') as f:
            f.write(html)
        print("[OK] HTML saved: data/debug/psal_with_dropdowns.html")

        # Keep browser open for inspection
        print("\n[9] Keeping browser open for 15 seconds for manual inspection...")
        print("(Press Ctrl+C to close early)")
        try:
            await asyncio.sleep(15)
        except KeyboardInterrupt:
            print("\nClosing...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_psal_with_dropdowns())
