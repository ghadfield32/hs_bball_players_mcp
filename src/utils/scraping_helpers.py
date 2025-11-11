"""
Scraping Helper Functions for DataSource Adapters

This module provides common patterns and utilities for implementing datasource adapters.
All functions follow proven patterns from working adapters (EYBL, PSAL, MN Hub, FIBA Youth).

Usage:
    from ...utils.scraping_helpers import (
        find_stat_table,
        parse_player_from_row,
        parse_season_stats_from_row,
        standardize_stat_columns,
    )
"""

from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from .parser import (
    clean_player_name,
    get_text_or_none,
    parse_float,
    parse_height_to_inches,
    parse_int,
)
from ..models import Position


def find_stat_table(
    soup: BeautifulSoup,
    table_class_hint: Optional[str] = None,
    header_text: Optional[str] = None,
) -> Optional[Tag]:
    """
    Find stats table in parsed HTML.

    Tries multiple strategies:
    1. Find table by class name containing hint
    2. Find table near header containing specific text
    3. Fall back to first table found

    Args:
        soup: BeautifulSoup parsed HTML
        table_class_hint: Optional hint for table class (e.g., "stats", "leaders")
        header_text: Optional text in nearby header (e.g., "Points Leaders")

    Returns:
        Table element or None

    Example:
        table = find_stat_table(soup, table_class_hint="stats")
        table = find_stat_table(soup, header_text="Season Averages")
    """
    # Strategy 1: Find by class hint
    if table_class_hint:
        table = soup.find("table", class_=lambda x: x and table_class_hint.lower() in str(x).lower())
        if table:
            return table

    # Strategy 2: Find table near header
    if header_text:
        headers = soup.find_all(["h1", "h2", "h3", "h4"])
        for header in headers:
            text = get_text_or_none(header)
            if text and header_text.lower() in text.lower():
                # Find next table after this header
                table = header.find_next("table")
                if table:
                    return table

    # Strategy 3: Fall back to first table
    return soup.find("table")


def parse_player_from_row(
    row: dict[str, str],
    source_prefix: str,
    default_level: str = "HIGH_SCHOOL",
    school_state: Optional[str] = None,
) -> dict[str, Any]:
    """
    Parse player data from table row dictionary.

    Handles common column name variations and returns dict ready for Player model.

    Args:
        row: Row dictionary from extract_table_data()
        source_prefix: Prefix for player_id (e.g., "eybl", "psal")
        default_level: Default PlayerLevel if not specified
        school_state: Default school state if applicable

    Returns:
        Dictionary with player fields ready for Player model validation

    Example:
        row = {"Player": "John Doe", "Team": "Lakers", "Pos": "PG"}
        player_data = parse_player_from_row(row, "eybl")
        player = Player(**player_data)
    """
    # Extract name (try multiple column names)
    player_name = (
        row.get("Player")
        or row.get("NAME")
        or row.get("Name")
        or row.get("PLAYER")
        or row.get("PLAYER NAME")
    )

    if not player_name:
        return {}

    # Clean and split name
    player_name = clean_player_name(player_name)
    name_parts = player_name.split()
    first_name = name_parts[0] if len(name_parts) > 0 else player_name
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    # Extract team/school (try multiple column names)
    team_or_school = (
        row.get("Team")
        or row.get("TEAM")
        or row.get("School")
        or row.get("SCHOOL")
        or row.get("Club")
    )

    # Extract position
    position_str = row.get("Pos") or row.get("POS") or row.get("Position")
    pos_enum = None
    if position_str:
        try:
            pos_enum = Position(position_str.upper().strip())
        except ValueError:
            pass

    # Extract height
    height_str = row.get("Height") or row.get("HT") or row.get("Ht")
    height_inches = parse_height_to_inches(height_str) if height_str else None

    # Extract class/grad year
    class_year = (
        row.get("Class")
        or row.get("YR")
        or row.get("Year")
        or row.get("Grade")
    )
    grad_year = parse_grad_year(class_year) if class_year else None

    # Extract jersey number
    number = row.get("#") or row.get("No") or row.get("NUMBER") or row.get("Number")
    jersey_number = parse_int(number) if number else None

    # Create player ID (sanitized)
    player_id = f"{source_prefix}_{player_name.lower().replace(' ', '_')}"

    # Build data dictionary
    player_data = {
        "player_id": player_id,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": player_name,
        "position": pos_enum,
        "height_inches": height_inches,
        "jersey_number": jersey_number,
        "grad_year": grad_year,
    }

    # Add team/school fields
    if team_or_school:
        player_data["team_name"] = team_or_school
        player_data["school_name"] = team_or_school

    if school_state:
        player_data["school_state"] = school_state
        player_data["school_country"] = "USA"

    return player_data


def parse_season_stats_from_row(
    row: dict[str, str],
    player_id: str,
    season: str,
    league_name: str,
) -> dict[str, Any]:
    """
    Parse season statistics from table row dictionary.

    Handles common stat column name variations and calculates derived stats.

    Args:
        row: Row dictionary from extract_table_data()
        player_id: Player identifier
        season: Season string (e.g., "2024-25")
        league_name: League/competition name

    Returns:
        Dictionary with stat fields ready for PlayerSeasonStats model

    Example:
        row = {"Player": "John Doe", "GP": "20", "PPG": "15.5"}
        stats_data = parse_season_stats_from_row(row, "eybl_john_doe", "2024-25", "EYBL")
        stats = PlayerSeasonStats(**stats_data)
    """
    # Extract player name
    player_name = clean_player_name(
        row.get("Player") or row.get("NAME") or row.get("Name") or ""
    )

    # Extract team
    team_name = row.get("Team") or row.get("TEAM") or row.get("School") or ""
    team_id = f"{player_id.split('_')[0]}_team_{team_name.lower().replace(' ', '_')}"

    # Parse games played
    games = parse_int(
        row.get("GP") or row.get("G") or row.get("Games") or row.get("GAMES")
    )

    # Parse averages (per game stats)
    ppg = parse_float(row.get("PPG") or row.get("Points") or row.get("PTS/G"))
    rpg = parse_float(row.get("RPG") or row.get("Rebounds") or row.get("REB/G"))
    apg = parse_float(row.get("APG") or row.get("Assists") or row.get("AST/G"))
    spg = parse_float(row.get("SPG") or row.get("Steals") or row.get("STL/G"))
    bpg = parse_float(row.get("BPG") or row.get("Blocks") or row.get("BLK/G"))

    # Parse totals
    total_points = parse_int(row.get("PTS") or row.get("Points Total"))
    total_rebounds = parse_int(row.get("REB") or row.get("Rebounds Total"))
    total_assists = parse_int(row.get("AST") or row.get("Assists Total"))
    total_steals = parse_int(row.get("STL") or row.get("Steals Total"))
    total_blocks = parse_int(row.get("BLK") or row.get("Blocks Total"))

    # Calculate totals from averages if not provided
    if total_points is None and ppg is not None and games:
        total_points = int(ppg * games)
    if total_rebounds is None and rpg is not None and games:
        total_rebounds = int(rpg * games)
    if total_assists is None and apg is not None and games:
        total_assists = int(apg * games)
    if total_steals is None and spg is not None and games:
        total_steals = int(spg * games)
    if total_blocks is None and bpg is not None and games:
        total_blocks = int(bpg * games)

    # Parse shooting stats
    fgm = parse_int(row.get("FGM") or row.get("FG Made"))
    fga = parse_int(row.get("FGA") or row.get("FG Att") or row.get("FG Attempted"))
    fg_pct = parse_float(row.get("FG%") or row.get("FG Pct"))

    tpm = parse_int(row.get("3PM") or row.get("3P Made"))
    tpa = parse_int(row.get("3PA") or row.get("3P Att") or row.get("3P Attempted"))
    tp_pct = parse_float(row.get("3P%") or row.get("3PT%") or row.get("3P Pct"))

    ftm = parse_int(row.get("FTM") or row.get("FT Made"))
    fta = parse_int(row.get("FTA") or row.get("FT Att") or row.get("FT Attempted"))
    ft_pct = parse_float(row.get("FT%") or row.get("FT Pct"))

    # Build stats dictionary
    stats_data = {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "season": season,
        "league": league_name,
        "games_played": games or 0,
        "points": total_points,
        "points_per_game": ppg,
        "total_rebounds": total_rebounds,
        "rebounds_per_game": rpg,
        "assists": total_assists,
        "assists_per_game": apg,
        "steals": total_steals,
        "steals_per_game": spg,
        "blocks": total_blocks,
        "blocks_per_game": bpg,
        "field_goals_made": fgm,
        "field_goals_attempted": fga,
        "field_goal_percentage": fg_pct,
        "three_pointers_made": tpm,
        "three_pointers_attempted": tpa,
        "three_point_percentage": tp_pct,
        "free_throws_made": ftm,
        "free_throws_attempted": fta,
        "free_throw_percentage": ft_pct,
    }

    return stats_data


def parse_grad_year(class_year_str: str) -> Optional[int]:
    """
    Parse graduation year from various formats.

    Handles formats: "2025", "'25", "Sr", "Senior", "12", etc.

    Args:
        class_year_str: Class year string

    Returns:
        4-digit graduation year or None

    Example:
        parse_grad_year("'25") -> 2025
        parse_grad_year("Sr") -> 2025  (current year)
        parse_grad_year("2026") -> 2026
    """
    if not class_year_str:
        return None

    # Remove quotes and whitespace
    cleaned = class_year_str.strip().replace("'", "")

    # Try as numeric
    year_num = parse_int(cleaned)
    if year_num:
        # Two-digit year
        if year_num < 100:
            return 2000 + year_num
        # Four-digit year
        if year_num > 2020 and year_num < 2040:
            return year_num

    # Map grade names to years (relative to current school year 2024-25)
    grade_map = {
        "fr": 2028,
        "freshman": 2028,
        "so": 2027,
        "sophomore": 2027,
        "jr": 2026,
        "junior": 2026,
        "sr": 2025,
        "senior": 2025,
        "9": 2028,
        "10": 2027,
        "11": 2026,
        "12": 2025,
    }

    grade = cleaned.lower()
    return grade_map.get(grade)


def standardize_stat_columns(row: dict[str, str]) -> dict[str, Optional[float]]:
    """
    Standardize stat column names to canonical form.

    Converts various stat name formats to standardized keys.

    Args:
        row: Row dictionary with varied column names

    Returns:
        Dictionary with standardized stat keys

    Example:
        row = {"PTS": "15", "REB": "8"}
        std = standardize_stat_columns(row)
        # {"points": 15.0, "rebounds": 8.0, ...}
    """
    # Mapping of possible column names to standard keys
    mappings = {
        "points": ["PTS", "Points", "PPG", "PTS/G"],
        "rebounds": ["REB", "Rebounds", "RPG", "REB/G"],
        "assists": ["AST", "Assists", "APG", "AST/G"],
        "steals": ["STL", "Steals", "SPG", "STL/G"],
        "blocks": ["BLK", "Blocks", "BPG", "BLK/G"],
        "turnovers": ["TO", "TOV", "Turnovers", "TPG"],
        "fouls": ["PF", "Fouls", "FPG"],
        "minutes": ["MIN", "Minutes", "MPG"],
        "fg_pct": ["FG%", "FG Pct", "Field Goal %"],
        "tp_pct": ["3P%", "3PT%", "3P Pct"],
        "ft_pct": ["FT%", "FT Pct", "Free Throw %"],
    }

    standardized = {}

    for standard_key, possible_names in mappings.items():
        value = None
        for name in possible_names:
            if name in row:
                value = parse_float(row[name])
                if value is not None:
                    break
        standardized[standard_key] = value

    return standardized


def build_leaderboard_entry(
    rank: int,
    player_name: str,
    stat_value: float,
    stat_name: str,
    season: str,
    source_prefix: str,
    team_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build standardized leaderboard entry dictionary.

    Args:
        rank: Player's rank (1-based)
        player_name: Player name
        stat_value: Stat value
        stat_name: Stat category name
        season: Season string
        source_prefix: Source prefix for player_id
        team_name: Optional team name

    Returns:
        Leaderboard entry dictionary

    Example:
        entry = build_leaderboard_entry(
            rank=1,
            player_name="John Doe",
            stat_value=25.5,
            stat_name="points",
            season="2024-25",
            source_prefix="eybl",
            team_name="Lakers"
        )
    """
    player_id = f"{source_prefix}_{clean_player_name(player_name).lower().replace(' ', '_')}"

    entry = {
        "rank": rank,
        "player_id": player_id,
        "player_name": clean_player_name(player_name),
        "stat_value": stat_value,
        "stat_name": stat_name,
        "season": season,
    }

    if team_name:
        entry["team_name"] = team_name

    return entry


def extract_links_from_table(table: Tag, link_column: str = "Player") -> dict[str, str]:
    """
    Extract links from table cells.

    Useful for finding player profile URLs or game URLs.

    Args:
        table: BeautifulSoup table element
        link_column: Column name containing links

    Returns:
        Dictionary mapping text to URL

    Example:
        links = extract_links_from_table(table, link_column="Player")
        # {"John Doe": "/player/123", "Jane Smith": "/player/456"}
    """
    links = {}

    # Find header index
    headers = []
    thead = table.find("thead")
    if thead:
        header_cells = thead.find_all(["th", "td"])
        headers = [get_text_or_none(cell) for cell in header_cells]

    if link_column not in headers:
        return links

    col_index = headers.index(link_column)

    # Extract links from column
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if col_index < len(cells):
            cell = cells[col_index]
            link = cell.find("a")
            if link:
                text = get_text_or_none(link)
                href = link.get("href")
                if text and href:
                    links[text] = href

    return links


# Implementation Guide Constants
COMMON_ENDPOINTS = {
    "stats": ["stats", "statistics", "player-stats", "season-stats"],
    "leaders": ["leaders", "leaderboard", "top-players", "statistical-leaders"],
    "teams": ["teams", "schools", "clubs", "rosters"],
    "schedule": ["schedule", "games", "fixtures", "results"],
    "standings": ["standings", "rankings", "table"],
}

COMMON_TABLE_CLASSES = [
    "stats",
    "statistics",
    "player-stats",
    "leaders",
    "leaderboard",
    "data-table",
    "sortable",
]
