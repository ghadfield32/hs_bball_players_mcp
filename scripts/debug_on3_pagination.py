"""
Debug pagination metadata for 2025.

Shows exactly what pagination info On3 provides.

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource


async def debug_pagination():
    """Debug pagination metadata extraction."""

    print("\n" + "=" * 80)
    print("DEBUG: On3 Pagination Metadata for 2025")
    print("=" * 80 + "\n")

    on3 = On3DataSource()

    year = 2025
    url = f"https://www.on3.com/rivals/rankings/industry-player/basketball/{year}/"

    print(f"Fetching: {url}\n")

    # Fetch HTML
    html = await on3.browser_client.get_rendered_html(
        url=url,
        wait_for="script#__NEXT_DATA__",
        wait_timeout=30000,
    )

    print(f"HTML length: {len(html)} chars\n")

    # Extract __NEXT_DATA__
    script_match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
        html,
        re.DOTALL
    )

    if not script_match:
        print("ERROR: __NEXT_DATA__ script not found")
        return

    next_data_json = script_match.group(1)
    data = json.loads(next_data_json)

    print("=" * 80)
    print("NEXT_DATA__ STRUCTURE:")
    print("=" * 80)
    print(json.dumps(data, indent=2)[:2000])  # First 2000 chars
    print("...\n")

    # Check for 404
    page_type = data.get('page', '')
    print(f"Page type: {page_type}")

    if page_type == '/404':
        print("⚠️  THIS IS A 404 PAGE!")
        print()
        return

    # Extract player data
    try:
        player_list = data['props']['pageProps']['playerData']['list']
        print(f"\n✅ Found {len(player_list)} players in playerData.list")
    except KeyError as e:
        print(f"\n❌ Could not find playerData.list: {e}")
        player_list = []

    # Extract pagination
    try:
        pagination = data['props']['pageProps']['playerData']['pagination']
        print("\n" + "=" * 80)
        print("PAGINATION METADATA:")
        print("=" * 80)
        print(json.dumps(pagination, indent=2))
        print()

        # Check critical fields
        page_count = pagination.get('pageCount')
        total_count = pagination.get('count')
        items_per_page = pagination.get('itemsPerPage')

        print("\nCRITICAL PAGINATION FIELDS:")
        print(f"  - pageCount: {page_count}")
        print(f"  - count (total): {total_count}")
        print(f"  - itemsPerPage: {items_per_page}")
        print()

        if page_count == 1:
            print("✅ pageCount == 1, so there is ONLY ONE PAGE")
            print("   → Should NOT try to fetch page 2")
        else:
            print(f"⚠️  pageCount == {page_count}, multiple pages exist")

    except KeyError as e:
        print(f"\n❌ Could not find pagination: {e}")

    # Cleanup
    await on3.browser_client.close()

    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_pagination())
