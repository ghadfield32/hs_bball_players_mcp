#!/usr/bin/env python
"""
Fetch Real EYBL Player Data

Scrapes real player statistics from Nike EYBL website using the EYBL adapter
and exports to Parquet format compatible with the HS forecasting pipeline.

Features:
- Async batch fetching with progress tracking
- Automatic retry on failures (3 attempts with exponential backoff)
- Export to both DuckDB and Parquet
- Schema validation
- Summary statistics

Usage:
    # Fetch all players and export to Parquet
    python scripts/fetch_real_eybl_data.py --output data/raw/eybl/player_season_stats.parquet

    # Fetch limited number with DuckDB storage
    python scripts/fetch_real_eybl_data.py --limit 100 --save-to-duckdb

    # Custom season
    python scripts/fetch_real_eybl_data.py --season 2024-25 --output eybl_2024.parquet

Created: 2025-11-15
Phase: 15 (Real Data Integration)
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
from tqdm import tqdm

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from datasources.us.eybl import EYBLDataSource
from hs_forecasting.schema_validator import validate_eybl_schema
from models import PlayerSeasonStats
from services.duckdb_storage import get_duckdb_storage

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def fetch_eybl_players_with_retry(
    adapter: EYBLDataSource,
    max_retries: int = 3,
    limit: Optional[int] = None,
) -> List[PlayerSeasonStats]:
    """
    Fetch EYBL player season stats with retry logic.

    Args:
        adapter: EYBL adapter instance
        max_retries: Maximum retry attempts
        limit: Optional limit on number of players

    Returns:
        List of PlayerSeasonStats objects
    """
    all_stats = []
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.info(f"Fetching EYBL players (attempt {retry_count + 1}/{max_retries})")

            # Search for all players
            players = await adapter.search_players(limit=limit or 1000)

            if not players:
                logger.warning("No players found, retrying...")
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                continue

            logger.info(f"Found {len(players)} players, fetching season stats...")

            # Fetch season stats for each player with progress bar
            with tqdm(total=len(players), desc="Fetching stats") as pbar:
                for player in players:
                    try:
                        stats = await adapter.get_player_season_stats(player.player_id)
                        if stats:
                            all_stats.append(stats)
                        pbar.update(1)
                    except Exception as e:
                        logger.debug(f"Failed to fetch stats for {player.player_id}: {e}")
                        pbar.update(1)
                        continue

            logger.info(f"Successfully fetched {len(all_stats)} player season stats")
            break

        except Exception as e:
            logger.error(f"Fetch attempt {retry_count + 1} failed: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
            else:
                logger.error("Max retries reached, returning partial data")
                break

    return all_stats


def convert_stats_to_dataframe(stats: List[PlayerSeasonStats]) -> pd.DataFrame:
    """
    Convert PlayerSeasonStats objects to DataFrame in dataset_builder format.

    Args:
        stats: List of PlayerSeasonStats objects

    Returns:
        DataFrame with standardized columns
    """
    if not stats:
        logger.warning("No stats to convert")
        return pd.DataFrame()

    data = []
    for stat in stats:
        row = {
            "player_name": stat.player_name,
            "player_id": stat.player_id,
            "team_id": stat.team_id,
            "season": stat.season,
            "league": stat.league,
            "gp": stat.games_played,
            "games_started": stat.games_started,
            # Per-game averages
            "pts_per_game": stat.points_per_game,
            "reb_per_game": stat.rebounds_per_game,
            "ast_per_game": stat.assists_per_game,
            "stl_per_game": stat.steals_per_game,
            "blk_per_game": stat.blocks_per_game,
            # Totals (if available)
            "points": stat.points,
            "field_goals_made": stat.field_goals_made,
            "field_goals_attempted": stat.field_goals_attempted,
            "three_pointers_made": stat.three_pointers_made,
            "three_pointers_attempted": stat.three_pointers_attempted,
            "free_throws_made": stat.free_throws_made,
            "free_throws_attempted": stat.free_throws_attempted,
            "total_rebounds": stat.total_rebounds,
            "assists": stat.assists,
            "steals": stat.steals,
            "blocks": stat.blocks,
            "turnovers": stat.turnovers,
            # Computed percentages
            "fg_pct": stat.field_goal_percentage,
            "three_pct": stat.three_point_percentage,
            "ft_pct": stat.free_throw_percentage,
        }
        data.append(row)

    df = pd.DataFrame(data)
    logger.info(f"Converted {len(df)} stats to DataFrame")

    return df


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Fetch real EYBL player data for HS forecasting"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/eybl/player_season_stats.parquet"),
        help="Output Parquet file path",
    )

    parser.add_argument(
        "--season",
        type=str,
        default=None,
        help="Season to fetch (e.g., '2024-25'). Uses current if not specified.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of players to fetch",
    )

    parser.add_argument(
        "--save-to-duckdb",
        action="store_true",
        help="Also save to DuckDB storage",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate schema after export (default: True)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("="*70)
    logger.info("EYBL REAL DATA FETCHER")
    logger.info("="*70)

    start_time = time.time()

    # Initialize EYBL adapter
    logger.info("Initializing EYBL adapter...")
    adapter = EYBLDataSource()

    # Fetch data
    logger.info(f"Fetching EYBL data (season: {args.season or 'current'}, limit: {args.limit or 'all'})")
    stats = await fetch_eybl_players_with_retry(
        adapter=adapter,
        max_retries=3,
        limit=args.limit,
    )

    if not stats:
        logger.error("Failed to fetch any player stats!")
        await adapter.close()
        sys.exit(1)

    logger.info(f"✅ Fetched {len(stats)} player season stats")

    # Convert to DataFrame
    logger.info("Converting to DataFrame...")
    df = convert_stats_to_dataframe(stats)

    # Validate schema if requested
    if args.validate:
        logger.info("Validating schema...")
        validation_result = validate_eybl_schema(df)

        if validation_result.is_valid:
            logger.info("✅ Schema validation PASSED")
        else:
            logger.warning("⚠️  Schema validation FAILED")
            print(validation_result)

    # Save to Parquet
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving to Parquet: {args.output}")
    df.to_parquet(args.output, index=False)

    # Save to DuckDB if requested
    if args.save_to_duckdb:
        logger.info("Saving to DuckDB...")
        try:
            duckdb = get_duckdb_storage()
            if duckdb:
                # Store player season stats
                stored_count = await duckdb.store_player_season_stats(stats)
                logger.info(f"✅ Stored {stored_count} stats in DuckDB")
        except Exception as e:
            logger.error(f"Failed to save to DuckDB: {e}")

    # Summary statistics
    elapsed = time.time() - start_time
    logger.info("="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Total players: {len(df)}")
    logger.info(f"Output file: {args.output}")
    logger.info(f"File size: {args.output.stat().st_size / 1024:.1f} KB")
    logger.info(f"Elapsed time: {elapsed:.1f}s")

    # Sample statistics
    if not df.empty:
        logger.info("\nSample Stats:")
        if "pts_per_game" in df.columns:
            logger.info(f"  PPG mean: {df['pts_per_game'].mean():.1f}")
            logger.info(f"  PPG max: {df['pts_per_game'].max():.1f}")
        if "gp" in df.columns:
            logger.info(f"  GP mean: {df['gp'].mean():.1f}")

        logger.info(f"\nSample players:")
        print(df[['player_name', 'pts_per_game', 'reb_per_game', 'ast_per_game']].head(10))

    logger.info("="*70)
    logger.info("✅ EYBL data fetch complete!")
    logger.info("="*70)

    # Cleanup
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
