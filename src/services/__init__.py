"""
Services Module

Provides high-level services for data aggregation, storage, and forecasting.
"""

from .aggregator import DataSourceAggregator
from .cache import get_cache
from .coverage_metrics import (
    CoverageFlags,
    CoverageScore,
    compute_coverage_score,
    extract_coverage_flags_from_profile,
    get_coverage_summary,
)
from .duckdb_storage import get_duckdb_storage
from .forecasting import ForecastingDataAggregator, get_forecasting_data_for_player
from .historical_trends import HistoricalTrendsService
from .identity import (
    deduplicate_players,
    resolve_player_uid,
    resolve_player_uid_enhanced,
    calculate_match_confidence,
    get_duplicate_candidates,
    mark_as_merged,
    get_canonical_uid,
)
from .parquet_exporter import get_parquet_exporter
from .player_comparison import PlayerComparisonService
from .rate_limiter import get_rate_limiter
from .source_registry import get_source_registry

__all__ = [
    # Aggregation
    "DataSourceAggregator",
    # Forecasting (NEW - Enhancement 4 & 2 integration)
    "ForecastingDataAggregator",
    "get_forecasting_data_for_player",
    # Analytics (NEW - Enhancement 7 & 8)
    "HistoricalTrendsService",
    "PlayerComparisonService",
    # Coverage Metrics (NEW - Enhancement 9)
    "CoverageFlags",
    "CoverageScore",
    "compute_coverage_score",
    "extract_coverage_flags_from_profile",
    "get_coverage_summary",
    # Storage
    "get_duckdb_storage",
    "get_parquet_exporter",
    # Utilities
    "get_cache",
    "get_rate_limiter",
    "get_source_registry",
    # Identity Resolution (Enhanced - Enhancement 10, Step 5)
    "deduplicate_players",
    "resolve_player_uid",
    "resolve_player_uid_enhanced",
    "calculate_match_confidence",
    "get_duplicate_candidates",
    "mark_as_merged",
    "get_canonical_uid",
]
