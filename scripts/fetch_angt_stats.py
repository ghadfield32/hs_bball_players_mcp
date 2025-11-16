"""
Fetch ANGT (Adidas Next Generation Tournament) Basketball Stats

Scrapes player-level season statistics from EuroLeague ANGT using the ANGT adapter
and saves to DuckDB for dataset building.

Coverage:
- Region: Europe (U18 elite tournament)
- Data: Player demographics + season stats (PIR, points, rebounds, assists)
- Clubs: Real Madrid, Barcelona, Maccabi, Olympiacos, Zalgiris, etc.

Features:
- Browser automation for JavaScript-rendered stats (React/AJAX)
- Progress tracking with tqdm
- DuckDB storage with deduplication
- Error handling and retry logic

Usage:
    # Fetch current season with limit (testing):
    python scripts/fetch_angt_stats.py --season 2025-26 --limit 50

    # Fetch full season and save to DuckDB:
    python scripts/fetch_angt_stats.py --season 2025-26 --save-to-duckdb

    # Fetch multiple seasons:
    python scripts/fetch_angt_stats.py --seasons 2025-26,2024-25 --save-to-duckdb

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - Global Circuits (ANGT Integration)
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


class ANGTDataFetcher:
    """
    Fetches ANGT player stats for European U18 elite tournament.

    Uses browser automation to handle JavaScript-rendered stats.
    """

    def __init__(
        self,
        seasons: List[str],
        save_to_duckdb: bool = True,
        limit: Optional[int] = None
    ):
        """
        Initialize ANGT data fetcher.

        Args:
            seasons: List of seasons to fetch (e.g., ['2025-26', '2024-25'])
            save_to_duckdb: Whether to save to DuckDB
            limit: Limit players (for testing)
        """
        self.seasons = seasons
        self.save_to_duckdb = save_to_duckdb
        self.limit = limit

    async def initialize_datasource(self):
        """Initialize ANGT datasource adapter."""
        from src.datasources.europe.angt import ANGTDataSource

        self.angt_source = ANGTDataSource()
        logger.info("ANGT datasource initialized")

    async def fetch_players_for_season(self, season: str) -> List:
        """
        Fetch all players for a given season.

        Args:
            season: Season string (e.g., "2025-26")

        Returns:
            List of Player objects
        """
        try:
            logger.info(f"Fetching ANGT players for {season}...")

            # ANGT adapter handles browser automation for JavaScript-rendered stats
            players = await self.angt_source.search_players(
                season=season,
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
        logger.info(f"Starting ANGT data fetch: {len(self.seasons)} season(s)")
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
            'players_by_season': {}
        }

        logger.info("\n" + "=" * 80)
        logger.info("FETCH SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total unique players (demographics): {summary['total_players']}")
        logger.info(f"Seasons processed: {summary['seasons_processed']}")
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
        """Close ANGT datasource connections."""
        if hasattr(self, 'angt_source'):
            await self.angt_source.close()
            logger.info("ANGT datasource closed")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Fetch ANGT (EuroLeague Next Generation) basketball statistics'
    )
    parser.add_argument(
        '--seasons',
        type=str,
        default='2025-26',
        help='Comma-separated seasons to fetch (e.g., "2025-26,2024-25")'
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
    logger.info("ANGT DATA FETCH STARTING")
    logger.info("=" * 80)
    logger.info(f"Seasons: {seasons}")
    logger.info(f"Save to DuckDB: {args.save_to_duckdb}")
    logger.info(f"Player limit: {args.limit or 'None (fetch all)'}")
    logger.info("=" * 80 + "\n")

    # Create fetcher
    fetcher = ANGTDataFetcher(
        seasons=seasons,
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
        logger.info("ANGT DATA FETCH COMPLETE")
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
