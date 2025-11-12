"""
Test MN Hub Adapter with Improved Selectors

Tests if the MN Hub adapter can now successfully extract player data
with improved table filtering and increased timeout.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import MNHubDataSource


async def test_mn_hub_search():
    """Test MN Hub player search with improved selectors."""
    print("=" * 80)
    print("TESTING: MN Hub with Improved Selectors")
    print("=" * 80)

    adapter = None
    try:
        # Initialize adapter
        print("\n[1] Initializing MN Hub adapter...")
        adapter = MNHubDataSource()
        print(f"[OK] Adapter initialized")
        print(f"     Base URL: {adapter.base_url}")
        print(f"     Season: {adapter.season}")
        print(f"     Leaderboards URL: {adapter.leaderboards_url}")
        print(f"     Browser timeout: {adapter.browser_client.timeout}ms")

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
                print(f"      Name: {player.full_name}")
                print(f"      Team: {player.team_name}")
                print(f"      Position: {player.position}")
                print(f"      State: {player.school_state}")
                print(f"      Level: {player.level}")
        else:
            print(f"[WARN] No players found")
            print(f"   Possible causes:")
            print(f"      1. Off-season (2025-26 season not started yet)")
            print(f"      2. Stats tables not loading")
            print(f"      3. Table filtering too aggressive")

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
    asyncio.run(test_mn_hub_search())
