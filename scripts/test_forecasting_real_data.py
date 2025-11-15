"""
Real Data Forecasting Validation Script

Tests the forecasting data aggregation pipeline with REAL player data.

This script validates:
- Birth date extraction from 247Sports
- Age-for-grade calculations
- Multi-source stats aggregation
- Recruiting data integration (rankings, offers, predictions)
- Advanced metrics calculation
- Forecasting score computation

**IMPORTANT**: Run with caution - makes actual web requests.
Use conservative rate limiting and respect ToS.

Usage:
    python scripts/test_forecasting_real_data.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.forecasting import ForecastingDataAggregator
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ====================================================================
# TEST PLAYERS - Real high school and young European prospects
# ====================================================================

TEST_PLAYERS = [
    # === US High School (Class of 2025) ===
    {
        "name": "Cooper Flagg",
        "grad_year": 2025,
        "state": "ME",
        "expected_data": {
            "birth_date": "2006-12-21",  # Known to be older for his class
            "age_for_grade_category": "Old",  # Reclassified
            "power_6_offers": 20,  # Estimated minimum
            "stars": 5,
            "committed_to": "Duke",
        },
        "description": "#1 ranked player in 2025, Duke commit, plays for Montverde Academy"
    },

    # === US High School (Class of 2026) ===
    {
        "name": "Cameron Boozer",
        "grad_year": 2026,
        "state": "FL",
        "expected_data": {
            "power_6_offers": 15,
            "stars": 5,
            "committed_to": "Duke",  # Commits with twin brother
        },
        "description": "#1/#2 ranked 2026 player, Duke commit, son of Carlos Boozer"
    },

    # === US High School - Underrated Prospect ===
    {
        "name": "Dylan Harper",
        "grad_year": 2025,
        "state": "NJ",
        "expected_data": {
            "power_6_offers": 10,
            "stars": 5,
        },
        "description": "Top 10 2025 player, son of Ron Harper"
    },

    # === European Young Prospect ===
    {
        "name": "Noa Essengue",
        "grad_year": 2024,  # International - may be different year system
        "state": None,
        "expected_data": {
            "countries_played": ["EUROPE"],
            "circuits_played": [],  # No US circuits
        },
        "description": "French prospect, plays in ANGT/LNB Espoirs"
    },
]


async def test_single_player(agg: ForecastingDataAggregator, player_config: dict) -> dict:
    """
    Test forecasting data extraction for a single player.

    Args:
        agg: ForecastingDataAggregator instance
        player_config: Player configuration dictionary

    Returns:
        Test results dictionary
    """
    logger.info(
        f"\n{'='*80}\nTesting: {player_config['name']} ({player_config['description']})\n{'='*80}"
    )

    try:
        # Get comprehensive profile
        profile = await agg.get_comprehensive_player_profile(
            player_name=player_config["name"],
            grad_year=player_config.get("grad_year"),
            state=player_config.get("state"),
        )

        # Analyze results
        results = {
            "player_name": player_config["name"],
            "success": False,
            "data_found": {},
            "validations": {},
            "profile": profile,
        }

        # Check what data was found
        results["data_found"] = {
            "birth_date": profile["birth_date"] is not None,
            "age_for_grade": profile["age_for_grade"] is not None,
            "recruiting_data": profile["composite_247_rating"] is not None or profile["stars_247"] is not None,
            "stats_data": profile["total_seasons"] > 0,
            "offers": profile["total_offer_count"] > 0,
            "predictions": len(profile.get("raw_predictions", [])) > 0,
            "advanced_metrics": profile["best_ts_pct"] is not None,
        }

        # Validate against expected data
        expected = player_config.get("expected_data", {})
        for key, expected_value in expected.items():
            actual_value = profile.get(key)
            if actual_value is not None:
                if isinstance(expected_value, (int, float)):
                    # Numeric comparison with tolerance
                    results["validations"][key] = abs(actual_value - expected_value) <= expected_value * 0.2
                else:
                    # Exact match
                    results["validations"][key] = actual_value == expected_value
            else:
                results["validations"][key] = False

        # Print detailed results
        logger.info("\n=== DATA FOUND ===")
        for key, found in results["data_found"].items():
            status = "✅" if found else "❌"
            logger.info(f"{status} {key}: {found}")

        logger.info("\n=== KEY METRICS ===")
        key_metrics = {
            "Birth Date": profile.get("birth_date"),
            "Age-for-Grade": profile.get("age_for_grade"),
            "Age Category": profile.get("age_for_grade_category"),
            "Height": profile.get("height"),
            "Weight": profile.get("weight"),
            "Position": profile.get("position"),
            "247 Composite Rating": profile.get("composite_247_rating"),
            "247 Composite Rank": profile.get("composite_247_rank"),
            "Stars": profile.get("stars_247"),
            "ESPN Rank": profile.get("espn_rank"),
            "Rivals Rank": profile.get("rivals_rank"),
            "On3 Rank": profile.get("on3_rank"),
            "Power 6 Offers": profile.get("power_6_offer_count"),
            "Total Offers": profile.get("total_offer_count"),
            "Committed": profile.get("is_committed"),
            "Committed To": profile.get("committed_to"),
            "Prediction Consensus": profile.get("prediction_consensus"),
            "Prediction Confidence": profile.get("prediction_confidence"),
            "Total Seasons": profile.get("total_seasons"),
            "Total Games": profile.get("total_games_played"),
            "Career PPG": profile.get("career_ppg"),
            "Career RPG": profile.get("career_rpg"),
            "Career APG": profile.get("career_apg"),
            "Best TS%": profile.get("best_ts_pct"),
            "Best eFG%": profile.get("best_efg_pct"),
            "Best A/TO": profile.get("best_ato_ratio"),
            "Best Per-40 PPG": profile.get("best_per_40_ppg"),
            "Circuits Played": profile.get("circuits_played"),
            "Highest Competition": profile.get("highest_competition_level"),
            "Performance Trend": profile.get("performance_trend"),
            "Forecasting Score": profile.get("forecasting_score"),
            "Data Completeness": profile.get("data_completeness"),
        }

        for key, value in key_metrics.items():
            logger.info(f"  {key}: {value}")

        logger.info("\n=== VALIDATIONS ===")
        for key, passed in results["validations"].items():
            status = "✅" if passed else "❌"
            expected = expected[key]
            actual = profile.get(key)
            logger.info(f"{status} {key}: Expected ~{expected}, Got {actual}")

        # Overall success if we found critical data
        critical_data_found = (
            results["data_found"]["recruiting_data"] or
            results["data_found"]["stats_data"]
        )
        results["success"] = critical_data_found

        return results

    except Exception as e:
        logger.error(
            f"Failed to test player {player_config['name']}",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        return {
            "player_name": player_config["name"],
            "success": False,
            "error": str(e),
        }


async def run_all_tests():
    """Run forecasting tests on all test players."""
    logger.info(f"\n{'#'*80}\n# FORECASTING DATA AGGREGATION - REAL DATA TESTS\n{'#'*80}\n")

    # Initialize aggregator
    agg = ForecastingDataAggregator()
    logger.info("Forecasting aggregator initialized\n")

    # Run tests for each player
    all_results = []
    for player_config in TEST_PLAYERS:
        results = await test_single_player(agg, player_config)
        all_results.append(results)

        # Wait between players (rate limiting)
        await asyncio.sleep(2)

    # Summary
    logger.info(f"\n{'#'*80}\n# TEST SUMMARY\n{'#'*80}\n")

    successful = sum(1 for r in all_results if r["success"])
    total = len(all_results)

    logger.info(f"Tests Passed: {successful}/{total}")

    for result in all_results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        logger.info(f"{status} - {result['player_name']}")

        if result.get("profile"):
            profile = result["profile"]
            logger.info(f"  Forecasting Score: {profile.get('forecasting_score')}")
            logger.info(f"  Data Completeness: {profile.get('data_completeness')}%")
            logger.info(f"  Age-for-Grade: {profile.get('age_for_grade')} ({profile.get('age_for_grade_category')})")
            logger.info(f"  Power 6 Offers: {profile.get('power_6_offer_count')}")
            logger.info(f"  Best TS%: {profile.get('best_ts_pct')}")

    logger.info(f"\n{'#'*80}\n")

    return all_results


if __name__ == "__main__":
    # Run tests
    results = asyncio.run(run_all_tests())

    # Exit with error code if any tests failed
    success = all(r["success"] for r in results)
    sys.exit(0 if success else 1)
