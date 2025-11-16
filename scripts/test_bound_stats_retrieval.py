"""Test if Bound adapter returns stats with values"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.bound import BoundDataSource


async def main():
    bound = BoundDataSource()

    try:
        # Test Iowa - we know this works from Phase HS-2
        print("Fetching top 5 players from Iowa...")
        players = await bound.search_players(state="IA", limit=5)

        if not players:
            print("ERROR: No players found!")
            return

        print(f"Found {len(players)} players")

        # Get stats for first player
        first_player = players[0]
        print(f"\nTesting stats for: {first_player.full_name} (ID: {first_player.player_id})")

        stats = await bound.get_player_season_stats(
            player_id=first_player.player_id,
            state="IA",
            season="2024-25"
        )

        if not stats:
            print("ERROR: No stats returned!")
            return

        print(f"\n[OK] Stats retrieved successfully!")
        print(f"Player Name: {stats.player_name}")
        print(f"Season: {stats.season}")
        print(f"League: {stats.league}")
        print(f"Games Played: {stats.games_played}")
        print(f"\nSTAT VALUES:")
        print(f"  Points: {stats.points}")
        print(f"  Three Pointers Made: {stats.three_pointers_made}")
        print(f"  Total Rebounds: {stats.total_rebounds}")
        print(f"  Assists: {stats.assists}")
        print(f"  Steals: {stats.steals}")
        print(f"  Blocks: {stats.blocks}")
        print(f"  Points Per Game: {stats.points_per_game}")
        print(f"  Rebounds Per Game: {stats.rebounds_per_game}")
        print(f"  Assists Per Game: {stats.assists_per_game}")

    finally:
        await bound.close()


if __name__ == "__main__":
    asyncio.run(main())
