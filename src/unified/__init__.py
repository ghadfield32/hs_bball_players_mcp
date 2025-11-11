"""
Unified Dataset Layer

Provides canonical schema, categories, and builders for creating
a unified, category-rich dataset from all data sources.

This layer enables:
- Consistent dimensions (sources, competitions, teams, players)
- Consistent facts (games, box scores, rosters, events)
- Categorical encodings for ML/analytics
- Cross-source deduplication and normalization
"""

from .build import build_unified_dataset
from .categories import (
    CIRCUIT_KEYS,
    SOURCE_TYPES,
    SourceType,
    map_source_meta,
    normalize_gender,
    normalize_level,
)
from .mapper import competition_uid, game_uid, team_uid
from .schema import BoxRow, CompetitionRow, GameRow, SourceRow, TeamRow

__all__ = [
    # Builder
    "build_unified_dataset",
    # Categories
    "SourceType",
    "CIRCUIT_KEYS",
    "SOURCE_TYPES",
    "map_source_meta",
    "normalize_gender",
    "normalize_level",
    # Mappers
    "competition_uid",
    "team_uid",
    "game_uid",
    # Schema
    "SourceRow",
    "CompetitionRow",
    "TeamRow",
    "GameRow",
    "BoxRow",
]
