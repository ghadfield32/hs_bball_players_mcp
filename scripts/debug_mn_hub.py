#!/usr/bin/env python3
"""
MN Hub Website Structure Analysis
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime


async def analyze_mn_hub():
    """Analyze MN Hub website structure."""

    # Try main site to see what exists
    url = "https://stats.mnbasketballhub.com"
    season_str = "main"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[...] Loading {url}")
        print(f"[...] Season: {season_str}")

        try:
            await page.goto(url, wait_until='load', timeout=30000)
            print(f"[OK] Page loaded (waiting for content...)")
            await page.wait_for_timeout(10000)  # Give more time for Angular
        except Exception as e:
            print(f"[!] Error loading page: {e}")
            await browser.close()
            return

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        print(f"[OK] Page loaded ({len(html)} chars)\n")

        # Check for tables
        all_tables = soup.find_all('table')
        print(f"[INFO] Found {len(all_tables)} <table> elements")

        if all_tables:
            for i, table in enumerate(all_tables, 1):
                classes = table.get('class', [])
                print(f"  Table {i}: class={classes}")

                # Count rows
                rows = table.find_all('tr')
                print(f"           rows={len(rows)}")

                # Show headers if available
                if rows:
                    headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                    if headers:
                        print(f"           headers={headers[:10]}")
        else:
            print("  [!] NO <table> ELEMENTS FOUND\n")

        # Check page title
        title = await page.title()
        print(f"\n[INFO] Page title: {title}")

        # Get body text (first 500 chars)
        body_text = await page.locator('body').inner_text()
        print(f"\n[INFO] Body text (first 800 chars):")
        print(body_text[:800])

        # Check for Angular/common stat elements
        print(f"\n[INFO] Checking for stat elements...")

        # Check for divs with data
        stat_divs = soup.find_all('div', class_=lambda x: x and 'stat' in str(x).lower())
        print(f"  Divs with 'stat' in class: {len(stat_divs)}")

        leader_divs = soup.find_all('div', class_=lambda x: x and 'leader' in str(x).lower())
        print(f"  Divs with 'leader' in class: {len(leader_divs)}")

        # Check for specific classes
        rows_divs = soup.find_all('div', class_=lambda x: x and 'row' in str(x).lower())
        print(f"  Divs with 'row' in class: {len(rows_divs)}")

        # Find all links
        print(f"\n[INFO] Finding navigation links...")
        links = soup.find_all('a', href=True)

        # Filter for leaderboard/stats related links
        stat_links = [
            (link.get_text(strip=True), link['href'])
            for link in links
            if any(keyword in link.get_text(strip=True).lower() or keyword in link['href'].lower()
                   for keyword in ['leader', 'stat', 'historical', 'archive'])
        ]

        print(f"\n[INFO] Found {len(stat_links)} stats/leaderboard links:")
        for text, href in stat_links[:20]:
            print(f"  '{text}' -> {href}")

        # Show HTML snippet
        print(f"\n[DEBUG] First 1500 chars of HTML:")
        print("=" * 80)
        print(html[:1500])
        print("=" * 80)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_mn_hub())
