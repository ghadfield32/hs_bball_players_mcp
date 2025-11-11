"""
Multi-Source Aggregation Service

Aggregates data from multiple basketball statistics sources.
Handles parallel queries, deduplication, and result merging.
"""

import asyncio
from datetime import datetime
from typing import Optional

from ..config import get_settings
from ..datasources.base import BaseDataSource
from ..datasources.europe.fiba_youth import FIBAYouthDataSource
from ..datasources.us.eybl import EYBLDataSource
from ..datasources.us.mn_hub import MNHubDataSource
from ..datasources.us.psal import PSALDataSource
from ..models import Player, PlayerSeasonStats, Team
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataSourceAggregator:
    """
    Multi-source data aggregator.

    Manages multiple datasource adapters and provides unified query interface.
    """

    def __init__(self):
        """Initialize aggregator with all enabled datasources."""
        self.settings = get_settings()
        self.sources: dict[str, BaseDataSource] = {}
        self._initialize_sources()

        logger.info(f"Aggregator initialized with {len(self.sources)} sources")

    def _initialize_sources(self) -> None:
        """Initialize all enabled datasource adapters."""
        # Map of source types to their adapter classes
        source_classes = {
            "eybl": EYBLDataSource,
            "fiba": FIBAYouthDataSource,
            "mn_hub": MNHubDataSource,
            "psal": PSALDataSource,
            # Add more as implemented:
            # "grind_session": GrindSessionDataSource,
            # "ote": OTEDataSource,
            # "angt": ANGTDataSource,
            # "osba": OSBADataSource,
            # "playhq": PlayHQDataSource,
        }

        for source_key, source_class in source_classes.items():
            if self.settings.is_datasource_enabled(source_key):
                try:
                    self.sources[source_key] = source_class()
                    logger.info(f"Enabled datasource: {source_key}")
                except Exception as e:
                    logger.error(f"Failed to initialize datasource {source_key}", error=str(e))

    async def close_all(self) -> None:
        """Close all datasource connections."""
        for source in self.sources.values():
            try:
                await source.close()
            except Exception as e:
                logger.error(f"Error closing source", error=str(e))

    async def search_players_all_sources(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        sources: Optional[list[str]] = None,
        limit_per_source: int = 20,
        total_limit: int = 100,
    ) -> list[Player]:
        """
        Search for players across multiple sources.

        Args:
            name: Player name filter
            team: Team name filter
            season: Season filter
            sources: Specific sources to query (None = all enabled)
            limit_per_source: Max results per source
            total_limit: Max total results

        Returns:
            List of Player objects from all sources
        """
        # Determine which sources to query
        query_sources = sources if sources else list(self.sources.keys())
        query_sources = [s for s in query_sources if s in self.sources]

        if not query_sources:
            logger.warning("No sources available for query")
            return []

        logger.info(
            f"Searching players across {len(query_sources)} sources",
            name=name,
            team=team,
            sources=query_sources,
        )

        # Query sources in parallel
        tasks = []
        for source_key in query_sources:
            source = self.sources[source_key]
            task = source.search_players(
                name=name, team=team, season=season, limit=limit_per_source
            )
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_players = []
        for i, result in enumerate(results):
            source_key = query_sources[i]

            if isinstance(result, Exception):
                logger.error(f"Source {source_key} failed", error=str(result))
                continue

            if result:
                all_players.extend(result)
                logger.info(f"Source {source_key} returned {len(result)} players")

        # Deduplicate (basic implementation - by name)
        seen_names = set()
        unique_players = []

        for player in all_players:
            key = (player.full_name.lower(), player.school_name or "")
            if key not in seen_names:
                unique_players.append(player)
                seen_names.add(key)

        # Apply total limit
        unique_players = unique_players[:total_limit]

        logger.info(
            f"Aggregated {len(unique_players)} unique players from {len(all_players)} total results"
        )

        return unique_players

    async def get_player_from_source(
        self, source_key: str, player_id: str
    ) -> Optional[Player]:
        """
        Get player from a specific source.

        Args:
            source_key: Source identifier (e.g., 'eybl', 'psal')
            player_id: Player ID

        Returns:
            Player object or None
        """
        if source_key not in self.sources:
            logger.warning(f"Source not available: {source_key}")
            return None

        try:
            return await self.sources[source_key].get_player(player_id)
        except Exception as e:
            logger.error(f"Failed to get player from {source_key}", error=str(e))
            return None

    async def get_player_season_stats_all_sources(
        self,
        player_name: str,
        season: Optional[str] = None,
        sources: Optional[list[str]] = None,
    ) -> list[PlayerSeasonStats]:
        """
        Get player season stats from multiple sources.

        Args:
            player_name: Player name to search
            season: Season filter
            sources: Specific sources to query

        Returns:
            List of PlayerSeasonStats from different sources
        """
        # First, search for the player to get their IDs in each source
        players = await self.search_players_all_sources(
            name=player_name, sources=sources, limit_per_source=1
        )

        if not players:
            return []

        # Query stats from sources in parallel
        tasks = []
        source_keys = []

        for player in players:
            # Extract source from player_id
            source_key = player.player_id.split("_")[0]
            if source_key in self.sources:
                task = self.sources[source_key].get_player_season_stats(player.player_id, season)
                tasks.append(task)
                source_keys.append(source_key)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect stats
        all_stats = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get stats", error=str(result))
                continue

            if result:
                all_stats.append(result)
                logger.info(f"Got stats from {source_keys[i]}")

        return all_stats

    async def search_teams_all_sources(
        self,
        name: Optional[str] = None,
        league: Optional[str] = None,
        season: Optional[str] = None,
        sources: Optional[list[str]] = None,
        limit_per_source: int = 20,
        total_limit: int = 100,
    ) -> list[Team]:
        """
        Search for teams across multiple sources.

        Args:
            name: Team name filter
            league: League filter
            season: Season filter
            sources: Specific sources to query
            limit_per_source: Max results per source
            total_limit: Max total results

        Returns:
            List of Team objects
        """
        # Note: Team search would need to be added to base datasource interface
        # For now, return empty list
        logger.warning("Team search across sources not yet fully implemented")
        return []

    async def get_leaderboard_all_sources(
        self,
        stat: str,
        season: Optional[str] = None,
        sources: Optional[list[str]] = None,
        limit_per_source: int = 20,
        total_limit: int = 100,
    ) -> list[dict]:
        """
        Get statistical leaderboard from multiple sources.

        Args:
            stat: Stat category
            season: Season filter
            sources: Specific sources to query
            limit_per_source: Max results per source
            total_limit: Max total results

        Returns:
            List of leaderboard entries
        """
        query_sources = sources if sources else list(self.sources.keys())
        query_sources = [s for s in query_sources if s in self.sources]

        if not query_sources:
            return []

        logger.info(f"Getting {stat} leaderboard from {len(query_sources)} sources")

        # Query sources in parallel
        tasks = []
        for source_key in query_sources:
            source = self.sources[source_key]
            task = source.get_leaderboard(stat=stat, season=season, limit=limit_per_source)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_entries = []
        for i, result in enumerate(results):
            source_key = query_sources[i]

            if isinstance(result, Exception):
                logger.error(f"Source {source_key} leaderboard failed", error=str(result))
                continue

            if result:
                # Add source info to each entry
                for entry in result:
                    entry["source"] = source_key
                all_entries.extend(result)

        # Sort by stat value (descending)
        all_entries.sort(key=lambda x: x.get("stat_value", 0), reverse=True)

        # Re-rank
        for i, entry in enumerate(all_entries[:total_limit], 1):
            entry["aggregated_rank"] = i

        logger.info(f"Aggregated leaderboard with {len(all_entries[:total_limit])} entries")

        return all_entries[:total_limit]

    async def health_check_all_sources(self) -> dict[str, bool]:
        """
        Check health of all datasources.

        Returns:
            Dictionary mapping source to health status
        """
        tasks = {key: source.health_check() for key, source in self.sources.items()}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        health_status = {}
        for i, key in enumerate(tasks.keys()):
            result = list(results)[i]
            if isinstance(result, Exception):
                health_status[key] = False
            else:
                health_status[key] = result

        return health_status

    def get_available_sources(self) -> list[str]:
        """
        Get list of available source keys.

        Returns:
            List of source keys
        """
        return list(self.sources.keys())

    def get_source_info(self) -> dict[str, dict]:
        """
        Get information about all sources.

        Returns:
            Dictionary with source metadata
        """
        info = {}
        for key, source in self.sources.items():
            info[key] = {
                "name": source.source_name,
                "type": source.source_type.value,
                "region": source.region.value,
                "base_url": source.base_url,
                "enabled": source.is_enabled(),
            }
        return info


# Global aggregator instance
_aggregator_instance: Optional[DataSourceAggregator] = None


def get_aggregator() -> DataSourceAggregator:
    """
    Get global aggregator instance.

    Returns:
        DataSourceAggregator instance
    """
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = DataSourceAggregator()
    return _aggregator_instance
