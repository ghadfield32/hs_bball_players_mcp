#!/usr/bin/env python3
"""
Debug EYBL Website Structure

Inspects the actual HTML structure of the EYBL stats page to understand
why table selectors are failing.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser_client import BrowserClient
from src.utils.scraping_helpers import parse_html


async def debug_eybl_website():
    """Fetch and analyze EYBL website structure."""
    print("[...] Initializing browser client...")
    bc = BrowserClient()

    url = "https://nikeeyb.com/cumulative-season-stats"
    print(f"[...] Fetching URL: {url}")
    print("[...] Waiting for 'body' to render...")

    try:
        # First try: Wait for body element
        html = await bc.get_rendered_html(
            url=url,
            wait_for='body',
            wait_timeout=15000,
            wait_for_network_idle=True
        )

        print(f"\n[OK] Page loaded successfully!")
        print(f"[INFO] HTML length: {len(html)} characters\n")

        # Parse HTML
        soup = parse_html(html)

        # Check for tables
        tables = soup.find_all('table')
        print(f"[INFO] Found {len(tables)} <table> elements")

        if tables:
            for i, table in enumerate(tables, 1):
                classes = table.get('class', [])
                print(f"  Table {i}: classes={classes}")
                # Show first few rows
                rows = table.find_all('tr')
                print(f"           rows={len(rows)}")
                if rows:
                    headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                    print(f"           headers={headers[:10]}")
        else:
            print("  [!] NO TABLES FOUND")

        # Check for divs that might be used instead of tables
        print(f"\n[INFO] Checking for alternative structures...")

        # Common React table classes
        react_table_classes = [
            'MuiTable',
            'react-table',
            'data-table',
            'stats-table',
            'player-stats',
            'table',
        ]

        for class_name in react_table_classes:
            elements = soup.find_all(class_=lambda x: x and class_name.lower() in str(x).lower())
            if elements:
                print(f"  Found {len(elements)} elements with class containing '{class_name}'")
                for elem in elements[:2]:
                    print(f"    - {elem.name}: {elem.get('class')}")

        # Check for data grids
        grids = soup.find_all(class_=lambda x: x and 'grid' in str(x).lower())
        if grids:
            print(f"  Found {len(grids)} elements with 'grid' in class")
            for grid in grids[:2]:
                print(f"    - {grid.name}: {grid.get('class')}")

        # Show first 2000 characters of body for manual inspection
        print(f"\n[DEBUG] First 2000 chars of <body>:")
        print("=" * 80)
        body = soup.find('body')
        if body:
            print(body.get_text()[:2000])
        print("=" * 80)

        # Show raw HTML snippet
        print(f"\n[DEBUG] Raw HTML snippet (first 1500 chars):")
        print("=" * 80)
        print(html[:1500])
        print("=" * 80)

    except Exception as e:
        print(f"\n[X] Error: {e}")
        print(f"[X] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    finally:
        await bc.close()
        print("\n[OK] Browser closed")


if __name__ == "__main__":
    asyncio.run(debug_eybl_website())
