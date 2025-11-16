"""
Debug script to identify why 2025 fails.

Removes all defensive coding to expose the real error.
Adds detailed step-by-step logging.

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource


async def debug_2025():
    """Debug 2025 rankings fetch with detailed logging."""

    print("\n" + "=" * 80)
    print("DEBUG: On3 2025 Rankings Fetch")
    print("=" * 80 + "\n")

    # Step 1: Initialize On3DataSource
    print("[STEP 1] Initializing On3DataSource...")
    on3 = On3DataSource()
    print(f"  - On3DataSource created: {on3}")
    print(f"  - Browser client: {on3.browser_client}")
    print()

    # Step 2: Construct URL
    year = 2025
    url = f"https://www.on3.com/rivals/rankings/industry-player/basketball/{year}/"
    print(f"[STEP 2] Target URL: {url}")
    print()

    # Step 3: Fetch rankings (NO try-catch - let errors bubble up)
    print("[STEP 3] Calling get_rankings()...")
    print(f"  - class_year: {year}")
    print(f"  - limit: 100")
    print()

    # NO TRY-CATCH - Let the error surface
    rankings = await on3.get_rankings(class_year=year, limit=100)

    print(f"[STEP 4] Success! Got {len(rankings)} rankings")
    if rankings:
        print(f"  - First player: {rankings[0].player_name}")
        print(f"  - Rank: #{rankings[0].rank_national}")
    print()

    # Cleanup
    print("[STEP 5] Cleaning up browser...")
    if hasattr(on3, 'browser_client') and on3.browser_client:
        await on3.browser_client.close()
    print("  - Browser closed")
    print()

    print("=" * 80)
    print("DEBUG COMPLETE - NO ERRORS")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_2025())
