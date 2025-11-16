"""
Test ANGT Adapter search_players() - Phase HS-4

Quick test to verify ANGT browser automation works before full activation.

Usage:
    python scripts/test_angt_search.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - ANGT Activation (Browser Automation)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.europe.angt import ANGTDataSource


async def test_angt_search():
    """Test ANGT player search with browser automation."""
    print("=" * 80)
    print("ANGT ADAPTER TEST - Browser Automation")
    print("=" * 80)

    angt = ANGTDataSource()

    try:
        # Test 1: Search for top players (no filters)
        print("\n[TEST 1] Fetching top 10 ANGT players...")
        players = await angt.search_players(limit=10)

        if not players:
            print("[FAIL] No players found!")
            print("\nPossible issues:")
            print("1. ANGT stats page structure changed")
            print("2. Browser automation selector mismatch")
            print("3. Network/timeout issues")
            return False

        print(f"[OK] Found {len(players)} players")

        # Display sample players
        print("\nSample Players:")
        for i, player in enumerate(players[:5], 1):
            print(f"\n{i}. {player.full_name}")
            print(f"   Player ID: {player.player_id}")
            print(f"   Club: {player.team_name or 'N/A'}")
            print(f"   Level: {player.level}")

        # Test 2: Search with name filter (if we have data)
        if players:
            first_player_name = players[0].full_name.split()[0]  # Get first name
            print(f"\n[TEST 2] Testing name filter with '{first_player_name}'...")
            filtered_players = await angt.search_players(name=first_player_name, limit=5)
            print(f"[OK] Found {len(filtered_players)} players matching '{first_player_name}'")

        print("\n[SUCCESS] All tests passed!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await angt.close()


if __name__ == "__main__":
    result = asyncio.run(test_angt_search())
    sys.exit(0 if result else 1)
