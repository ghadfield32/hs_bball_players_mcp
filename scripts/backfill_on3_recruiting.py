"""
Historical Backfill Script for On3/Rivals Recruiting Data

Fetches rankings for a range of years and loads into DuckDB:
- Raw layer: on3_player_rankings_raw (source-shaped, reproducible)
- Normalized layer: player_recruiting (modeling-ready)
- Coverage: recruiting_coverage (metadata tracking)

Features:
- Idempotent: Safe to re-run for any year
- Resumable: Tracks progress, skips already-loaded years
- Two-layer storage: Raw + Normalized
- Coverage tracking: Metadata for QA

Usage:
    python scripts/backfill_on3_recruiting.py --start 2020 --end 2025
    python scripts/backfill_on3_recruiting.py --year 2024  # Single year
    python scripts/backfill_on3_recruiting.py --start 2020 --end 2025 --force  # Re-fetch existing

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource
from src.services.recruiting_duckdb import RecruitingDuckDBStorage
from src.services.recruiting_pipeline import RecruitingPipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


class On3Backfiller:
    """
    Backfill manager for On3/Rivals recruiting data.

    Orchestrates:
    1. Fetching rankings from On3
    2. Writing raw data to on3_player_rankings_raw
    3. Normalizing and writing to player_recruiting
    4. Updating coverage metadata
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize backfiller.

        Args:
            db_path: Path to DuckDB file (optional)
        """
        self.storage = RecruitingDuckDBStorage(db_path=db_path)
        self.pipeline = RecruitingPipeline()
        self.on3 = None  # Will be created per-year to avoid browser issues

    async def backfill_year(
        self,
        year: int,
        force: bool = False,
        limit: int = 5000
    ) -> dict:
        """
        Backfill a single year.

        Args:
            year: Class year to backfill
            force: Force re-fetch even if data exists
            limit: Max players to fetch (default: 5000 for full coverage)

        Returns:
            Dict with backfill results
        """
        logger.info(f"Starting backfill for {year}", force=force)

        # Check if already loaded (unless force=True)
        if not force:
            existing = self.storage.conn.execute(
                "SELECT COUNT(*) as cnt FROM player_recruiting WHERE source = 'on3_industry' AND class_year = ?",
                [year]
            ).fetchone()

            if existing and existing[0] > 0:
                logger.info(f"Year {year} already loaded ({existing[0]} players), skipping (use --force to re-fetch)")
                return {
                    "year": year,
                    "status": "skipped",
                    "reason": "already_loaded",
                    "existing_count": existing[0]
                }

        # Step 1: Fetch rankings from On3
        logger.info(f"Fetching rankings for {year}...")
        scraped_at = datetime.utcnow()

        self.on3 = On3DataSource()
        try:
            rankings = await self.on3.get_rankings(class_year=year, limit=limit)

            if not rankings:
                logger.warning(f"No rankings found for {year}")
                return {
                    "year": year,
                    "status": "no_data",
                    "players_fetched": 0
                }

            logger.info(f"Fetched {len(rankings)} rankings for {year}")

            # Step 2: Write raw data to on3_player_rankings_raw
            logger.info(f"Writing {len(rankings)} rankings to raw table...")
            raw_df = self.pipeline.normalize_on3_raw_to_dataframe(
                rankings=rankings,
                class_year=year,
                scraped_at=scraped_at
            )

            # Register DataFrame as DuckDB relation for SQL access
            self.storage.conn.register("on3_raw_tmp", raw_df)

            # Delete existing raw data for this year (idempotent)
            self.storage.conn.execute(
                "DELETE FROM on3_player_rankings_raw WHERE class_year = ?",
                [year]
            )

            # Insert raw data from temporary view
            self.storage.conn.execute(
                "INSERT INTO on3_player_rankings_raw SELECT * FROM on3_raw_tmp"
            )

            # Unregister temporary view (cleanup)
            self.storage.conn.unregister("on3_raw_tmp")

            logger.info(f"Wrote {len(raw_df)} raw rankings for {year}")

            # Step 3: Normalize and write to player_recruiting
            logger.info(f"Normalizing {len(rankings)} rankings...")
            normalized_df = self.pipeline.normalize_on3_to_player_recruiting(
                rankings=rankings,
                source="on3_industry"
            )

            # Register DataFrame as DuckDB relation for SQL access
            self.storage.conn.register("player_recruiting_tmp", normalized_df)

            # Delete existing normalized data (idempotent)
            recruiting_ids = normalized_df['recruiting_id'].tolist()
            if recruiting_ids:
                placeholders = ','.join(['?'] * len(recruiting_ids))
                self.storage.conn.execute(
                    f"DELETE FROM player_recruiting WHERE recruiting_id IN ({placeholders})",
                    recruiting_ids
                )

            # Insert normalized data from temporary view
            self.storage.conn.execute(
                "INSERT INTO player_recruiting SELECT * FROM player_recruiting_tmp"
            )

            # Unregister temporary view (cleanup)
            self.storage.conn.unregister("player_recruiting_tmp")

            logger.info(f"Wrote {len(normalized_df)} normalized rankings for {year}")

            # Step 4: Update coverage metadata
            n_ranked = sum(1 for r in rankings if r.rank_national is not None)
            n_stars = sum(1 for r in rankings if r.stars is not None)
            n_ratings = sum(1 for r in rankings if r.rating is not None)
            n_committed = sum(1 for r in rankings if r.committed_to is not None)

            self.storage.upsert_coverage(
                source="on3_industry",
                class_year=year,
                n_players=len(rankings),
                n_players_expected=None,
                n_players_with_ranks=n_ranked,
                n_players_with_stars=n_stars,
                n_players_with_ratings=n_ratings,
                n_players_committed=n_committed,
                notes=f"Backfilled on {scraped_at.strftime('%Y-%m-%d')}"
            )

            logger.info(f"Updated coverage for {year}")

            return {
                "year": year,
                "status": "success",
                "players_fetched": len(rankings),
                "players_raw": len(raw_df),
                "players_normalized": len(normalized_df),
                "scraped_at": scraped_at
            }

        except Exception as e:
            logger.error(f"Error backfilling {year}: {e}", exc_info=True)
            return {
                "year": year,
                "status": "error",
                "error": str(e)
            }

        finally:
            # Cleanup browser
            if self.on3 and hasattr(self.on3, 'browser_client'):
                try:
                    await self.on3.browser_client.close()
                except:
                    pass

    async def backfill_range(
        self,
        start_year: int,
        end_year: int,
        force: bool = False,
        limit: int = 5000
    ) -> list:
        """
        Backfill a range of years.

        Args:
            start_year: First year to backfill
            end_year: Last year to backfill
            force: Force re-fetch even if data exists
            limit: Max players per year

        Returns:
            List of result dicts
        """
        logger.info(f"Starting backfill for {start_year}-{end_year}")

        results = []

        for year in range(start_year, end_year + 1):
            result = await self.backfill_year(year=year, force=force, limit=limit)
            results.append(result)

            # Small delay between years to avoid rate limiting
            await asyncio.sleep(1)

        return results

    def close(self):
        """Close storage connection."""
        if self.storage:
            self.storage.close()


def print_backfill_summary(results: list):
    """Print formatted backfill summary."""
    print("\n" + "=" * 80)
    print("ON3/RIVALS BACKFILL SUMMARY")
    print("=" * 80)
    print(f"{'Year':<8} {'Status':<12} {'Players':<10} {'Raw':<8} {'Normalized':<12} {'Notes'}")
    print("-" * 80)

    total_players = 0
    years_success = 0
    years_skipped = 0
    years_failed = 0

    for result in results:
        year = result["year"]
        status = result["status"]

        if status == "success":
            players = result.get("players_fetched", 0)
            raw = result.get("players_raw", 0)
            normalized = result.get("players_normalized", 0)
            print(f"{year:<8} {status:<12} {players:<10} {raw:<8} {normalized:<12}")
            total_players += players
            years_success += 1

        elif status == "skipped":
            reason = result.get("reason", "")
            existing = result.get("existing_count", 0)
            print(f"{year:<8} {status:<12} {'—':<10} {'—':<8} {existing:<12} {reason}")
            years_skipped += 1

        elif status == "no_data":
            print(f"{year:<8} {status:<12} {'0':<10} {'—':<8} {'—':<12} No data found")

        else:  # error
            error = result.get("error", "Unknown error")[:40]
            print(f"{year:<8} {status:<12} {'—':<10} {'—':<8} {'—':<12} {error}")
            years_failed += 1

    print("-" * 80)
    print(f"SUCCESS: {years_success} years, {total_players:,} total players")
    print(f"SKIPPED: {years_skipped} years (already loaded)")
    print(f"FAILED: {years_failed} years")
    print("=" * 80)
    print()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Backfill On3/Rivals recruiting data")
    parser.add_argument(
        "--start",
        type=int,
        help="Start year (inclusive)"
    )
    parser.add_argument(
        "--end",
        type=int,
        help="End year (inclusive)"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Single year to backfill (alternative to --start/--end)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetch even if data already exists"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Max players per year (default: 5000)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to DuckDB file (default: data/duckdb/recruiting.duckdb)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.year:
        start_year = end_year = args.year
    elif args.start and args.end:
        start_year = args.start
        end_year = args.end
    else:
        parser.error("Must specify either --year or both --start and --end")

    # Run backfill
    backfiller = On3Backfiller(db_path=args.db)

    try:
        results = await backfiller.backfill_range(
            start_year=start_year,
            end_year=end_year,
            force=args.force,
            limit=args.limit
        )

        print_backfill_summary(results)

    finally:
        backfiller.close()


if __name__ == "__main__":
    asyncio.run(main())
