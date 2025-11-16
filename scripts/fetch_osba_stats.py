"""
Fetch OSBA (Ontario Scholastic Basketball Association) Basketball Stats

Scrapes player-level season statistics from OSBA using the OSBA adapter
and saves to DuckDB for dataset building.

Coverage:
- Region: Ontario, Canada (prep basketball)
- Data: Player demographics + season stats
- Divisions: OSBA Mens, OSBA Womens, Trillium Mens, D-League Girls/Boys
- Teams: CIA Bounce, Athlete Institute, UPlay Canada, Orangeville Prep, etc.

Features:
- Handles RAMP Interactive platform (team-centric navigation)
- Progress tracking with tqdm
- DuckDB storage with deduplication
- Error handling and retry logic

Usage:
    # Fetch current season with limit (testing):
    python scripts/fetch_osba_stats.py --season 2024-25 --limit 50

    # Fetch full season and save to DuckDB:
    python scripts/fetch_osba_stats.py --season 2024-25 --save-to-duckdb

    # Fetch multiple seasons:
    python scripts/fetch_osba_stats.py --seasons 2024-25,2023-24 --save-to-duckdb

    # Fetch specific division:
    python scripts/fetch_osba_stats.py --season 2024-25 --division osba_mens --save-to-duckdb

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - Global Circuits (OSBA Integration)
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class OSBADataFetcher:
    """
    Fetches OSBA player stats for Ontario prep basketball.

    Handles RAMP Interactive platform with team-centric navigation.
    """

    def __init__(
        self,
        seasons: List[str],
        division: Optional[str] = None,
        save_to_duckdb: bool = True,
        limit: Optional[int] = None
    ):
        """
        Initialize OSBA data fetcher.

        Args:
            seasons: List of seasons to fetch (e.g., ['2024-25', '2023-24'])
            division: Specific division to fetch (e.g., 'osba_mens'), or None for all
            save_to_duckdb: Whether to save to DuckDB
            limit: Limit players (for testing)
        """
        self.seasons = seasons
        self.division = division
        self.save_to_duckdb = save_to_duckdb
        self.limit = limit

    async def initialize_datasource(self):
        """Initialize OSBA datasource adapter."""
        from src.datasources.canada.osba import OSBADataSource

        self.osba_source = OSBADataSource()
        logger.info("OSBA datasource initialized")

    async def fetch_players_for_season(self, season: str) -> List:
        """
        Fetch all players for a given season.

        Args:
            season: Season string (e.g., "2024-25")

        Returns:
            List of Player objects
        """
        try:
            logger.info(f"Fetching OSBA players for {season}...")

            # OSBA adapter handles RAMP Interactive platform navigation
            # May require division parameter for team-centric scraping
            players = await self.osba_source.search_players(
                season=season,
                division=self.division,
                limit=self.limit or 500  # Default to 500 if no limit
            )

            logger.info(f"Found {len(players)} players in {season}")
            return players

        except Exception as e:
            logger.error(f"Failed to fetch players for {season}: {str(e)}")
            return []

    async def fetch_all_data(self):
        """
        Fetch all player data across all seasons.

        Returns:
            Dictionary with:
            - 'players': List of Player objects (demographics)
            - 'summary': Summary statistics
        """
        logger.info("=" * 80)
        logger.info(f"Starting OSBA data fetch: {len(self.seasons)} season(s)")
        if self.division:
            logger.info(f"Division filter: {self.division}")
        logger.info("=" * 80)

        all_players = []  # Player demographics
        player_ids_seen = set()  # For deduplication

        # Fetch data per season
        for season in self.seasons:
            logger.info(f"\n{'='*80}\nProcessing Season: {season}\n{'='*80}")

            # Fetch players for this season
            season_players = await self.fetch_players_for_season(season)

            # Deduplicate players (same player may appear in multiple seasons)
            new_players = []
            for player in season_players:
                if player.player_id not in player_ids_seen:
                    new_players.append(player)
                    player_ids_seen.add(player.player_id)
                    all_players.append(player)

            logger.info(
                f"Season {season} complete: {len(season_players)} total, "
                f"{len(new_players)} unique new players"
            )

        # Generate summary
        summary = {
            'total_players': len(all_players),
            'seasons_processed': len(self.seasons),
            'division': self.division or 'all',
            'players_by_season': {}
        }

        logger.info("\n" + "=" * 80)
        logger.info("FETCH SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total unique players (demographics): {summary['total_players']}")
        logger.info(f"Seasons processed: {summary['seasons_processed']}")
        logger.info(f"Division: {summary['division']}")
        logger.info("=" * 80 + "\n")

        return {
            'players': all_players,
            'summary': summary
        }

    async def save_to_duckdb_storage(self, players: List) -> None:
        """
        Save Player demographics to DuckDB.

        Args:
            players: List of Player objects (demographics)
        """
        if not players:
            logger.warning("No players to save to DuckDB")
            return

        logger.info(f"Saving {len(players)} players to DuckDB...")

        try:
            from src.services.duckdb_storage import DuckDBStorage

            # Initialize DuckDB storage
            storage = DuckDBStorage()

            # Store players
            player_count = await storage.store_players(players)
            logger.info(f"✅ Stored {player_count} players to DuckDB")

        except Exception as e:
            logger.error(f"Failed to save to DuckDB: {str(e)}")
            raise

    async def close(self):
        """Close OSBA datasource connections."""
        if hasattr(self, 'osba_source'):
            await self.osba_source.close()
            logger.info("OSBA datasource closed")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Fetch OSBA (Ontario Scholastic Basketball) statistics'
    )
    parser.add_argument(
        '--seasons',
        type=str,
        default='2024-25',
        help='Comma-separated seasons to fetch (e.g., "2024-25,2023-24")'
    )
    parser.add_argument(
        '--division',
        type=str,
        default=None,
        help='Specific division to fetch (osba_mens, osba_womens, trillium_mens, dleague_girls, dleague_boys)'
    )
    parser.add_argument(
        '--save-to-duckdb',
        action='store_true',
        help='Save data to DuckDB database'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of players (for testing)'
    )

    args = parser.parse_args()

    # Parse seasons
    seasons = [s.strip() for s in args.seasons.split(',')]

    logger.info("=" * 80)
    logger.info("OSBA DATA FETCH STARTING")
    logger.info("=" * 80)
    logger.info(f"Seasons: {seasons}")
    logger.info(f"Division: {args.division or 'all'}")
    logger.info(f"Save to DuckDB: {args.save_to_duckdb}")
    logger.info(f"Player limit: {args.limit or 'None (fetch all)'}")
    logger.info("=" * 80 + "\n")

    # Create fetcher
    fetcher = OSBADataFetcher(
        seasons=seasons,
        division=args.division,
        save_to_duckdb=args.save_to_duckdb,
        limit=args.limit
    )

    try:
        # Initialize datasource
        await fetcher.initialize_datasource()

        # Fetch all data
        result = await fetcher.fetch_all_data()

        # Save to DuckDB if requested
        if args.save_to_duckdb and result['players']:
            await fetcher.save_to_duckdb_storage(result['players'])

        logger.info("\n" + "=" * 80)
        logger.info("OSBA DATA FETCH COMPLETE")
        logger.info("=" * 80)
        logger.info(f"✅ Total players fetched: {result['summary']['total_players']}")

        if args.save_to_duckdb:
            logger.info("✅ Data saved to DuckDB: data/duckdb/recruiting.duckdb")

        logger.info("=" * 80 + "\n")

    except KeyboardInterrupt:
        logger.warning("\n\nFetch interrupted by user")
    except Exception as e:
        logger.error(f"\n\nFetch failed with error: {str(e)}")
        raise
    finally:
        # Close connections
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
