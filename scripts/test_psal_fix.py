"""
Test PSAL Adapter - Data Exists Investigation

The debug script found 5 tables with 15 rows on the PSAL leaders page.
This test investigates why the adapter isn't extracting that data.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import PSALDataSource


async def test_psal_search():
    """Test PSAL player search to see why data isn't being extracted."""
    print("=" * 80)
    print("TESTING: PSAL (NYC) - Data Exists Investigation")
    print("=" * 80)
    print("Debug script found 5 tables with 15 rows - investigating why no data extracted")

    adapter = None
    try:
        # Initialize adapter
        print("\n[1] Initializing PSAL adapter...")
        adapter = PSALDataSource()
        print(f"[OK] Adapter initialized")
        print(f"     Base URL: {adapter.base_url}")
        print(f"     Leaders URL: {adapter.leaders_url}")

        # Test health check
        print("\n[2] Testing health check...")
        health = await adapter.health_check()
        print(f"[OK] Health check: {health}")

        # Test player search
        print("\n[3] Searching for players (limit=10)...")
        players = await adapter.search_players(limit=10)

        if players and len(players) > 0:
            print(f"[SUCCESS] Found {len(players)} players!")
            print(f"\n[4] Player details:")
            for i, player in enumerate(players, 1):
                print(f"\n   Player #{i}:")
                print(f"      Name: {player.name}")
                print(f"      Team: {player.team_name}")
                print(f"      Position: {player.position}")
                print(f"      Level: {player.level}")
        else:
            print(f"[ISSUE] No players found despite debug script finding 15 rows of data!")
            print(f"\n   Possible causes:")
            print(f"      1. Adapter looking at wrong table (5 tables exist)")
            print(f"      2. Parsing logic broken (column names changed)")
            print(f"      3. ASP.NET form submission required")
            print(f"      4. Data in table but not in expected format")
            print(f"\n   Next steps:")
            print(f"      - Check adapter's table selection logic")
            print(f"      - Inspect _parse_player_from_leaders_row method")
            print(f"      - Verify which of the 5 tables has player data")

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
    asyncio.run(test_psal_search())
