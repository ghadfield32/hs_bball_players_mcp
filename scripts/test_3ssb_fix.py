"""
Test 3SSB Adapter with Browser Automation Fix

Tests if the 3SSB adapter can now successfully extract player data
using Playwright for JavaScript rendering.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import ThreeSSBDataSource


async def test_3ssb_search():
    """Test 3SSB player search with browser automation."""
    print("=" * 80)
    print("TESTING: 3SSB with Browser Automation")
    print("=" * 80)

    adapter = None
    try:
        # Initialize adapter
        print("\n[1] Initializing 3SSB adapter...")
        adapter = ThreeSSBDataSource()
        print(f"[OK] Adapter initialized")
        print(f"     Base URL: {adapter.base_url}")
        print(f"     Stats URL: {adapter.stats_url}")
        print(f"     Browser client: {adapter.browser_client}")

        # Test health check
        print("\n[2] Testing health check...")
        health = await adapter.health_check()
        print(f"[OK] Health check: {health}")

        # Test player search
        print("\n[3] Searching for players (limit=5)...")
        players = await adapter.search_players(limit=5)

        if players and len(players) > 0:
            print(f"[SUCCESS] Found {len(players)} players!")
            print(f"\n[4] Player details:")
            for i, player in enumerate(players, 1):
                print(f"\n   Player #{i}:")
                print(f"      Name: {player.name}")
                print(f"      Team: {player.team_name}")
                print(f"      Position: {player.position}")
                print(f"      Grad Year: {player.grad_year}")
                print(f"      Level: {player.level}")
        else:
            print(f"[WARN] No players found")
            print(f"   Possible causes:")
            print(f"      1. Off-season (no data published)")
            print(f"      2. DataTables not rendering correctly")
            print(f"      3. Table structure changed")

        print(f"\n{'=' * 80}")
        print(f"TEST COMPLETE")
        print(f"{'=' * 80}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if adapter:
            await adapter.close()
            print(f"\n[OK] Adapter closed")


if __name__ == "__main__":
    asyncio.run(test_3ssb_search())
