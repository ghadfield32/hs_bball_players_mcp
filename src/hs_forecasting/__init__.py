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

__all__ = [
    "HSForecastingConfig",
    "build_hs_player_season_dataset",
    "make_player_uid",
    "normalize_name",
    "standardize_eybl_stats",
    "standardize_maxpreps_stats",
    "standardize_recruiting",
]
