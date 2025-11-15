"""
Multi-Source Aggregation Service

Aggregates data from multiple basketball statistics sources.
Handles parallel queries, deduplication, and result merging.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml

from ..config import get_settings
from ..datasources.base import BaseDataSource

# Active adapters (fully implemented):
# US - National Circuits
from ..datasources.us.bound import BoundDataSource
from ..datasources.us.eybl import EYBLDataSource
from ..datasources.us.eybl_girls import EYBLGirlsDataSource
from ..datasources.us.three_ssb import ThreeSSBDataSource
from ..datasources.us.three_ssb_girls import ThreeSSBGirlsDataSource
from ..datasources.us.uaa import UAADataSource
from ..datasources.us.uaa_girls import UAAGirlsDataSource

# US - State/Regional Platforms
from ..datasources.us.fhsaa import FHSAADataSource
from ..datasources.us.hhsaa import HHSAADataSource
from ..datasources.us.mn_hub import MNHubDataSource
from ..datasources.us.psal import PSALDataSource
from ..datasources.us.rankone import RankOneDataSource
from ..datasources.us.sblive import SBLiveDataSource
from ..datasources.us.wsn import WSNDataSource

# Wisconsin - Hybrid Coverage (Phase 15 + Phase 20)
from ..datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from ..datasources.us.wisconsin_maxpreps import MaxPrepsWisconsinDataSource

# US - Event Platforms (Phase 10/11)
from ..datasources.us.cifsshome import CIFSSHomeDataSource
from ..datasources.us.uil_brackets import UILBracketsDataSource
from ..datasources.us.exposure_events import ExposureEventsDataSource
from ..datasources.us.tourneymachine import TournyMachineDataSource

# US - State Association Adapters (Phase 14.5)
from ..datasources.us.nchsaa import NCHSAADataSource
from ..datasources.us.georgia_ghsa import GeorgiaGHSADataSource

# US - State Association Adapters (Phase 16 - 50/50 US Coverage Complete)
from ..datasources.us.arizona_aia import ArizonaAIADataSource
from ..datasources.us.oregon_osaa import OregonOSAADataSource
from ..datasources.us.nevada_niaa import NevadaNIAADataSource
from ..datasources.us.washington_wiaa import WashingtonWIAADataSource
from ..datasources.us.idaho_ihsaa import IdahoIHSAADataSource

# US - Phase 17 High-Impact States (CA, TX, FL, GA, OH, PA, NY)
from ..datasources.us.california_cif_ss import CaliforniaCIFSSDataSource
from ..datasources.us.texas_uil import TexasUILDataSource
from ..datasources.us.florida_fhsaa import FloridaFHSAADataSource
from ..datasources.us.ohio_ohsaa import OhioOHSAADataSource
from ..datasources.us.pennsylvania_piaa import PennsylvaniaPIAADataSource
from ..datasources.us.newyork_nysphsaa import NewYorkNYSPHSAADataSource

# Europe - Youth Leagues (Phase 7)
from ..datasources.europe.fiba_youth import FIBAYouthDataSource
from ..datasources.europe.nbbl import NBBLDataSource
from ..datasources.europe.feb import FEBDataSource
from ..datasources.europe.mkl import MKLDataSource
from ..datasources.europe.lnb_espoirs import LNBEspoirsDataSource

# Canada - Youth Leagues (Phase 7)
from ..datasources.canada.npa import NPADataSource

# Canada - Provincial Associations (Phase 14.5)
from ..datasources.canada.ofsaa import OFSAADataSource

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

# Vendor Generics (Phase 14 - Global expansion):
# TODO: Fix missing DataSourceType.CIRCUIT enum
# from ..datasources.vendors.fiba_federation_events import FibaFederationEventsDataSource
# from ..datasources.vendors.gameday import GameDayDataSource

# Vendor Generics (Phase 16 - Parameterized Federation Coverage):
from ..datasources.vendors.fibalivestats_federation import FIBALiveStatsFederationDataSource

# Recruiting adapters:
from ..datasources.recruiting.base_recruiting import BaseRecruitingSource
from ..datasources.recruiting.sports_247 import Sports247DataSource

from ..models import (
    CollegeOffer,
    Player,
    PlayerSeasonStats,
    RecruitingPrediction,
    RecruitingProfile,
    RecruitingRank,
    Team,
)
from ..utils.advanced_stats import enrich_player_season_stats
from ..utils.logger import get_logger
from .duckdb_storage import get_duckdb_storage
from .identity import deduplicate_players, resolve_player_uid
from .parquet_exporter import get_parquet_exporter

logger = get_logger(__name__)


def load_from_registry(yaml_path: str | Path = "config/sources.yaml") -> dict[str, type]:
    """
    Build the source id -> DataSourceClass map from config/sources.yaml.
    Only include entries with status in {'active', 'enabled'} and
    with a resolvable adapter module/class.
    Prevents aggregator drift vs registry.

    Args:
        yaml_path: Path to sources.yaml registry file

    Returns:
        Dictionary mapping source_id to DataSource class
    """
    from importlib import import_module

    path = Path(yaml_path)
    if not path.exists():
        logger.warning(f"Registry file not found: {yaml_path}, falling back to hard-coded sources")
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.error(f"Failed to load registry: {e}, falling back to hard-coded sources")
        return {}

    sources_list = data.get("sources", [])
    source_classes = {}

    for src in sources_list:
        src_id = src.get("id")
        status = src.get("status", "")
        adapter_module = src.get("adapter_module")
        adapter_class = src.get("adapter_class")

        # Only load active/enabled sources
        if status not in {"active", "enabled"}:
            continue

        # Must have module + class
        if not adapter_module or not adapter_class:
            logger.warning(f"Source {src_id} missing adapter_module or adapter_class, skipping")
            continue

        try:
            mod = import_module(adapter_module)
            cls = getattr(mod, adapter_class)
            source_classes[src_id] = cls
            logger.debug(f"Loaded {src_id} → {adapter_class}")
        except (ModuleNotFoundError, AttributeError) as e:
            logger.warning(f"Could not load {src_id}: {e}")

    logger.info(f"Registry loader found {len(source_classes)} active sources")
    return source_classes


class DataSourceAggregator:
    """
    Multi-source data aggregator.

    Manages multiple datasource adapters and provides unified query interface.
    """

    def __init__(self, registry_path: str | Path = "config/sources.yaml"):
        """Initialize aggregator with all enabled datasources.

        Args:
            registry_path: Path to sources.yaml registry file (default: config/sources.yaml)
        """
        self.settings = get_settings()
        self.sources: dict[str, BaseDataSource] = {}  # Stats datasources
        self.recruiting_sources: dict[str, BaseRecruitingSource] = {}  # Recruiting datasources
        self.registry_path = registry_path
        self._initialize_sources()

        # Initialize storage and export services
        self.duckdb = get_duckdb_storage() if self.settings.duckdb_enabled else None
        self.exporter = get_parquet_exporter()

        logger.info(
            f"Aggregator initialized with {len(self.sources)} stats sources "
            f"and {len(self.recruiting_sources)} recruiting sources",
            duckdb_enabled=self.settings.duckdb_enabled,
        )

    def _initialize_sources(self) -> None:
        """Initialize all enabled datasource adapters."""
        # Try to load from registry first
        source_classes = load_from_registry(self.registry_path)

        # Fallback to hard-coded sources if registry loading fails
        if not source_classes:
            logger.warning("Registry loader returned empty, using hard-coded source list")
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
                "wsn": WSNDataSource,            # Wisconsin (INACTIVE - news site only)

                # Wisconsin - Hybrid Coverage (Phase 15 + Phase 20):
                "wiaa": WisconsinWiaaDataSource,          # Wisconsin - Official tournament brackets
                "maxpreps_wi": MaxPrepsWisconsinDataSource,  # Wisconsin - Player/team stats

                # Global/International:
                "fiba": FIBAYouthDataSource,           # FIBA Youth competitions

                # US - State Associations (Tournaments/Brackets):
                "fhsaa": FHSAADataSource,        # Florida (Southeast anchor)
                "hhsaa": HHSAADataSource,        # Hawaii (excellent historical data)

                # US - State Associations (Phase 16 - 50/50 US Coverage Complete):
                "aia": ArizonaAIADataSource,              # Arizona (7 conferences)
                "osaa": OregonOSAADataSource,            # Oregon (6 classifications, JSON support)
                "niaa": NevadaNIAADataSource,            # Nevada (5 divisions, PDF caching)
                "wiaa_wa": WashingtonWIAADataSource,     # Washington (4 classifications)
                "ihsaa_id": IdahoIHSAADataSource,        # Idaho (6 classifications)

                # US - Event Platforms (Phase 10/11 - Generic AAU):
                "cifsshome": CIFSSHomeDataSource,     # California CIF-SS sections
                "uil_brackets": UILBracketsDataSource, # Texas UIL playoffs
                "exposure_events": ExposureEventsDataSource,  # Exposure Events (generic)
                "tourneymachine": TournyMachineDataSource,    # TournyMachine (generic)

                # Europe - Youth Leagues (Phase 7):
                "nbbl": NBBLDataSource,                # Germany NBBL/JBBL (U19/U16)
                "feb": FEBDataSource,                  # Spain FEB Junior (U16/U18/U20)
                "mkl": MKLDataSource,                  # Lithuania MKL Youth (U16/U18/U20)
                "lnb_espoirs": LNBEspoirsDataSource,  # France LNB Espoirs (U21)

                # Canada - Youth Leagues (Phase 7):
                "npa": NPADataSource,                  # National Preparatory Association

                # Global/International:
                "fiba": FIBAYouthDataSource,           # FIBA Youth competitions
                "fiba_livestats": FIBALiveStatsDataSource,  # FIBA LiveStats v7 global

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

        # Recruiting sources (separate from stats sources)
        recruiting_source_classes = {
            # ===== RECRUITING SERVICES =====
            # WARNING: Most recruiting services prohibit scraping
            # Use only with explicit permission or commercial license
            "247sports": Sports247DataSource,  # 247Sports Composite Rankings
            # Future: ESPN, Rivals, On3
        }

        # Initialize stats datasources
        for source_key, source_class in source_classes.items():
            if self.settings.is_datasource_enabled(source_key):
                try:
                    self.sources[source_key] = source_class()
                    logger.info(f"Enabled stats datasource: {source_key}")
                except Exception as e:
                    logger.error(f"Failed to initialize stats datasource {source_key}", error=str(e))

        # Initialize recruiting datasources
        for source_key, source_class in recruiting_source_classes.items():
            if self.settings.is_datasource_enabled(source_key):
                try:
                    self.recruiting_sources[source_key] = source_class()
                    logger.info(f"Enabled recruiting datasource: {source_key}")
                except Exception as e:
                    logger.error(f"Failed to initialize recruiting datasource {source_key}", error=str(e))

    async def close_all(self) -> None:
        """Close all datasource connections."""
        # Close stats sources
        for source in self.sources.values():
            try:
                await source.close()
            except Exception as e:
                logger.error(f"Error closing stats source", error=str(e))

        # Close recruiting sources
        for source in self.recruiting_sources.values():
            try:
                await source.close()
            except Exception as e:
                logger.error(f"Error closing recruiting source", error=str(e))

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

        # Enrich stats with advanced metrics (TS%, eFG%, A/TO, etc.)
        enriched_stats = []
        for stat in all_stats:
            try:
                enriched_stat = enrich_player_season_stats(stat)
                enriched_stats.append(enriched_stat)
            except Exception as e:
                logger.warning(f"Failed to enrich stats, using original", error=str(e))
                enriched_stats.append(stat)

        logger.info(f"Enriched {len(enriched_stats)} player stats with advanced metrics")

        # Persist enriched stats to DuckDB if enabled
        if self.duckdb and enriched_stats:
            try:
                await self.duckdb.store_player_stats(enriched_stats)
                logger.info(f"Persisted {len(enriched_stats)} player stats to DuckDB")
            except Exception as e:
                logger.error("Failed to persist stats to DuckDB", error=str(e))

        return enriched_stats

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

    # ===== RECRUITING-SPECIFIC METHODS =====

    def get_recruiting_sources(self) -> list[str]:
        """
        Get list of available recruiting source keys.

        Returns:
            List of recruiting source keys
        """
        return list(self.recruiting_sources.keys())

    def get_recruiting_source_info(self) -> dict[str, dict]:
        """
        Get information about all recruiting sources.

        Returns:
            Dictionary with recruiting source metadata
        """
        info = {}
        for key, source in self.recruiting_sources.items():
            info[key] = {
                "name": source.source_name,
                "type": source.source_type.value,
                "region": source.region.value,
                "base_url": source.base_url,
                "enabled": source.is_enabled(),
            }
        return info

    async def get_rankings_all_sources(
        self,
        class_year: int,
        position: Optional[str] = None,
        state: Optional[str] = None,
        sources: Optional[list[str]] = None,
        limit_per_source: int = 100,
        total_limit: int = 200,
    ) -> list[RecruitingRank]:
        """
        Get recruiting rankings from multiple recruiting sources.

        Args:
            class_year: Graduation year (2020-2035)
            position: Filter by position (optional)
            state: Filter by state (optional)
            sources: Specific recruiting sources to query (None = all enabled)
            limit_per_source: Max results per source
            total_limit: Max total results

        Returns:
            List of RecruitingRank objects from all recruiting sources
        """
        # Determine which recruiting sources to query
        query_sources = sources if sources else list(self.recruiting_sources.keys())
        query_sources = [s for s in query_sources if s in self.recruiting_sources]

        if not query_sources:
            logger.warning("No recruiting sources available for query")
            return []

        logger.info(
            f"Getting rankings from {len(query_sources)} recruiting sources",
            class_year=class_year,
            position=position,
            state=state,
            sources=query_sources,
        )

        # Query sources in parallel
        tasks = []
        for source_key in query_sources:
            source = self.recruiting_sources[source_key]
            task = source.get_rankings(
                class_year=class_year,
                limit=limit_per_source,
                position=position,
                state=state,
            )
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_rankings = []
        for i, result in enumerate(results):
            source_key = query_sources[i]

            if isinstance(result, Exception):
                logger.error(f"Recruiting source {source_key} failed", error=str(result))
                continue

            if result:
                all_rankings.extend(result)
                logger.info(f"Recruiting source {source_key} returned {len(result)} rankings")

        # Apply total limit
        all_rankings = all_rankings[:total_limit]

        logger.info(f"Aggregated {len(all_rankings)} rankings from recruiting sources")

        # Persist to DuckDB if enabled
        if self.duckdb and all_rankings:
            try:
                await self.duckdb.store_recruiting_ranks(all_rankings)
                logger.info(f"Persisted {len(all_rankings)} rankings to DuckDB")
            except Exception as e:
                logger.error("Failed to persist rankings to DuckDB", error=str(e))

        return all_rankings

    async def get_player_offers_all_sources(
        self,
        player_id: str,
        sources: Optional[list[str]] = None,
    ) -> list[CollegeOffer]:
        """
        Get college offers for a player from multiple recruiting sources.

        Args:
            player_id: Player identifier
            sources: Specific recruiting sources to query (None = all enabled)

        Returns:
            List of CollegeOffer objects from all recruiting sources
        """
        query_sources = sources if sources else list(self.recruiting_sources.keys())
        query_sources = [s for s in query_sources if s in self.recruiting_sources]

        if not query_sources:
            logger.warning("No recruiting sources available")
            return []

        logger.info(
            f"Getting offers from {len(query_sources)} recruiting sources",
            player_id=player_id,
        )

        # Query sources in parallel
        tasks = []
        for source_key in query_sources:
            source = self.recruiting_sources[source_key]
            task = source.get_offers(player_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_offers = []
        for i, result in enumerate(results):
            source_key = query_sources[i]

            if isinstance(result, Exception):
                logger.error(f"Recruiting source {source_key} failed", error=str(result))
                continue

            if result:
                all_offers.extend(result)
                logger.info(f"Recruiting source {source_key} returned {len(result)} offers")

        logger.info(f"Aggregated {len(all_offers)} offers from recruiting sources")

        # Persist to DuckDB if enabled
        if self.duckdb and all_offers:
            try:
                await self.duckdb.store_college_offers(all_offers)
                logger.info(f"Persisted {len(all_offers)} offers to DuckDB")
            except Exception as e:
                logger.error("Failed to persist offers to DuckDB", error=str(e))

        return all_offers

    async def get_player_predictions_all_sources(
        self,
        player_id: str,
        sources: Optional[list[str]] = None,
    ) -> list[RecruitingPrediction]:
        """
        Get recruiting predictions for a player from multiple sources.

        Args:
            player_id: Player identifier
            sources: Specific recruiting sources to query (None = all enabled)

        Returns:
            List of RecruitingPrediction objects from all recruiting sources
        """
        query_sources = sources if sources else list(self.recruiting_sources.keys())
        query_sources = [s for s in query_sources if s in self.recruiting_sources]

        if not query_sources:
            logger.warning("No recruiting sources available")
            return []

        logger.info(
            f"Getting predictions from {len(query_sources)} recruiting sources",
            player_id=player_id,
        )

        # Query sources in parallel
        tasks = []
        for source_key in query_sources:
            source = self.recruiting_sources[source_key]
            task = source.get_predictions(player_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_predictions = []
        for i, result in enumerate(results):
            source_key = query_sources[i]

            if isinstance(result, Exception):
                logger.error(f"Recruiting source {source_key} failed", error=str(result))
                continue

            if result:
                all_predictions.extend(result)
                logger.info(f"Recruiting source {source_key} returned {len(result)} predictions")

        logger.info(f"Aggregated {len(all_predictions)} predictions from recruiting sources")

        # Persist to DuckDB if enabled
        if self.duckdb and all_predictions:
            try:
                await self.duckdb.store_recruiting_predictions(all_predictions)
                logger.info(f"Persisted {len(all_predictions)} predictions to DuckDB")
            except Exception as e:
                logger.error("Failed to persist predictions to DuckDB", error=str(e))

        return all_predictions

    async def get_player_recruiting_profile_all_sources(
        self,
        player_id: str,
        sources: Optional[list[str]] = None,
    ) -> Optional[RecruitingProfile]:
        """
        Get complete recruiting profile for a player from multiple sources.

        Aggregates rankings, offers, and predictions into a comprehensive
        RecruitingProfile object.

        Args:
            player_id: Player identifier
            sources: Specific recruiting sources to query (None = all enabled)

        Returns:
            RecruitingProfile with aggregated data or None
        """
        query_sources = sources if sources else list(self.recruiting_sources.keys())
        query_sources = [s for s in query_sources if s in self.recruiting_sources]

        if not query_sources:
            logger.warning("No recruiting sources available")
            return None

        logger.info(
            f"Getting recruiting profile from {len(query_sources)} sources",
            player_id=player_id,
        )

        # Query sources in parallel
        tasks = []
        for source_key in query_sources:
            source = self.recruiting_sources[source_key]
            task = source.get_player_recruiting_profile(player_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate profiles
        all_rankings = []
        all_offers = []
        all_predictions = []
        player_name = None

        for i, result in enumerate(results):
            source_key = query_sources[i]

            if isinstance(result, Exception):
                logger.error(f"Recruiting source {source_key} failed", error=str(result))
                continue

            if result:
                # Extract data from profile
                if result.rankings:
                    all_rankings.extend(result.rankings)
                if result.offers:
                    all_offers.extend(result.offers)
                if result.predictions:
                    all_predictions.extend(result.predictions)
                if result.player_name and not player_name:
                    player_name = result.player_name

                logger.info(f"Recruiting source {source_key} returned profile")

        # If we got no data, return None
        if not all_rankings and not all_offers and not all_predictions:
            logger.warning(f"No recruiting profile data found for {player_id}")
            return None

        # Create aggregated profile
        profile = RecruitingProfile(
            player_id=player_id,
            player_name=player_name or "Unknown",
            rankings=all_rankings if all_rankings else None,
            offers=all_offers if all_offers else None,
            predictions=all_predictions if all_predictions else None,
        )

        logger.info(
            f"Aggregated recruiting profile",
            player_id=player_id,
            rankings_count=len(all_rankings),
            offers_count=len(all_offers),
            predictions_count=len(all_predictions),
        )

        return profile


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
