"""
Test On3/Rivals Historical Data Availability

Quick test to validate which years have data available before building full backfill.

Usage:
    python scripts/test_on3_historical_coverage.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_year_coverage(on3, year: int) -> dict:
    """
    Test if On3 has data for a specific year.

    Returns dict with: year, has_data, player_count, top_player
    """
    try:
        # Fetch just top 5 to test availability
        rankings = await on3.get_rankings(class_year=year, limit=5)

        has_data = len(rankings) > 0
        player_count = len(rankings)
        top_player = rankings[0].player_name if rankings else None

        return {
            "year": year,
            "has_data": has_data,
            "player_count": player_count,
            "top_player": top_player,
            "status": "✓" if has_data else "✗"
        }
    except Exception as e:
        logger.error(f"Error testing year {year}: {e}")
        return {
            "year": year,
            "has_data": False,
            "player_count": 0,
            "top_player": None,
            "status": "ERROR",
            "error": str(e)
        }


async def main():
    """Test historical coverage across multiple years."""
    from src.datasources.recruiting.on3 import On3DataSource

    logger.info("="*70)
    logger.info("Testing On3/Rivals Historical Data Availability")
    logger.info("="*70)
    logger.info("")

    on3 = On3DataSource()

    # Test years: 2020-2027 (current recruiting cycles)
    # Plus a few older years to test depth
    test_years = [
        # Far past
        2010, 2015,
        # Recent past
        2020, 2021, 2022, 2023, 2024,
        # Current
        2025,
        # Future
        2026, 2027, 2028
    ]

    logger.info(f"Testing {len(test_years)} years...")
    logger.info("")

    results = []
    for year in test_years:
        logger.info(f"Testing {year}...")
        result = await test_year_coverage(on3, year)
        results.append(result)

        # Add small delay to be respectful
        await asyncio.sleep(2)

    # Print summary
    logger.info("")
    logger.info("="*70)
    logger.info("COVERAGE SUMMARY")
    logger.info("="*70)
    logger.info("")
    logger.info(f"{'Year':<10} {'Status':<10} {'Players':<10} {'Top Ranked Player'}")
    logger.info("-"*70)

    for r in results:
        status = r['status']
        count = r['player_count'] if r['has_data'] else "-"
        top = r['top_player'] if r['top_player'] else "-"

        logger.info(f"{r['year']:<10} {status:<10} {count:<10} {top}")

    logger.info("")
    logger.info("="*70)

    # Summary stats
    years_with_data = [r for r in results if r['has_data']]
    if years_with_data:
        min_year = min(r['year'] for r in years_with_data)
        max_year = max(r['year'] for r in years_with_data)

        logger.info(f"Coverage Range: {min_year} - {max_year}")
        logger.info(f"Total Years with Data: {len(years_with_data)} / {len(results)}")
        logger.info("")
        logger.info("Recommended backfill range for production:")
        logger.info(f"  --from-year {min_year} --to-year {max_year}")
    else:
        logger.warning("No years found with data!")

    logger.info("="*70)


if __name__ == '__main__':
    asyncio.run(main())
