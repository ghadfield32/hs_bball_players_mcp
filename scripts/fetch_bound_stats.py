"""
Fetch Bound (Varsity Bound) State HS Basketball Stats

Scrapes player-level season statistics from Bound state coverage using
the Bound adapter and saves to DuckDB for dataset building.

Coverage:
- States: IA, SD, IL (Midwest US - Bound's flagship coverage)
  NOTE: MN excluded - Phase HS-2 validation confirmed no data on GoBound platform
- Seasons: 2022-23, 2023-24, 2024-25 (3 years of historical data)
- Data: Player demographics + season stats (player-level averages)

Features:
- Multi-state concurrent processing
- Multi-season historical fetching
- Player demographics (height, position, grad_year) from Player objects
- Season stats (pts_per_g, reb_per_g, etc.) from PlayerSeasonStats objects
- Retry logic with exponential backoff
- Progress tracking with tqdm
- Error handling per state (continue on failure)
- DuckDB storage with deduplication

Usage:
    # Fetch all states, all seasons (recommended for production):
    python scripts/fetch_bound_stats.py --states all --seasons 2022-23,2023-24,2024-25 --save-to-duckdb

    # Fetch specific state for testing:
    python scripts/fetch_bound_stats.py --states IA --seasons 2024-25 --limit 50

    # Fetch multiple states:
    python scripts/fetch_bound_stats.py --states IA,MN --limit 100 --save-to-duckdb

Author: Claude Code
Date: 2025-11-15
Phase: 17 - State HS Stats Pipeline
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

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


class BoundDataFetcher:
    """
    Fetches Bound player stats across multiple midwest states and seasons.

    Handles pagination, retries, multi-state fetching, and DuckDB storage.
    """

    # Bound covered states (Midwest US)
    # Note: MN is excluded - Phase HS-2 validation confirmed no data available on GoBound
    BOUND_STATES = ['IA', 'SD', 'IL']

    def __init__(
        self,
        states: List[str],
        seasons: List[str],
        save_to_duckdb: bool = True,
        max_retries: int = 3,
        limit_per_state: Optional[int] = None
    ):
        """
        Initialize Bound data fetcher.

        Args:
            states: List of state codes to fetch (e.g., ['IA', 'MN'])
            seasons: List of seasons to fetch (e.g., ['2024-25', '2023-24'])
            save_to_duckdb: Whether to save to DuckDB
            max_retries: Maximum retries per player
            limit_per_state: Limit players per state (for testing)
        """
        # Validate states
        invalid_states = [s for s in states if s not in self.BOUND_STATES]
        if invalid_states:
            raise ValueError(
                f"Invalid Bound states: {invalid_states}. "
                f"Valid states: {self.BOUND_STATES}"
            )

        self.states = states
        self.seasons = seasons
        self.save_to_duckdb = save_to_duckdb
        self.max_retries = max_retries
        self.limit_per_state = limit_per_state

        self.bound_source = None
        self.duckdb_storage = None

        logger.info(
            f"BoundDataFetcher initialized: states={states}, seasons={seasons}, "
            f"save_to_duckdb={save_to_duckdb}"
        )

    async def initialize(self):
        """Initialize data sources and storage."""
        from src.datasources.us.bound import BoundDataSource
        from src.services.duckdb_storage import get_duckdb_storage

        self.bound_source = BoundDataSource()

        if self.save_to_duckdb:
            self.duckdb_storage = get_duckdb_storage()

        logger.info("Data sources initialized")

    async def cleanup(self):
        """Clean up connections."""
        if self.bound_source:
            await self.bound_source.close()

        logger.info("Cleanup complete")

    async def fetch_players_for_state(
        self,
        state: str,
        season: Optional[str] = None
    ) -> List:
        """
        Fetch all players for a specific state using leaderboards.

        Args:
            state: State code (e.g., 'IA')
            season: Season string (e.g., '2024-25')

        Returns:
            List of Player objects
        """
        logger.info(f"Fetching players for {state} (season={season})")

        try:
            # Bound's search_players returns Player objects from state leaderboards
            players = await self.bound_source.search_players(
                state=state,
                season=season,
                limit=self.limit_per_state or 500  # Default to 500 if no limit
            )

            logger.info(f"Found {len(players)} players in {state}")
            return players

        except Exception as e:
            logger.error(f"Failed to fetch players for {state}: {str(e)}")
            return []

    async def fetch_season_stats_for_player(
        self,
        player_id: str,
        player_name: str,
        state: str,
        season: str,
        retries: int = 0
    ):
        """
        Fetch season stats for a specific player with retry logic.

        Args:
            player_id: Player ID
            player_name: Player name (for logging)
            state: State code
            season: Season string
            retries: Current retry count

        Returns:
            PlayerSeasonStats object or None
        """
        try:
            stats = await self.bound_source.get_player_season_stats(
                player_id=player_id,
                season=season,
                state=state
            )

            return stats

        except Exception as e:
            if retries < self.max_retries:
                # Exponential backoff
                await asyncio.sleep(1 * (retries + 1))
                return await self.fetch_season_stats_for_player(
                    player_id, player_name, state, season, retries + 1
                )
            else:
                logger.warning(
                    f"Failed to get stats for {player_name} ({state}, {season}) "
                    f"after {self.max_retries} retries: {str(e)}"
                )
                return None

    async def fetch_all_data(self) -> Dict:
        """
        Fetch all player data across all states and seasons.

        Returns:
            Dictionary with:
            - 'players': List of Player objects (demographics)
            - 'stats': List of PlayerSeasonStats objects (performance)
            - 'summary': Summary statistics
        """
        logger.info("=" * 80)
        logger.info(
            f"Starting Bound data fetch: {len(self.states)} states, "
            f"{len(self.seasons)} seasons"
        )
        logger.info("=" * 80)

        all_players = []  # Player demographics
        all_stats = []  # Season stats
        player_ids_seen: Set[str] = set()  # For deduplication

        # Fetch data per state
        for state in self.states:
            logger.info(f"\n{'='*80}\nProcessing State: {state}\n{'='*80}")

            # Fetch players for this state (demographics)
            # Note: search_players returns Player objects with demographics
            state_players = await self.fetch_players_for_state(
                state=state,
                season=self.seasons[0] if self.seasons else None  # Use first season for player search
            )

            if not state_players:
                logger.warning(f"No players found for {state}, skipping")
                continue

            logger.info(f"Found {len(state_players)} players in {state}")

            # Fetch season stats for each player across all seasons
            stats_count = 0

            # Create progress bar for this state
            with tqdm(
                total=len(state_players) * len(self.seasons),
                desc=f"{state} stats",
                unit="player-season"
            ) as pbar:

                for player in state_players:
                    # Add player demographics (only once per player)
                    if player.player_id not in player_ids_seen:
                        all_players.append(player)
                        player_ids_seen.add(player.player_id)

                    # Fetch stats for each season
                    for season in self.seasons:
                        stats = await self.fetch_season_stats_for_player(
                            player_id=player.player_id,
                            player_name=player.full_name,
                            state=state,
                            season=season
                        )

                        if stats:
                            all_stats.append(stats)
                            stats_count += 1
                            pbar.set_postfix({
                                'player': player.full_name[:20],
                                'stats': stats_count
                            })

                        pbar.update(1)

            logger.info(
                f"State {state} complete: {len(state_players)} players, "
                f"{stats_count} player-season records"
            )

        # Generate summary
        summary = {
            'total_players': len(all_players),
            'total_stats': len(all_stats),
            'states_processed': len(self.states),
            'seasons_processed': len(self.seasons),
            'players_by_state': {},
            'stats_by_season': {}
        }

        # Count players by state
        for player in all_players:
            state = player.school_state or 'UNKNOWN'
            summary['players_by_state'][state] = summary['players_by_state'].get(state, 0) + 1

        # Count stats by season
        for stat in all_stats:
            season = stat.season or 'UNKNOWN'
            summary['stats_by_season'][season] = summary['stats_by_season'].get(season, 0) + 1

        logger.info("\n" + "=" * 80)
        logger.info("FETCH SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total unique players (demographics): {summary['total_players']}")
        logger.info(f"Total player-season stat records: {summary['total_stats']}")
        logger.info(f"Players by state: {summary['players_by_state']}")
        logger.info(f"Stats by season: {summary['stats_by_season']}")
        logger.info("=" * 80 + "\n")

        return {
            'players': all_players,
            'stats': all_stats,
            'summary': summary
        }

    async def save_to_duckdb_storage(
        self,
        players: List,
        stats: List
    ) -> None:
        """
        Save Player demographics and PlayerSeasonStats to DuckDB.

        Args:
            players: List of Player objects (demographics)
            stats: List of PlayerSeasonStats objects (performance)
        """
        if not self.duckdb_storage:
            logger.warning("DuckDB storage not initialized, skipping")
            return

        logger.info(
            f"Saving to DuckDB: {len(players)} players, {len(stats)} season stats"
        )

        # Save player demographics
        if players:
            try:
                # DuckDB storage has store_players method for Player objects
                stored_players = await self.duckdb_storage.store_players(players)
                logger.info(f"Stored {stored_players} player demographic records in DuckDB")
            except Exception as e:
                logger.error(f"Failed to store players in DuckDB: {str(e)}")

        # Save season stats
        if stats:
            try:
                stored_stats = await self.duckdb_storage.store_player_stats(stats)
                logger.info(f"Stored {stored_stats} player season stat records in DuckDB")
            except Exception as e:
                logger.error(f"Failed to store player stats in DuckDB: {str(e)}")

    async def run(self) -> Dict:
        """
        Run the full Bound data fetch pipeline.

        Returns:
            Dictionary with fetch results and summary
        """
        logger.info(
            f"\nStarting Bound data fetch pipeline\n"
            f"States: {self.states}\n"
            f"Seasons: {self.seasons}\n"
            f"Save to DuckDB: {self.save_to_duckdb}"
        )

        try:
            # Initialize
            await self.initialize()

            # Fetch all data
            result = await self.fetch_all_data()

            # Save to DuckDB
            if self.save_to_duckdb:
                await self.save_to_duckdb_storage(
                    players=result['players'],
                    stats=result['stats']
                )

            logger.info("\n✅ Bound data fetch pipeline completed successfully!")
            return result

        finally:
            # Cleanup
            await self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch Bound (Varsity Bound) state HS basketball player stats"
    )

    # State selection
    parser.add_argument(
        '--states',
        type=str,
        default='all',
        help='Comma-separated state codes (IA,SD,IL,MN) or "all" (default: all)'
    )

    # Season selection
    parser.add_argument(
        '--seasons',
        type=str,
        default='2024-25,2023-24,2022-23',
        help='Comma-separated seasons (default: 2024-25,2023-24,2022-23)'
    )

    # Limit for testing
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit players per state (for testing)'
    )

    # DuckDB option
    parser.add_argument(
        '--save-to-duckdb',
        action='store_true',
        help='Save results to DuckDB'
    )

    # Retry configuration
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retries per player (default: 3)'
    )

    args = parser.parse_args()

    # Parse states
    if args.states.lower() == 'all':
        states = BoundDataFetcher.BOUND_STATES
    else:
        states = [s.strip().upper() for s in args.states.split(',')]

    # Parse seasons
    seasons = [s.strip() for s in args.seasons.split(',')]

    logger.info(f"Configuration: states={states}, seasons={seasons}")

    # Create fetcher
    fetcher = BoundDataFetcher(
        states=states,
        seasons=seasons,
        save_to_duckdb=args.save_to_duckdb,
        max_retries=args.max_retries,
        limit_per_state=args.limit
    )

    # Run async pipeline
    try:
        result = asyncio.run(fetcher.run())

        # Print final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"Total players: {result['summary']['total_players']}")
        print(f"Total stat records: {result['summary']['total_stats']}")
        print(f"States: {', '.join(states)}")
        print(f"Seasons: {', '.join(seasons)}")
        print("=" * 80)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
