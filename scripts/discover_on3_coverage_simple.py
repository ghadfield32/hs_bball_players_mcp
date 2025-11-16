"""
Simple Coverage Discovery Script for On3/Rivals

Pragmatic approach - measures data availability with basic error handling.
Browser cleanup warnings are expected on Windows and can be ignored.

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource
from src.services.recruiting_duckdb import RecruitingDuckDBStorage


async def discover_year(year: int) -> dict:
    """Discover coverage for a single year."""
    print(f"Checking {year}...", end=" ", flush=True)

    on3 = On3DataSource()

    try:
        # Use smaller limit to avoid pagination issues
        rankings = await on3.get_rankings(class_year=year, limit=100)

        if not rankings:
            print("NO DATA")
            return {"year": year, "has_data": False}

        # Calculate metrics
        n_players = len(rankings)
        n_ranked = sum(1 for r in rankings if r.rank_national is not None)
        n_stars = sum(1 for r in rankings if r.stars is not None)
        n_ratings = sum(1 for r in rankings if r.rating is not None)
        n_committed = sum(1 for r in rankings if r.committed_to is not None)

        print(f"OK - {n_players} players, {n_ranked} ranked, {n_committed} committed")

        return {
            "year": year,
            "has_data": True,
            "n_players": n_players,
            "n_players_with_ranks": n_ranked,
            "n_players_with_stars": n_stars,
            "n_players_with_ratings": n_ratings,
            "n_players_committed": n_committed,
            "top_player": rankings[0].player_name if rankings else None,
        }

    except Exception as e:
        # Print full error for debugging
        import traceback
        print(f"ERROR")
        print(f"  Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"year": year, "has_data": False, "error": str(e)}
    finally:
        # Best-effort cleanup (ignore errors)
        try:
            if hasattr(on3, 'browser_client') and on3.browser_client:
                await on3.browser_client.close()
        except:
            pass


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2020, help="Start year")
    parser.add_argument("--end", type=int, default=2027, help="End year")
    parser.add_argument("--db", type=str, default=None, help="DuckDB path")

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"On3/Rivals Coverage Discovery ({args.start}-{args.end})")
    print(f"{'='*70}\n")

    # Initialize storage
    storage = RecruitingDuckDBStorage(db_path=args.db)

    results = []

    # Loop through years
    for year in range(args.start, args.end + 1):
        result = await discover_year(year)
        results.append(result)

        # Write to DuckDB
        if result["has_data"]:
            storage.upsert_coverage(
                source="on3_industry",
                class_year=year,
                n_players=result["n_players"],
                n_players_expected=None,
                n_players_with_ranks=result.get("n_players_with_ranks"),
                n_players_with_stars=result.get("n_players_with_stars"),
                n_players_with_ratings=result.get("n_players_with_ratings"),
                n_players_committed=result.get("n_players_committed"),
                notes=f"Top: {result.get('top_player', 'N/A')}"
            )

        # Small delay to avoid rate limiting
        await asyncio.sleep(1)

    # Close storage
    storage.close()

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    years_with_data = sum(1 for r in results if r["has_data"])
    total_players = sum(r.get("n_players", 0) for r in results if r["has_data"])

    print(f"Years with data: {years_with_data}/{len(results)}")
    print(f"Total players: {total_players:,}")
    print(f"\nCoverage data written to recruiting_coverage table")
    print(f"Query: SELECT * FROM recruiting_coverage ORDER BY class_year\n")


if __name__ == "__main__":
    asyncio.run(main())
