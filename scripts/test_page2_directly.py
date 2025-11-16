"""
Test if page 2 exists for 2025 by fetching it directly.

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser_client import BrowserClient


async def test_page2():
    """Test page 2 directly."""

    print("\n" + "=" * 80)
    print("TEST: Direct fetch of 2025 Page 2")
    print("=" * 80 + "\n")

    browser = BrowserClient()

    url = "https://www.on3.com/rivals/rankings/industry-player/basketball/2025/2/"

    print(f"URL: {url}\n")
    print("Fetching...")

    try:
        html = await browser.get_rendered_html(
            url=url,
            wait_for="script#__NEXT_DATA__",
            wait_timeout=30000,
        )

        print(f"\n✅ SUCCESS - Page loaded ({len(html)} chars)")

        # Check for 404
        script_match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
            html,
            re.DOTALL
        )

        if script_match:
            data = json.loads(script_match.group(1))
            page_type = data.get('page', '')

            if page_type == '/404':
                print("❌ BUT it's a 404 page!")
            else:
                print(f"✅ Page type: {page_type}")

                # Count players
                try:
                    players = data['props']['pageProps']['playerData']['list']
                    print(f"✅ Found {len(players)} players")
                except:
                    print("❌ No player data found")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_page2())
