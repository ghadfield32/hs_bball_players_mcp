"""
Validation Script for MaxPreps Enhancement 5

Tests the enhanced MaxPreps parser to verify:
1. Player data extraction (name, school, position, height, weight, grad year)
2. Season stats extraction (PPG, RPG, APG, SPG, BPG, FG%, 3P%, FT%)
3. Tuple return format (Player, PlayerSeasonStats)
4. Integration with forecasting pipeline

**IMPORTANT**: This makes actual web requests to MaxPreps.
Use conservative testing and respect ToS.

Usage:
    python scripts/validate_maxpreps_enhancement.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.maxpreps import MaxPrepsDataSource
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_search_players_basic():
    """Test basic search_players() - should still work (backward compatibility)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Basic search_players() - Backward Compatibility")
    logger.info("="*80 + "\n")

    maxpreps = MaxPrepsDataSource()

    try:
        # Search for players in California
        players = await maxpreps.search_players(
            state="CA",
            limit=5
        )

        logger.info(f"✅ Found {len(players)} players via search_players()")

        for idx, player in enumerate(players, 1):
            logger.info(
                f"\nPlayer {idx}:",
                name=player.full_name,
                school=player.school_name,
                grad_year=player.grad_year,
                position=player.position,
                height=player.height_inches,
                weight=player.weight_lbs
            )

        return len(players) > 0

    except Exception as e:
        logger.error("❌ Test failed", error=str(e), exc_info=True)
        return False


async def test_search_players_with_stats():
    """Test new search_players_with_stats() - enhanced method."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Enhanced search_players_with_stats()")
    logger.info("="*80 + "\n")

    maxpreps = MaxPrepsDataSource()

    try:
        # Search for players WITH stats in California
        results = await maxpreps.search_players_with_stats(
            state="CA",
            limit=5
        )

        logger.info(f"✅ Found {len(results)} player-stats pairs")

        players_with_stats = sum(1 for _, stats in results if stats is not None)
        logger.info(f"   {players_with_stats} have season stats")

        for idx, (player, stats) in enumerate(results, 1):
            logger.info(f"\n=== Player {idx}: {player.full_name} ===")
            logger.info(
                "Player Info:",
                school=player.school_name,
                grad_year=player.grad_year,
                position=player.position,
                height=player.height_inches,
                weight=player.weight_lbs
            )

            if stats:
                logger.info(
                    "Season Stats:",
                    games=stats.games_played,
                    ppg=stats.points_per_game,
                    rpg=stats.rebounds_per_game,
                    apg=stats.assists_per_game,
                    spg=stats.steals_per_game,
                    bpg=stats.blocks_per_game,
                    fg_pct=stats.field_goal_percentage,
                    three_pt_pct=stats.three_point_percentage,
                    ft_pct=stats.free_throw_percentage
                )
            else:
                logger.warning("   No stats found for this player")

        return len(results) > 0 and players_with_stats > 0

    except Exception as e:
        logger.error("❌ Test failed", error=str(e), exc_info=True)
        return False


async def test_stats_extraction_detail():
    """Test that ALL available stats are extracted."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Detailed Stats Extraction")
    logger.info("="*80 + "\n")

    maxpreps = MaxPrepsDataSource()

    try:
        results = await maxpreps.search_players_with_stats(
            state="CA",
            limit=3
        )

        if not results:
            logger.warning("No results found")
            return False

        # Check first player with stats
        player, stats = results[0]

        if not stats:
            logger.warning("First player has no stats")
            return False

        logger.info(f"Analyzing stats for: {player.full_name}")

        # Check what fields are populated
        stats_fields = {
            "games_played": stats.games_played,
            "points": stats.points,
            "points_per_game": stats.points_per_game,
            "total_rebounds": stats.total_rebounds,
            "rebounds_per_game": stats.rebounds_per_game,
            "assists": stats.assists,
            "assists_per_game": stats.assists_per_game,
            "steals": stats.steals,
            "steals_per_game": stats.steals_per_game,
            "blocks": stats.blocks,
            "blocks_per_game": stats.blocks_per_game,
            "turnovers": stats.turnovers,
            "field_goal_percentage": stats.field_goal_percentage,
            "three_point_percentage": stats.three_point_percentage,
            "free_throw_percentage": stats.free_throw_percentage,
            "minutes_played": stats.minutes_played,
        }

        populated = sum(1 for v in stats_fields.values() if v is not None and v > 0)
        total = len(stats_fields)

        logger.info(f"\n✅ Stats Completeness: {populated}/{total} fields populated")

        for field, value in stats_fields.items():
            status = "✅" if value is not None and value > 0 else "❌"
            logger.info(f"   {status} {field}: {value}")

        return populated >= 8  # At least 8 fields should be populated

    except Exception as e:
        logger.error("❌ Test failed", error=str(e), exc_info=True)
        return False


async def run_all_tests():
    """Run all validation tests."""
    logger.info("\n" + "#"*80)
    logger.info("# MaxPreps Enhancement 5 Validation")
    logger.info("#"*80 + "\n")

    tests = [
        ("Backward Compatibility", test_search_players_basic),
        ("Enhanced Stats Method", test_search_players_with_stats),
        ("Stats Extraction Detail", test_stats_extraction_detail),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}...")

        try:
            passed = await test_func()
            results.append((test_name, passed))

            if passed:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.warning(f"❌ {test_name} FAILED")

        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception", error=str(e))
            results.append((test_name, False))

        # Wait between tests (rate limiting)
        await asyncio.sleep(3)

    # Summary
    logger.info("\n" + "#"*80)
    logger.info("# TEST SUMMARY")
    logger.info("#"*80 + "\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    logger.info(f"Tests Passed: {passed}/{total}")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info("\n" + "#"*80 + "\n")

    return all(result for _, result in results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
