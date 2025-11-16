#!/usr/bin/env python3
"""
Simple script to fetch real EYBL player names for test cases.
Uses the EYBL adapter with browser automation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.eybl import EYBLDataSource


async def main():
    """Fetch player names from EYBL using browser automation."""
    print("Initializing EYBL datasource with browser automation...")

    ds = EYBLDataSource()

    try:
        # Search for players (will use browser automation)
        print("\nFetching top players from EYBL stats page...")
        print("This will use browser automation to render the React app...")

        players = await ds.search_players(limit=10)

        if not players:
            print("❌ No players found - browser automation may have failed")
            return

        print(f"\n✅ Successfully fetched {len(players)} players!\n")
        print("=" * 80)
        print("Real EYBL Players for Test Cases:")
        print("=" * 80)

        for i, player in enumerate(players[:5], 1):
            print(f"\n{i}. {player.full_name}")
            print(f"   Team: {player.team_name or 'N/A'}")
            print(f"   Player ID: {player.player_id}")

            # Try to get season stats for this player
            print(f"   Fetching season stats...")
            stats = await ds.get_player_season_stats(player.player_id)

            if stats:
                print(f"   Games: {stats.games_played or 'N/A'}")
                print(f"   PPG: {stats.points_per_game or 'N/A'}")
                print(f"   RPG: {stats.rebounds_per_game or 'N/A'}")
                print(f"   APG: {stats.assists_per_game or 'N/A'}")
            else:
                print(f"   ⚠️  Could not fetch stats")

        print("\n" + "=" * 80)
        print("\nYou can use these players in config/datasource_test_cases.yaml:")
        print("\neybl:")
        for i, player in enumerate(players[:3], 1):
            print(f"  - player_name: \"{player.full_name}\"")
            print(f"    season: \"2024\"")
            print(f"    team_hint: \"{player.team_name or 'Unknown'}\"")
            print(f"    expected_min_games: 1")
            print(f"    expected_min_ppg: 5.0")
            print(f"    expected_max_ppg: 50.0")
            print(f"    notes: \"Player {i} from 2024 season\"")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await ds.close()


if __name__ == "__main__":
    asyncio.run(main())
