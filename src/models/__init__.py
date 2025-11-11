"""
Basketball Statistics Data Models

Comprehensive Pydantic models for basketball player, team, game, and statistics data.
"""

# Source and metadata models
from .source import (
    DataQualityFlag,
    DataSource,
    DataSourceRegion,
    DataSourceType,
    RateLimitStatus,
)

# Player models
from .player import Player, PlayerIdentifier, PlayerLevel, Position

# Team models
from .team import Team, TeamLevel, TeamStandings

# Game models
from .game import Game, GameSchedule, GameStatus, GameType

# Statistics models
from .stats import (
    BaseStats,
    LeaderboardEntry,
    PlayerGameStats,
    PlayerSeasonStats,
    TeamGameStats,
)

__all__ = [
    # Source models
    "DataSource",
    "DataSourceType",
    "DataSourceRegion",
    "DataQualityFlag",
    "RateLimitStatus",
    # Player models
    "Player",
    "PlayerIdentifier",
    "Position",
    "PlayerLevel",
    # Team models
    "Team",
    "TeamLevel",
    "TeamStandings",
    # Game models
    "Game",
    "GameSchedule",
    "GameStatus",
    "GameType",
    # Statistics models
    "BaseStats",
    "PlayerGameStats",
    "PlayerSeasonStats",
    "TeamGameStats",
    "LeaderboardEntry",
]
