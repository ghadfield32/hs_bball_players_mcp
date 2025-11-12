"""
Simple WSN Investigation - No Adapter Imports

Investigates WSN website content without importing adapters.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup
from src.utils.http_client import HTTPClient


async def investigate():
    """Simple WSN investigation."""
    print("=" * 80)
    print("WSN WEBSITE INVESTIGATION (Phase 12.2)")
    print("=" * 80)

    client = HTTPClient(source="wsn_check")

    try:
        # Test main site
        print("\n[1] Main Site: https://www.wissports.net")
        html = await client.get_text("https://www.wissports.net", use_cache=False, timeout=15)
        print(f"    Fetched: {len(html):,} chars")

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('title')
        print(f"    Title: {title.get_text() if title else 'None'}")

        # Check indicators
        html_lower = html.lower()
        print(f"    Has 'basketball': {'basketball' in html_lower}")
        print(f"    Has 'stats': {'stats' in html_lower}")
        print(f"    Has 'player': {'player' in html_lower}")

        # Test basketball URLs
        print("\n[2] Testing Basketball URLs...")
        test_urls = [
            "https://www.wissports.net/basketball",
            "https://www.wissports.net/boys-basketball",
            "https://www.wissports.net/basketball/stats",
        ]

        for url in test_urls:
            try:
                print(f"\n    {url}")
                test_html = await client.get_text(url, use_cache=False, timeout=10)
                test_soup = BeautifulSoup(test_html, 'html.parser')
                tables = test_soup.find_all('table')
                print(f"      [OK] {len(test_html):,} chars, {len(tables)} tables")
            except Exception as e:
                print(f"      [FAIL] {type(e).__name__}")

        print("\n" + "=" * 80)
        print("INVESTIGATION COMPLETE")
        print("Check output above for basketball content indicators")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(investigate())
