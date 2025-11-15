"""
High School Basketball Forecasting Module

This module provides tools for building unified HS player-season datasets
suitable for college-success forecasting models.

The dataset builder combines data from multiple sources:
- MaxPreps (HS statistics)
- Recruiting rankings (ratings, offers, physical measurements)
- EYBL (elite circuit performance)

All sources are standardized into a canonical schema with stable player UIDs
for cross-source linkage.

UPDATED (Phase 14): Added export adapters and schema validators for
bridging existing datasources to the forecasting pipeline.
"""

from .dataset_builder import (
    HSForecastingConfig,
    build_hs_player_season_dataset,
    make_player_uid,
    normalize_name,
    standardize_eybl_stats,
    standardize_maxpreps_stats,
    standardize_recruiting,
)
from .exporters import (
    create_mock_maxpreps_parquet,
    create_mock_recruiting_csv,
    export_eybl_from_duckdb,
    export_players_from_duckdb,
)
from .schema_validator import (
    SchemaValidationResult,
    check_join_compatibility,
    generate_schema_report,
    validate_eybl_schema,
    validate_maxpreps_schema,
    validate_recruiting_schema,
)

__all__ = [
    # Dataset Builder Core
    "HSForecastingConfig",
    "build_hs_player_season_dataset",
    "make_player_uid",
    "normalize_name",
    "standardize_eybl_stats",
    "standardize_maxpreps_stats",
    "standardize_recruiting",
    # Export Adapters
    "export_eybl_from_duckdb",
    "export_players_from_duckdb",
    "create_mock_recruiting_csv",
    "create_mock_maxpreps_parquet",
    # Schema Validators
    "validate_maxpreps_schema",
    "validate_recruiting_schema",
    "validate_eybl_schema",
    "generate_schema_report",
    "check_join_compatibility",
    "SchemaValidationResult",
]
