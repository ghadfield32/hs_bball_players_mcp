"""
Fetch Real EYBL Data Script

Scrapes Nike EYBL player stats using the EYBL adapter and saves to:
1. Parquet file (for dataset building)
2. DuckDB (for analytics and querying)

Features:
- Retry logic with exponential backoff
- Progress tracking with tqdm
- Schema validation
- Deduplication
- Error handling and logging

Usage:
    python scripts/fetch_real_eybl_data.py --limit 100 --save-to-duckdb
    python scripts/fetch_real_eybl_data.py --season 2024 --output data/raw/eybl/stats.parquet

Author: Claude Code
Date: 2025-11-15
Phase: 15 - EYBL Data Pipeline
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.eybl import EYBLDataSource
from src.models import PlayerSeasonStats
from src.services.duckdb_storage import get_duckdb_storage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EYBLDataFetcher:
    """
    Fetches EYBL player stats and saves to Parquet + DuckDB.

    Handles pagination, retries, and data validation.
    """

    def __init__(
        self,
        output_path: str = "data/raw/eybl/player_season_stats.parquet",
        save_to_duckdb: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize EYBL data fetcher.

        Args:
            output_path: Path to output Parquet file
            save_to_duckdb: Whether to save to DuckDB
            max_retries: Maximum retries per player
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.save_to_duckdb = save_to_duckdb
        self.max_retries = max_retries

        self.eybl_source = None
        self.duckdb_storage = None

        logger.info(
            "EYBLDataFetcher initialized",
            output_path=str(self.output_path),
            save_to_duckdb=save_to_duckdb
        )

    async def initialize(self):
        """Initialize data sources and storage."""
        self.eybl_source = EYBLDataSource()

        if self.save_to_duckdb:
            self.duckdb_storage = get_duckdb_storage()

        logger.info("Data sources initialized")

    async def cleanup(self):
        """Clean up connections."""
        if self.eybl_source:
            await self.eybl_source.close()

        logger.info("Cleanup complete")

    async def fetch_all_players(
        self,
        limit: Optional[int] = None,
        season: Optional[str] = None
    ) -> List[dict]:
        """
        Fetch all EYBL players and their season stats.

        Args:
            limit: Maximum number of players to fetch
            season: Season filter (e.g., "2024")

        Returns:
            List of player stat dictionaries
        """
        logger.info(f"Fetching EYBL players (limit={limit}, season={season})")

        # Step 1: Search for all players
        logger.info("Step 1: Searching for all players in EYBL leaderboards")
        players = await self.eybl_source.search_players(
            season=season,
            limit=limit or 500  # Default to 500 if no limit
        )

        logger.info(f"Found {len(players)} players from leaderboards")

        if not players:
            logger.warning("No players found from EYBL")
            return []

        # Step 2: Fetch season stats for each player
        logger.info("Step 2: Fetching season stats for each player")
        player_stats = []

        with tqdm(total=len(players), desc="Fetching player stats") as pbar:
            for player in players:
                retries = 0
                while retries < self.max_retries:
                    try:
                        # Get season stats for this player
                        stats = await self.eybl_source.get_player_season_stats(
                            player_id=player.player_id,
                            season=season
                        )

                        if stats:
                            # Convert to dict for DataFrame
                            stat_dict = {
                                'player_id': stats.player_id,
                                'player_name': stats.player_name,
                                'team_id': stats.team_id,
                                'season': stats.season,
                                'games_played': stats.games_played,
                                'points_per_game': stats.points_per_game,
                                'rebounds_per_game': stats.rebounds_per_game,
                                'assists_per_game': stats.assists_per_game,
                                'steals_per_game': stats.steals_per_game,
                                'blocks_per_game': stats.blocks_per_game,
                                'field_goal_percentage': stats.field_goal_percentage,
                                'three_point_percentage': stats.three_point_percentage,
                                'free_throw_percentage': stats.free_throw_percentage,
                                'offensive_rebounds_per_game': stats.offensive_rebounds_per_game,
                                'defensive_rebounds_per_game': stats.defensive_rebounds_per_game,
                                'retrieved_at': datetime.now(),
                            }

                            player_stats.append(stat_dict)
                            pbar.set_postfix({
                                'current': player.full_name,
                                'stats_count': len(player_stats)
                            })

                        break  # Success, exit retry loop

                    except Exception as e:
                        retries += 1
                        logger.warning(
                            f"Failed to get stats for {player.full_name} (attempt {retries}/{self.max_retries})",
                            error=str(e)
                        )

                        if retries >= self.max_retries:
                            logger.error(f"Max retries exceeded for {player.full_name}")

                        await asyncio.sleep(1 * retries)  # Exponential backoff

                pbar.update(1)

        logger.info(f"Successfully fetched {len(player_stats)} player season stat records")
        return player_stats

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Validate DataFrame schema matches expected EYBL schema.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        required_columns = [
            'player_id', 'player_name', 'season', 'games_played',
            'points_per_game', 'rebounds_per_game', 'assists_per_game'
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False

        # Check for reasonable data ranges
        if len(df) > 0:
            if df['points_per_game'].max() > 100:
                logger.warning("Suspicious PPG values detected (>100)")

            if df['games_played'].max() > 100:
                logger.warning("Suspicious games_played values detected (>100)")

        logger.info("Schema validation passed")
        return True

    def save_to_parquet(self, df: pd.DataFrame) -> None:
        """
        Save DataFrame to Parquet file.

        Args:
            df: DataFrame to save
        """
        logger.info(f"Saving {len(df)} records to Parquet: {self.output_path}")

        # Convert datetime columns to ensure Parquet compatibility
        if 'retrieved_at' in df.columns:
            df['retrieved_at'] = pd.to_datetime(df['retrieved_at'])

        # Save with snappy compression (good balance of speed and size)
        df.to_parquet(
            self.output_path,
            index=False,
            compression='snappy',
            engine='pyarrow'
        )

        # Log file size
        file_size_mb = self.output_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Parquet file saved successfully",
            path=str(self.output_path),
            size_mb=f"{file_size_mb:.2f}"
        )

    async def save_to_duckdb_storage(self, df: pd.DataFrame) -> None:
        """
        Save DataFrame to DuckDB.

        Args:
            df: DataFrame to save
        """
        if not self.duckdb_storage:
            logger.warning("DuckDB storage not initialized, skipping")
            return

        logger.info(f"Saving {len(df)} records to DuckDB")

        # Convert DataFrame rows to PlayerSeasonStats objects
        stats_objects = []

        for _, row in df.iterrows():
            try:
                # Create minimal data source metadata
                from src.models.source import DataSource, DataSourceType, DataQualityFlag

                data_source = DataSource(
                    source_type=DataSourceType.EYBL,
                    url="https://nikeeyb.com/cumulative-season-stats",
                    quality_flag=DataQualityFlag.PARTIAL,
                    retrieved_at=row.get('retrieved_at', datetime.now())
                )

                stats = PlayerSeasonStats(
                    player_id=row['player_id'],
                    player_name=row['player_name'],
                    team_id=row.get('team_id', 'unknown'),
                    season=row['season'],
                    games_played=row['games_played'],
                    points_per_game=row.get('points_per_game'),
                    rebounds_per_game=row.get('rebounds_per_game'),
                    assists_per_game=row.get('assists_per_game'),
                    steals_per_game=row.get('steals_per_game'),
                    blocks_per_game=row.get('blocks_per_game'),
                    field_goal_percentage=row.get('field_goal_percentage'),
                    three_point_percentage=row.get('three_point_percentage'),
                    free_throw_percentage=row.get('free_throw_percentage'),
                    offensive_rebounds_per_game=row.get('offensive_rebounds_per_game'),
                    defensive_rebounds_per_game=row.get('defensive_rebounds_per_game'),
                    data_source=data_source
                )

                stats_objects.append(stats)

            except Exception as e:
                logger.warning(f"Failed to create PlayerSeasonStats for {row.get('player_name')}: {e}")

        # Store in DuckDB
        if stats_objects:
            stored_count = await self.duckdb_storage.store_player_stats(stats_objects)
            logger.info(f"Stored {stored_count} player stats in DuckDB")

    async def run(
        self,
        limit: Optional[int] = None,
        season: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Run the full EYBL data fetch pipeline.

        Args:
            limit: Maximum number of players
            season: Season filter

        Returns:
            DataFrame with fetched data
        """
        logger.info(
            "Starting EYBL data fetch pipeline",
            limit=limit,
            season=season
        )

        # Initialize
        await self.initialize()

        try:
            # Fetch data
            player_stats = await self.fetch_all_players(limit=limit, season=season)

            if not player_stats:
                logger.error("No player stats fetched")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(player_stats)

            # Remove duplicates (by player_id + season)
            df = df.drop_duplicates(subset=['player_id', 'season'])

            logger.info(
                f"Created DataFrame with {len(df)} records after deduplication",
                shape=df.shape
            )

            # Validate schema
            if not self.validate_schema(df):
                logger.error("Schema validation failed")
                return df

            # Save to Parquet
            self.save_to_parquet(df)

            # Save to DuckDB
            if self.save_to_duckdb:
                await self.save_to_duckdb_storage(df)

            logger.info("EYBL data fetch pipeline completed successfully")
            return df

        finally:
            # Cleanup
            await self.cleanup()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fetch real EYBL player data")

    parser.add_argument(
        '--output',
        type=str,
        default='data/raw/eybl/player_season_stats.parquet',
        help='Output Parquet file path'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of players to fetch (default: all)'
    )

    parser.add_argument(
        '--season',
        type=str,
        default=None,
        help='Season filter (e.g., "2024")'
    )

    parser.add_argument(
        '--save-to-duckdb',
        action='store_true',
        help='Save data to DuckDB (in addition to Parquet)'
    )

    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retries per player (default: 3)'
    )

    args = parser.parse_args()

    # Create fetcher
    fetcher = EYBLDataFetcher(
        output_path=args.output,
        save_to_duckdb=args.save_to_duckdb,
        max_retries=args.max_retries
    )

    # Run pipeline
    df = await fetcher.run(
        limit=args.limit,
        season=args.season
    )

    # Print summary
    if not df.empty:
        print("\n" + "="*60)
        print("EYBL Data Fetch Summary")
        print("="*60)
        print(f"Total players: {len(df)}")
        print(f"Seasons: {df['season'].unique().tolist()}")
        print(f"Output file: {args.output}")
        print(f"\nSample stats:")
        print(df[['player_name', 'season', 'games_played', 'points_per_game', 'rebounds_per_game']].head(10))
        print("="*60)
    else:
        print("\nNo data fetched")


if __name__ == '__main__':
    asyncio.run(main())
