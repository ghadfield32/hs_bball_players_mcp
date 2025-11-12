"""
Mapping Functions for Unified IDs

Generates deterministic unique identifiers for competitions, teams, and games.
Ensures consistent cross-source identity resolution.
"""

from typing import Tuple

from .categories import CIRCUIT_KEYS, SOURCE_TYPES


def normalize_string(s: str) -> str:
    """
    Normalize a string for use in IDs.

    Args:
        s: Input string

    Returns:
        Normalized string (lowercase, underscores for spaces)
    """
    return s.lower().strip().replace(" ", "_").replace("-", "_")


def competition_uid(source_key: str, name: str, season: str) -> str:
    """
    Generate unique competition identifier.

    Format: {CIRCUIT}:{season}:{name}

    Args:
        source_key: Source identifier (e.g., "eybl", "fhsaa")
        name: Competition name
        season: Season identifier

    Returns:
        Unique competition UID (max 128 chars)

    Example:
        >>> competition_uid("eybl", "Nike EYBL", "2024")
        'EYBL:2024:nike_eybl'
    """
    base = CIRCUIT_KEYS.get(source_key, source_key.upper())
    normalized_name = normalize_string(name)
    uid = f"{base}:{season}:{normalized_name}"
    return uid[:128]


def team_uid(
    source_key: str, team_name: str, season: str, organizer: str | None = None
) -> str:
    """
    Generate unique team identifier.

    Format: {source_key}:{season}:{team_name}[:{organizer}]

    For AAU events, including the organizer prevents collisions when the same
    team competes in multiple events during the same week.

    Args:
        source_key: Source identifier
        team_name: Team name
        season: Season identifier
        organizer: Event organizer (for AAU events, e.g., "Exposure", "TournyMachine")

    Returns:
        Unique team UID (max 128 chars)

    Example:
        >>> team_uid("eybl", "Team Takeover", "2024")
        'eybl:2024:team_takeover'
        >>> team_uid("exposure_events", "Team Takeover", "2024", "Exposure")
        'exposure_events:2024:team_takeover:exposure'
    """
    normalized_name = normalize_string(team_name)
    uid = f"{source_key}:{season}:{normalized_name}"
    if organizer:
        normalized_organizer = normalize_string(organizer)
        uid = f"{uid}:{normalized_organizer}"
    return uid[:128]


def game_uid(
    source_key: str,
    season: str,
    home: str,
    away: str,
    date_iso: str,
    event_id: str | None = None,
) -> str:
    """
    Generate unique game identifier.

    Format: {source_key}:{season}:{date}:{home}|{away}[:{event_id}]

    For AAU events, including the event_id prevents collisions when the same
    teams play multiple times in different tournaments during the same week.

    Args:
        source_key: Source identifier
        season: Season identifier
        home: Home team name
        away: Away team name
        date_iso: ISO date string (YYYY-MM-DD)
        event_id: Event identifier (for AAU tournaments, e.g., "boo_williams_2024")

    Returns:
        Unique game UID (max 160 chars)

    Example:
        >>> game_uid("eybl", "2024", "Team Takeover", "Expressions Elite", "2024-04-15")
        'eybl:2024:2024-04-15:team_takeover|expressions_elite'
        >>> game_uid("exposure_events", "2024", "Team Takeover", "Expressions", "2024-04-15", "spring_showcase")
        'exposure_events:2024:2024-04-15:team_takeover|expressions:spring_showcase'
    """
    home_norm = normalize_string(home)
    away_norm = normalize_string(away)
    uid = f"{source_key}:{season}:{date_iso}:{home_norm}|{away_norm}"
    if event_id:
        normalized_event = normalize_string(event_id)
        uid = f"{uid}:{normalized_event}"
    return uid[:160]


def player_uid_from_identity(
    name: str, school: str, grad_year: int | None
) -> str:
    """
    Generate player UID using identity resolution logic.

    This should match the identity.resolve_player_uid() function.

    Format: {normalized_name}:{normalized_school}:{grad_year}

    Args:
        name: Player full name
        school: School name
        grad_year: Graduation year

    Returns:
        Unique player UID

    Example:
        >>> player_uid_from_identity("John Smith", "Lincoln HS", 2025)
        'john_smith:lincoln_hs:2025'
    """
    name_norm = normalize_string(name)
    school_norm = normalize_string(school) if school else "unknown"
    year_str = str(grad_year) if grad_year else "unknown"
    return f"{name_norm}:{school_norm}:{year_str}"


def extract_date_from_datetime(dt_str: str) -> str:
    """
    Extract ISO date (YYYY-MM-DD) from datetime string.

    Args:
        dt_str: Datetime string (ISO or other format)

    Returns:
        ISO date string (YYYY-MM-DD)

    Example:
        >>> extract_date_from_datetime("2024-04-15T18:00:00Z")
        '2024-04-15'
    """
    if not dt_str:
        return ""
    # Take first 10 chars if ISO format
    if len(dt_str) >= 10 and dt_str[4] == "-" and dt_str[7] == "-":
        return dt_str[:10]
    return dt_str.split("T")[0] if "T" in dt_str else dt_str


def infer_season_from_date(date_str: str) -> str:
    """
    Infer season from date string.

    Basketball seasons span two years (e.g., "2024-25" for Aug 2024 - July 2025).

    Args:
        date_str: ISO date string (YYYY-MM-DD)

    Returns:
        Season string (e.g., "2024-25")

    Example:
        >>> infer_season_from_date("2024-11-15")
        '2024-25'
        >>> infer_season_from_date("2024-07-15")
        '2023-24'
    """
    if not date_str or len(date_str) < 10:
        return "unknown"

    try:
        year = int(date_str[:4])
        month = int(date_str[5:7])

        # Basketball season: Aug-July (start year - end year)
        # If month >= 8 (August), it's the start of the season
        if month >= 8:
            return f"{year}-{(year + 1) % 100:02d}"
        else:
            return f"{year - 1}-{year % 100:02d}"
    except (ValueError, IndexError):
        return "unknown"
