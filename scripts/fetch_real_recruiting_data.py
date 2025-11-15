"""
Fetch Real Recruiting Rankings Script

Scrapes recruiting rankings from 247Sports and saves to:
1. Parquet file (for dataset building)
2. DuckDB (for analytics and querying)

Features:
- Multi-year fetching (2024-2029)
- Retry logic with exponential backoff
- Progress tracking with tqdm
- Schema validation
- Deduplication
- Error handling and logging

Usage:
    # Fetch rankings for specific years:
    python scripts/fetch_real_recruiting_data.py --class-years 2025,2026 --save-to-duckdb

    # Fetch rankings for year range:
    python scripts/fetch_real_recruiting_data.py --start-year 2024 --end-year 2026 --save-to-duckdb

    # Fetch with limit:
    python scripts/fetch_real_recruiting_data.py --class-years 2025 --limit 50 --save-to-duckdb

Author: Claude Code
Date: 2025-11-15
Phase: 15 - Recruiting Data Pipeline
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class RecruitingDataFetcher:
    """
    Fetches recruiting rankings from 247Sports and saves to Parquet + DuckDB.

    Handles multiple class years, retries, and data validation.
    """

    def __init__(
        self,
        output_path: str = "data/raw/recruiting/recruiting_ranks.parquet",
        save_to_duckdb: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize recruiting data fetcher.

        Args:
            output_path: Path to output Parquet file
            save_to_duckdb: Whether to save to DuckDB
            max_retries: Maximum retries per request
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.save_to_duckdb = save_to_duckdb
        self.max_retries = max_retries

        self.recruiting_source = None
        self.duckdb_storage = None

        logger.info(
            f"RecruitingDataFetcher initialized: output_path={str(self.output_path)}, save_to_duckdb={save_to_duckdb}"
        )

    async def initialize(self):
        """Initialize data sources and storage."""
        # Import here to avoid circular imports
        from src.datasources.recruiting.sports_247 import Sports247DataSource
        from src.services.duckdb_storage import get_duckdb_storage

        self.recruiting_source = Sports247DataSource()

        if self.save_to_duckdb:
            self.duckdb_storage = get_duckdb_storage()

        logger.info("Data sources initialized")

    async def cleanup(self):
        """Clean up connections."""
        if self.recruiting_source:
            await self.recruiting_source.close()

        logger.info("Cleanup complete")

    async def fetch_rankings_for_year(
        self,
        class_year: int,
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        Fetch recruiting rankings for a specific class year.

        Args:
            class_year: Graduation year (e.g., 2025)
            limit: Maximum number of rankings to fetch

        Returns:
            List of ranking dictionaries
        """
        logger.info(f"Fetching recruiting rankings for class {class_year}")

        rankings_list = []
        retries = 0

        while retries < self.max_retries:
            try:
                # Fetch rankings from 247Sports
                rankings = await self.recruiting_source.get_rankings(
                    class_year=class_year,
                    limit=limit or 100
                )

                logger.info(f"Found {len(rankings)} rankings for class {class_year}")

                # Convert to dict format
                for rank in rankings:
                    rank_dict = {
                        'player_id': rank.player_id,
                        'player_name': rank.player_name,
                        'rank_national': rank.rank_national,
                        'rank_position': rank.rank_position,
                        'rank_state': rank.rank_state,
                        'stars': rank.stars,
                        'rating': rank.rating,
                        'service': rank.service.value if rank.service else 'composite',
                        'class_year': rank.class_year,
                        'position': rank.position.value if rank.position else None,
                        'height': rank.height,
                        'weight': rank.weight,
                        'school': rank.school,
                        'city': rank.city,
                        'state': rank.state,
                        'committed_to': rank.committed_to,
                        'commitment_date': rank.commitment_date,
                        'profile_url': rank.profile_url,
                        'retrieved_at': datetime.now(),
                    }
                    rankings_list.append(rank_dict)

                break  # Success, exit retry loop

            except Exception as e:
                retries += 1
                logger.warning(
                    f"Failed to fetch rankings for class {class_year} (attempt {retries}/{self.max_retries}): {str(e)}"
                )

                if retries >= self.max_retries:
                    logger.error(f"Max retries exceeded for class {class_year}")
                    return []

                await asyncio.sleep(2 * retries)  # Exponential backoff

        return rankings_list

    async def fetch_all_rankings(
        self,
        class_years: List[int],
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        Fetch recruiting rankings for multiple class years.

        Args:
            class_years: List of graduation years
            limit: Maximum rankings per year

        Returns:
            Combined list of all rankings
        """
        logger.info(
            f"Fetching recruiting rankings for class years: {class_years}"
        )

        all_rankings = []

        with tqdm(total=len(class_years), desc="Fetching recruiting rankings") as pbar:
            for class_year in class_years:
                rankings = await self.fetch_rankings_for_year(
                    class_year=class_year,
                    limit=limit
                )

                all_rankings.extend(rankings)

                pbar.set_postfix({
                    'current_year': class_year,
                    'total_rankings': len(all_rankings)
                })
                pbar.update(1)

        logger.info(
            f"Successfully fetched {len(all_rankings)} total recruiting rankings"
        )
        return all_rankings

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Validate DataFrame schema matches expected recruiting schema.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        required_columns = [
            'player_id', 'player_name', 'class_year', 'rank_national', 'stars'
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False

        # Check for reasonable data ranges
        if len(df) > 0:
            if df['stars'].max() > 5 or df['stars'].min() < 0:
                logger.warning("Suspicious star rating values detected")

            if df['rank_national'].min() < 1:
                logger.warning("Suspicious rank values detected")

        logger.info("Schema validation passed")
        return True

    def save_to_parquet(self, df: pd.DataFrame) -> None:
        """
        Save DataFrame to Parquet file.

        Args:
            df: DataFrame to save
        """
        logger.info(f"Saving {len(df)} records to Parquet: {self.output_path}")

        # Convert datetime columns for Parquet compatibility
        if 'retrieved_at' in df.columns:
            df['retrieved_at'] = pd.to_datetime(df['retrieved_at'])
        if 'commitment_date' in df.columns:
            df['commitment_date'] = pd.to_datetime(df['commitment_date'])

        # Save with snappy compression
        df.to_parquet(
            self.output_path,
            index=False,
            compression='snappy',
            engine='pyarrow'
        )

        # Log file size
        file_size_mb = self.output_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Parquet file saved successfully: path={str(self.output_path)}, size_mb={file_size_mb:.2f}"
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

        # Convert DataFrame rows to RecruitingRank objects
        rank_objects = []

        # Helper function to convert NaN to None for Pydantic validation
        def nan_to_none(value):
            """Convert NaN values to None, which Pydantic accepts as Optional."""
            import math
            if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
                return None
            return value

        for idx, row in df.iterrows():
            try:
                from src.models import RecruitingRank
                from src.models.recruiting import RecruitingService
                from src.models.player import Position
                from src.models.source import DataSource, DataSourceType, DataSourceRegion, DataQualityFlag

                # Convert service string to enum
                service_str = row.get('service', 'composite')
                try:
                    service = RecruitingService(service_str)
                except ValueError:
                    service = RecruitingService.COMPOSITE

                # Convert position string to enum
                position_str = row.get('position')
                position = None
                if position_str:
                    try:
                        position = Position(position_str)
                    except ValueError:
                        pass

                # Create data source metadata
                data_source = DataSource(
                    source_name="247Sports",
                    source_type=DataSourceType.SPORTS_247,
                    region=DataSourceRegion.US,
                    url="https://247sports.com",
                    quality_flag=DataQualityFlag.VERIFIED,
                    retrieved_at=row.get('retrieved_at', datetime.now())
                )

                rank = RecruitingRank(
                    player_id=row['player_id'],
                    player_name=row['player_name'],
                    rank_national=nan_to_none(row.get('rank_national')),
                    rank_position=nan_to_none(row.get('rank_position')),
                    rank_state=nan_to_none(row.get('rank_state')),
                    stars=nan_to_none(row.get('stars')),
                    rating=nan_to_none(row.get('rating')),
                    service=service,
                    class_year=int(row['class_year']),
                    position=position,
                    height=nan_to_none(row.get('height')),
                    weight=nan_to_none(row.get('weight')),
                    school=nan_to_none(row.get('school')),
                    city=nan_to_none(row.get('city')),
                    state=nan_to_none(row.get('state')),
                    committed_to=nan_to_none(row.get('committed_to')),
                    commitment_date=nan_to_none(row.get('commitment_date')),
                    profile_url=nan_to_none(row.get('profile_url')),
                    data_source=data_source
                )

                rank_objects.append(rank)

            except Exception as e:
                logger.warning(
                    f"Failed to create RecruitingRank for {row.get('player_name')} (row {idx}): {e}"
                )

        # Store in DuckDB
        if rank_objects:
            stored_count = await self.duckdb_storage.store_recruiting_ranks(rank_objects)
            logger.info(f"Stored {stored_count} recruiting ranks in DuckDB")

    async def run(
        self,
        class_years: List[int],
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Run the full recruiting data fetch pipeline.

        Args:
            class_years: List of graduation years to fetch
            limit: Maximum rankings per year

        Returns:
            DataFrame with fetched data
        """
        logger.info(
            f"Starting recruiting data fetch pipeline: class_years={class_years}, limit={limit}"
        )

        # Initialize
        await self.initialize()

        try:
            # Fetch data
            rankings = await self.fetch_all_rankings(
                class_years=class_years,
                limit=limit
            )

            if not rankings:
                logger.error("No recruiting rankings fetched")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(rankings)

            # Remove duplicates (by player_id + service + class_year)
            df = df.drop_duplicates(subset=['player_id', 'service', 'class_year'])

            logger.info(
                f"Created DataFrame with {len(df)} records after deduplication: shape={df.shape}"
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

            logger.info("Recruiting data fetch pipeline completed successfully")
            return df

        finally:
            # Cleanup
            await self.cleanup()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch real recruiting rankings from 247Sports"
    )

    parser.add_argument(
        '--output',
        type=str,
        default='data/raw/recruiting/recruiting_ranks.parquet',
        help='Output Parquet file path'
    )

    parser.add_argument(
        '--class-years',
        type=str,
        default=None,
        help='Comma-separated list of class years (e.g., "2025,2026,2027")'
    )

    parser.add_argument(
        '--start-year',
        type=int,
        default=None,
        help='Start year for range (inclusive)'
    )

    parser.add_argument(
        '--end-year',
        type=int,
        default=None,
        help='End year for range (inclusive)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum rankings per year (default: 100)'
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
        help='Maximum retries per request (default: 3)'
    )

    args = parser.parse_args()

    # Determine class years to fetch
    if args.class_years:
        class_years = [int(y.strip()) for y in args.class_years.split(',')]
    elif args.start_year and args.end_year:
        class_years = list(range(args.start_year, args.end_year + 1))
    else:
        # Default to current + next 2 years
        current_year = datetime.now().year
        class_years = [current_year + 4, current_year + 5, current_year + 6]
        logger.info(f"No years specified, defaulting to: {class_years}")

    # Create fetcher
    fetcher = RecruitingDataFetcher(
        output_path=args.output,
        save_to_duckdb=args.save_to_duckdb,
        max_retries=args.max_retries
    )

    # Run pipeline
    df = await fetcher.run(
        class_years=class_years,
        limit=args.limit
    )

    # Print summary
    if not df.empty:
        print("\n" + "="*60)
        print("Recruiting Data Fetch Summary")
        print("="*60)
        print(f"Total rankings: {len(df)}")
        print(f"Class years: {sorted(df['class_year'].unique().tolist())}")
        print(f"Services: {df['service'].unique().tolist()}")
        print(f"Output file: {args.output}")
        print(f"\nTop 10 Rankings (Class {df['class_year'].min()}):")
        sample = df[df['class_year'] == df['class_year'].min()].head(10)
        print(sample[['player_name', 'rank_national', 'stars', 'position', 'school', 'state']].to_string(index=False))
        print("="*60)
    else:
        print("\nNo data fetched")


if __name__ == '__main__':
    asyncio.run(main())
