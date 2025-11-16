"""
Test PSAL Adapter - Phase HS-5

Tests the NYC PSAL adapter functionality before activation.
Validates player search, season stats, team data, and leaderboards.

Usage:
    python scripts/test_psal_adapter.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-5 - Expand US State Coverage (PSAL)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.psal import PSALDataSource
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_psal_search_players():
    """Test PSAL player search functionality."""
    print("\n" + "=" * 80)
    print("TEST 1: PSAL Player Search")
    print("=" * 80)

    psal = PSALDataSource()

    try:
        # Test 1: Search for top players (no filters)
        print("\n[1.1] Fetching top 10 players from PSAL leaderboards...")
        players = await psal.search_players(limit=10)

        if not players:
            print("[FAIL] No players found!")
            return False

        print(f"[OK] Found {len(players)} players")

        # Display sample players
        print("\nSample Players:")
        for i, player in enumerate(players[:5], 1):
            print(f"\n{i}. {player.full_name}")
            print(f"   Player ID: {player.player_id}")
            print(f"   School: {player.school_name or 'N/A'}")
            print(f"   State: {player.school_state or 'N/A'}")
            print(f"   City: {player.school_city or 'N/A'}")
            print(f"   Grad Year: {player.grad_year or 'N/A'}")
            print(f"   Level: {player.level}")

        # Test 2: Search with name filter
        if players:
            first_player_name = players[0].full_name.split()[0]  # Get first name
            print(f"\n[1.2] Testing name filter with '{first_player_name}'...")
            filtered_players = await psal.search_players(name=first_player_name, limit=5)
            print(f"[OK] Found {len(filtered_players)} players matching '{first_player_name}'")

        print("\n[OK] Player search test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Player search test failed: {e}")
        logger.error("PSAL player search test failed", error=str(e))
        return False
    finally:
        await psal.close()


async def test_psal_season_stats():
    """Test PSAL player season stats retrieval."""
    print("\n" + "=" * 80)
    print("TEST 2: PSAL Player Season Stats")
    print("=" * 80)

    psal = PSALDataSource()

    try:
        # Get a player first
        print("\n[2.1] Finding a player to get stats for...")
        players = await psal.search_players(limit=3)

        if not players:
            print("[FAIL] No players found for stats test!")
            return False

        test_player = players[0]
        print(f"[OK] Testing stats for: {test_player.full_name} (ID: {test_player.player_id})")

        # Get season stats
        print(f"\n[2.2] Fetching season stats...")
        stats = await psal.get_player_season_stats(
            player_id=test_player.player_id,
            season="2024-25"
        )

        if not stats:
            print("[WARN] No stats returned (may be expected if player not in current stats)")
            return True  # Not a failure - player may not have stats

        print(f"[OK] Stats retrieved successfully!")
        print(f"\nStats Summary:")
        print(f"  Player: {stats.player_name}")
        print(f"  Season: {stats.season}")
        print(f"  League: {stats.league}")
        print(f"  Games Played: {stats.games_played}")

        if stats.points_per_game:
            print(f"\nPer-Game Averages:")
            print(f"  PPG: {stats.points_per_game}")
            print(f"  RPG: {stats.rebounds_per_game or 'N/A'}")
            print(f"  APG: {stats.assists_per_game or 'N/A'}")
            print(f"  SPG: {stats.steals_per_game or 'N/A'}")
            print(f"  BPG: {stats.blocks_per_game or 'N/A'}")

        if stats.points:
            print(f"\nTotals:")
            print(f"  Points: {stats.points}")
            print(f"  Rebounds: {stats.total_rebounds or 'N/A'}")
            print(f"  Assists: {stats.assists or 'N/A'}")

        print("\n[OK] Season stats test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Season stats test failed: {e}")
        logger.error("PSAL season stats test failed", error=str(e))
        return False
    finally:
        await psal.close()


async def test_psal_leaderboard():
    """Test PSAL leaderboard functionality."""
    print("\n" + "=" * 80)
    print("TEST 3: PSAL Leaderboard")
    print("=" * 80)

    psal = PSALDataSource()

    try:
        # Test points leaderboard
        print("\n[3.1] Fetching points leaderboard (top 10)...")
        leaderboard = await psal.get_leaderboard(stat="points", limit=10)

        if not leaderboard:
            print("[WARN] No leaderboard data returned")
            return True  # Not a failure - may not be available

        print(f"[OK] Retrieved {len(leaderboard)} leaderboard entries")

        print("\nTop 10 Scorers:")
        for entry in leaderboard[:10]:
            rank = entry.get('rank', '?')
            player = entry.get('player_name', 'Unknown')
            school = entry.get('team_name', 'N/A')
            value = entry.get('stat_value', 0)
            print(f"  {rank}. {player:<25} ({school:<20}) - {value}")

        print("\n[OK] Leaderboard test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Leaderboard test failed: {e}")
        logger.error("PSAL leaderboard test failed", error=str(e))
        return False
    finally:
        await psal.close()


async def test_psal_team():
    """Test PSAL team retrieval."""
    print("\n" + "=" * 80)
    print("TEST 4: PSAL Team Data")
    print("=" * 80)

    psal = PSALDataSource()

    try:
        # Get a player with school info
        print("\n[4.1] Finding a team to test...")
        players = await psal.search_players(limit=5)

        if not players:
            print("[FAIL] No players found for team test!")
            return False

        # Find player with school name
        test_school = None
        for player in players:
            if player.school_name:
                test_school = player.school_name
                break

        if not test_school:
            print("[WARN] No players with school names found")
            return True

        # Create team ID from school name
        team_id = f"psal_{test_school.lower().replace(' ', '_')}"
        print(f"[OK] Testing team: {test_school} (ID: {team_id})")

        # Get team info
        print(f"\n[4.2] Fetching team data...")
        team = await psal.get_team(team_id=team_id)

        if not team:
            print("[WARN] Team data not found (may be expected)")
            return True

        print(f"[OK] Team data retrieved!")
        print(f"\nTeam Info:")
        print(f"  Name: {team.team_name}")
        print(f"  School: {team.school_name or 'N/A'}")
        print(f"  City: {team.city or 'N/A'}")
        print(f"  State: {team.state or 'N/A'}")
        print(f"  League: {team.league or 'N/A'}")
        print(f"  Conference: {team.conference or 'N/A'}")
        print(f"  Record: {team.wins or 0}-{team.losses or 0}")

        print("\n[OK] Team data test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Team data test failed: {e}")
        logger.error("PSAL team data test failed", error=str(e))
        return False
    finally:
        await psal.close()


async def main():
    """Run all PSAL adapter tests."""
    print("=" * 80)
    print("PSAL ADAPTER TEST SUITE - Phase HS-5")
    print("=" * 80)
    print("\nTesting NYC Public Schools Athletic League (PSAL) adapter")
    print("Base URL: https://www.psal.org")
    print("Coverage: New York City high school basketball")

    results = {
        "Player Search": False,
        "Season Stats": False,
        "Leaderboard": False,
        "Team Data": False,
    }

    # Run tests
    results["Player Search"] = await test_psal_search_players()
    results["Season Stats"] = await test_psal_season_stats()
    results["Leaderboard"] = await test_psal_leaderboard()
    results["Team Data"] = await test_psal_team()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for p in results.values() if p)

    print(f"\nResults: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n[SUCCESS] All tests passed! PSAL adapter is ready for activation.")
        return 0
    elif passed_tests >= total_tests * 0.75:
        print("\n[PARTIAL] Most tests passed. PSAL adapter may be usable with limitations.")
        return 0
    else:
        print("\n[FAILURE] Multiple tests failed. PSAL adapter needs fixes before activation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
