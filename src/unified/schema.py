"""
Canonical Schema Definitions

Defines the unified schema for dimensions and facts tables.
All data sources are normalized into these structures.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceRow:
    """
    Dimension: Data source metadata.

    Tracks all data sources and their characteristics.
    """

    source_key: str  # Unique source identifier (e.g., "eybl", "fhsaa")
    source_url: str  # Base URL of the source
    fetched_at: str  # ISO timestamp of last fetch
    region: str  # Geographic region (US, CANADA, EUROPE, etc.)
    country: str  # ISO-2 country code
    state: Optional[str] = None  # USPS state code (US only)


@dataclass
class CompetitionRow:
    """
    Dimension: Competition/league/tournament metadata.

    Represents a season of a competition (e.g., "EYBL 2024", "GHSA 2024-25").
    """

    competition_uid: str  # Unique competition identifier
    name: str  # Competition display name
    circuit: str  # Canonical circuit name (from CIRCUIT_KEYS)
    level: str  # Competition level (HS, PREP, U16, U17, U18, U21)
    gender: str  # Gender (M/F)
    age_group: Optional[str]  # Age group if applicable (U16, U17, U18, etc.)
    season: str  # Season identifier (e.g., "2024", "2024-25")
    country: str  # ISO-2 country code
    state: Optional[str] = None  # USPS state code (US only)


@dataclass
class TeamRow:
    """
    Dimension: Team metadata.

    Represents a team in a specific season/competition.
    """

    team_uid: str  # Unique team identifier
    team_name: str  # Team display name
    school_uid: Optional[str]  # School identifier (if applicable)
    org_type: str  # Organization type (SCHOOL, CLUB, AAU, ACADEMY, etc.)
    country: str  # ISO-2 country code
    state: Optional[str]  # USPS state code
    city: Optional[str]  # City name


@dataclass
class PlayerRow:
    """
    Dimension: Player metadata.

    Represents a unique player across all sources.
    """

    player_uid: str  # Unique player identifier (from identity resolution)
    full_name: str  # Player full name
    birth_year: Optional[int]  # Birth year
    height_cm: Optional[float]  # Height in centimeters
    position_std: Optional[str]  # Standardized position (PG, SG, SF, PF, C)
    handedness: Optional[str]  # Handedness (R/L)
    country: str  # Country of origin


@dataclass
class GameRow:
    """
    Fact: Game results.

    Represents a single game with teams, score, and metadata.
    """

    game_uid: str  # Unique game identifier
    competition_uid: str  # FK to CompetitionRow
    season: str  # Season identifier
    date_utc: str  # ISO datetime of game (UTC)
    venue: Optional[str]  # Venue name
    home_team_uid: str  # FK to TeamRow
    away_team_uid: str  # FK to TeamRow
    result: Optional[str]  # Game result (e.g., "85-72")
    source_id: str  # Source key
    source_url: str  # URL of the game page
    fetched_at: str  # ISO timestamp of fetch


@dataclass
class BoxRow:
    """
    Fact: Box score statistics.

    Represents player statistics for a single game.
    """

    game_uid: str  # FK to GameRow
    player_uid: str  # FK to PlayerRow
    team_uid: str  # FK to TeamRow
    minutes: Optional[float]  # Minutes played
    pts: Optional[int]  # Points
    fgm: Optional[int]  # Field goals made
    fga: Optional[int]  # Field goals attempted
    fg3m: Optional[int]  # 3-pointers made
    fg3a: Optional[int]  # 3-pointers attempted
    ftm: Optional[int]  # Free throws made
    fta: Optional[int]  # Free throws attempted
    oreb: Optional[int]  # Offensive rebounds
    dreb: Optional[int]  # Defensive rebounds
    reb: Optional[int]  # Total rebounds
    ast: Optional[int]  # Assists
    stl: Optional[int]  # Steals
    blk: Optional[int]  # Blocks
    tov: Optional[int]  # Turnovers
    pf: Optional[int]  # Personal fouls
    plus_minus: Optional[int]  # Plus/minus
    starters_flag: Optional[bool]  # Started the game
    source_id: str  # Source key


@dataclass
class RosterRow:
    """
    Fact: Team roster entries.

    Represents a player's membership on a team for a season.
    """

    season: str  # Season identifier
    competition_uid: str  # FK to CompetitionRow
    team_uid: str  # FK to TeamRow
    player_uid: str  # FK to PlayerRow
    jersey: Optional[int]  # Jersey number
    role: Optional[str]  # Role (starter, bench, captain, etc.)
    source_id: str  # Source key


@dataclass
class EventRow:
    """
    Fact: Non-game events (brackets, camps, showcases).

    Represents events that don't have box score data.
    """

    season: str  # Season identifier
    competition_uid: str  # FK to CompetitionRow
    event_type: str  # Event type (BRACKET, CAMP, SHOWCASE, PDF, etc.)
    label: str  # Event label/name
    date_utc: str  # ISO datetime of event
    meta: Optional[str]  # JSON metadata
    source_id: str  # Source key
