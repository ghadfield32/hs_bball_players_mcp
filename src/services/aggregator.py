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

# Active adapters (fully implemented):
from ..datasources.europe.fiba_youth import FIBAYouthDataSource
from ..datasources.us.bound import BoundDataSource
from ..datasources.us.eybl import EYBLDataSource
from ..datasources.us.eybl_girls import EYBLGirlsDataSource
from ..datasources.us.fhsaa import FHSAADataSource
from ..datasources.us.hhsaa import HHSAADataSource
from ..datasources.us.mn_hub import MNHubDataSource
from ..datasources.us.psal import PSALDataSource
from ..datasources.us.rankone import RankOneDataSource
from ..datasources.us.sblive import SBLiveDataSource
from ..datasources.us.three_ssb import ThreeSSBDataSource
from ..datasources.us.three_ssb_girls import ThreeSSBGirlsDataSource
from ..datasources.us.uaa import UAADataSource
from ..datasources.us.uaa_girls import UAAGirlsDataSource
from ..datasources.us.wsn import WSNDataSource

# Import from global module (avoid 'global' keyword with import style - it's a Python reserved word)
# Guard FIBA LiveStats import so other tests/adapters can run even if this fails
try:
    import importlib
    _fiba_mod = importlib.import_module("src.datasources.global.fiba_livestats")
    FIBALiveStatsDataSource = _fiba_mod.FIBALiveStatsDataSource
    FIBA_LIVESTATS_AVAILABLE = True
except (ImportError, ModuleNotFoundError, AttributeError):
    # FIBA LiveStats module not available - skip it
    FIBALiveStatsDataSource = None
    FIBA_LIVESTATS_AVAILABLE = False

# Template adapters (need URL updates after website inspection):
from ..datasources.australia.playhq import PlayHQDataSource
from ..datasources.canada.osba import OSBADataSource
from ..datasources.europe.angt import ANGTDataSource
from ..datasources.us.grind_session import GrindSessionDataSource
from ..datasources.us.ote import OTEDataSource

from ..models import Player, PlayerSeasonStats, Team
from ..utils.logger import get_logger
from .duckdb_storage import get_duckdb_storage
from .identity import deduplicate_players, resolve_player_uid
from .parquet_exporter import get_parquet_exporter

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

        # Initialize storage and export services
        self.duckdb = get_duckdb_storage() if self.settings.duckdb_enabled else None
        self.exporter = get_parquet_exporter()

        logger.info(
            f"Aggregator initialized with {len(self.sources)} sources",
            duckdb_enabled=self.settings.duckdb_enabled,
        )

    def _initialize_sources(self) -> None:
        """Initialize all enabled datasource adapters."""
        # Map of source types to their adapter classes
        source_classes = {
            # ===== ACTIVE ADAPTERS (Production Ready) =====
            # US - National Circuits (Big 3 complete):
            "eybl": EYBLDataSource,                      # Nike EYBL (boys)
            "eybl_girls": EYBLGirlsDataSource,          # Nike Girls EYBL
            "three_ssb": ThreeSSBDataSource,            # Adidas 3SSB (boys)
            "three_ssb_girls": ThreeSSBGirlsDataSource, # Adidas 3SSB Girls
            "uaa": UAADataSource,                        # Under Armour Association (boys)
            "uaa_girls": UAAGirlsDataSource,            # UA Next (girls)

            # US - Multi-State Coverage:
            "bound": BoundDataSource,        # IA, SD, IL, MN (4 states)
            "sblive": SBLiveDataSource,      # WA, OR, CA, AZ, ID, NV (6 states)
            "rankone": RankOneDataSource,    # TX, KY, IN, OH, TN (schedules/fixtures)

            # US - Single State Deep Coverage:
            "mn_hub": MNHubDataSource,       # Minnesota (best free HS stats)
            "psal": PSALDataSource,          # NYC public schools
            "wsn": WSNDataSource,            # Wisconsin (deep stats)

            # US - State Associations (Tournaments/Brackets):
            "fhsaa": FHSAADataSource,        # Florida (Southeast anchor)
            "hhsaa": HHSAADataSource,        # Hawaii (excellent historical data)

            # Global/International:
            "fiba": FIBAYouthDataSource,           # FIBA Youth competitions

            # ===== TEMPLATE ADAPTERS (Need URL Updates) =====
            # These have complete code structure but need actual website URLs:
            # "grind_session": GrindSessionDataSource,  # TODO: Update URLs after inspection
            # "ote": OTEDataSource,                      # TODO: Update URLs after inspection
            # "angt": ANGTDataSource,                    # TODO: Update URLs after inspection
            # "osba": OSBADataSource,                    # TODO: Update URLs after inspection
            # "playhq": PlayHQDataSource,                # TODO: Update URLs after inspection
        }

        # Add FIBA LiveStats conditionally (only if import succeeded)
        if FIBA_LIVESTATS_AVAILABLE:
            source_classes["fiba_livestats"] = FIBALiveStatsDataSource

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

        # Deduplicate using identity resolution
        unique_players = deduplicate_players(all_players, fuzzy=False)

        # Apply total limit
        unique_players = unique_players[:total_limit]

        # Add stable player_uid to each result
        for player in unique_players:
            # Store uid as a custom attribute (not part of the model)
            uid = resolve_player_uid(
                player.full_name, player.school_name or "", player.grad_year
            )
            # Add uid as metadata in data_source
            if player.data_source:
                player.data_source.player_uid = uid

        logger.info(
            f"Aggregated {len(unique_players)} unique players from {len(all_players)} total results"
        )

        # Persist to DuckDB if enabled
        if self.duckdb and all_players:
            try:
                await self.duckdb.store_players(all_players)
                logger.info(f"Persisted {len(all_players)} players to DuckDB")
            except Exception as e:
                logger.error("Failed to persist players to DuckDB", error=str(e))

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

        # Persist to DuckDB if enabled
        if self.duckdb and all_stats:
            try:
                await self.duckdb.store_player_stats(all_stats)
                logger.info(f"Persisted {len(all_stats)} player stats to DuckDB")
            except Exception as e:
                logger.error("Failed to persist stats to DuckDB", error=str(e))

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
                # Add source info and player_uid to each entry
                for entry in result:
                    entry["source"] = source_key
                    # Add stable player_uid if we have player info
                    if "player_name" in entry:
                        uid = resolve_player_uid(
                            entry.get("player_name", ""),
                            entry.get("school", ""),
                            entry.get("grad_year"),
                        )
                        entry["player_uid"] = uid
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
