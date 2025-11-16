"""
Coverage Discovery Script for On3/Rivals Recruiting Data

Measures data availability across all years and writes metadata to DuckDB.

This script:
1. Loops through years 2000-2027
2. Fetches rankings for each year (limit=5000 for full coverage)
3. Calculates quality metrics (ranks, stars, ratings, commits)
4. Writes coverage metadata to recruiting_coverage table
5. Outputs summary showing coverage by year

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource
from src.services.recruiting_duckdb import RecruitingDuckDBStorage
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def discover_year_coverage(year: int) -> dict:
    """
    Discover coverage for a single year.

    Args:
        year: Class year to check

    Returns:
        Dict with coverage metrics
    """
    logger.info(f"Discovering coverage for {year}...")

    # Create fresh On3 instance for each year (avoids browser context issues)
    on3 = On3DataSource()

    try:
        # Fetch all rankings for this year (high limit to get full coverage)
        rankings = await on3.get_rankings(class_year=year, limit=5000)

        if not rankings:
            logger.warning(f"No data found for {year}")
            return {
                "year": year,
                "n_players": 0,
                "has_data": False,
            }

        # Calculate quality metrics
        n_players = len(rankings)
        n_with_ranks = sum(1 for r in rankings if r.rank_national is not None)
        n_with_stars = sum(1 for r in rankings if r.stars is not None)
        n_with_ratings = sum(1 for r in rankings if r.rating is not None)
        n_committed = sum(1 for r in rankings if r.committed_to is not None)

        # Check for ranking gaps
        ranks = [r.rank_national for r in rankings if r.rank_national is not None]
        has_gaps = False
        if ranks:
            sorted_ranks = sorted(ranks)
            expected_ranks = list(range(1, len(sorted_ranks) + 1))
            has_gaps = sorted_ranks != expected_ranks

        logger.info(
            f"[OK] {year}: {n_players} players, "
            f"{n_with_ranks} ranked, "
            f"{n_with_stars} with stars, "
            f"{n_committed} committed"
        )

        return {
            "year": year,
            "n_players": n_players,
            "n_players_with_ranks": n_with_ranks,
            "n_players_with_stars": n_with_stars,
            "n_players_with_ratings": n_with_ratings,
            "n_players_committed": n_committed,
            "has_gaps": has_gaps,
            "has_data": True,
            "top_player": rankings[0].player_name if rankings else None,
        }

    except Exception as e:
        logger.error(f"[ERROR] Error discovering {year}: {e}")
        return {
            "year": year,
            "n_players": 0,
            "has_data": False,
            "error": str(e),
        }
    finally:
        # Clean up browser resources
        try:
            if hasattr(on3, 'browser_client') and on3.browser_client:
                await on3.browser_client.close()
        except Exception:
            pass  # Ignore cleanup errors


async def discover_all_coverage(
    start_year: int = 2000,
    end_year: int = 2027,
    db_path: str = None
) -> list:
    """
    Discover coverage for all years and write to DuckDB.

    Args:
        start_year: First year to check (default: 2000)
        end_year: Last year to check (default: 2027)
        db_path: Path to DuckDB file (optional)

    Returns:
        List of coverage dicts
    """
    logger.info(f"Starting coverage discovery for {start_year}-{end_year}")

    # Initialize DuckDB storage
    storage = RecruitingDuckDBStorage(db_path=db_path)

    coverage_results = []

    # Loop through all years
    for year in range(start_year, end_year + 1):
        coverage = await discover_year_coverage(year)
        coverage_results.append(coverage)

        # Write to DuckDB if we have data
        if coverage.get("has_data"):
            storage.upsert_coverage(
                source="on3_industry",
                class_year=year,
                n_players=coverage["n_players"],
                n_players_expected=None,  # On3 doesn't provide expected count in all cases
                n_players_with_ranks=coverage.get("n_players_with_ranks"),
                n_players_with_stars=coverage.get("n_players_with_stars"),
                n_players_with_ratings=coverage.get("n_players_with_ratings"),
                n_players_committed=coverage.get("n_players_committed"),
                has_gaps=coverage.get("has_gaps"),
                notes=f"Top player: {coverage.get('top_player', 'N/A')}"
            )

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    # Close storage
    storage.close()

    return coverage_results


def print_coverage_summary(coverage_results: list) -> None:
    """
    Print formatted coverage summary.

    Args:
        coverage_results: List of coverage dicts
    """
    print("\n" + "=" * 80)
    print("ON3/RIVALS COVERAGE DISCOVERY SUMMARY")
    print("=" * 80)
    print(f"{'Year':<8} {'Players':<10} {'Ranked':<10} {'Stars':<10} {'Committed':<12} {'Top Player'}")
    print("-" * 80)

    total_players = 0
    years_with_data = 0

    for coverage in coverage_results:
        year = coverage["year"]

        if coverage["has_data"]:
            n_players = coverage["n_players"]
            n_ranked = coverage.get("n_players_with_ranks", 0)
            n_stars = coverage.get("n_players_with_stars", 0)
            n_committed = coverage.get("n_players_committed", 0)
            top_player = coverage.get("top_player", "N/A")

            print(
                f"{year:<8} {n_players:<10} {n_ranked:<10} {n_stars:<10} "
                f"{n_committed:<12} {top_player[:40]}"
            )

            total_players += n_players
            years_with_data += 1
        else:
            error_msg = coverage.get("error", "No data")
            print(f"{year:<8} {'—':<10} {'—':<10} {'—':<10} {'—':<12} {error_msg[:40]}")

    print("-" * 80)
    print(f"TOTAL: {years_with_data} years with data, {total_players:,} total players")
    print("=" * 80)
    print("\n[OK] Coverage metadata written to recruiting_coverage table")
    print("     Query: SELECT * FROM recruiting_coverage ORDER BY class_year")
    print()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Discover On3/Rivals coverage across all years")
    parser.add_argument(
        "--start-year",
        type=int,
        default=2000,
        help="First year to check (default: 2000)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2027,
        help="Last year to check (default: 2027)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to DuckDB file (default: data/duckdb/recruiting.duckdb)"
    )

    args = parser.parse_args()

    # Discover coverage
    coverage_results = await discover_all_coverage(
        start_year=args.start_year,
        end_year=args.end_year,
        db_path=args.db_path
    )

    # Print summary
    print_coverage_summary(coverage_results)


if __name__ == "__main__":
    asyncio.run(main())
