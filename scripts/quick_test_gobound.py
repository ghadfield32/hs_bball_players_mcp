"""
Quick test of GoBound to verify it actually provides player stats.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.bound import BoundDataSource


async def main():
    """Test GoBound Iowa."""
    print("Testing GoBound for Iowa")
    print("="*60)

    bound = BoundDataSource()

    # Test 1: Search for players
    print("\n[1] Searching for players in Iowa...")
    try:
        players = await bound.search_players(state="IA", limit=5)
        print(f"RESULT: Found {len(players)} players")

        if players:
            for i, player in enumerate(players, 1):
                print(f"  {i}. {player.full_name}")
                print(f"     ID: {player.player_id}")
                print(f"     School: {player.school_name or 'N/A'}")
                print(f"     Position: {player.position or 'N/A'}")

            # Test 2: Get stats for first player
            print(f"\n[2] Getting stats for: {players[0].full_name}")
            try:
                stats = await bound.get_player_season_stats(
                    player_id=players[0].player_id,
                    state="IA"
                )

                if stats:
                    print(f"RESULT: Got stats")
                    print(f"  Games: {stats.games_played or 'N/A'}")
                    print(f"  Points: {stats.points or stats.points_per_game or 'N/A'}")
                    print(f"  Rebounds: {stats.total_rebounds or stats.rebounds_per_game or 'N/A'}")
                    print(f"  Assists: {stats.assists or stats.assists_per_game or 'N/A'}")
                    print(f"  3PM: {stats.three_pointers_made or 'N/A'}")
                    print(f"  Steals: {stats.steals or 'N/A'}")
                    print(f"  Blocks: {stats.blocks or 'N/A'}")
                else:
                    print("RESULT: No stats returned")

            except Exception as e:
                print(f"ERROR getting stats: {e}")

        else:
            print("WARNING: No players found")

    except Exception as e:
        print(f"ERROR searching players: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await bound.close()


if __name__ == '__main__':
    asyncio.run(main())
