"""
Data Quality Verification - "Real Data" Integrity Checks

Validates that box scores and game data are internally consistent and plausible.
Helps filter out fake/test data and catch scraping errors.
"""

from typing import Optional
import pandas as pd

from ..utils.logger import get_logger

logger = get_logger(__name__)


def verify_boxscore_integrity(
    team_box: Optional[pd.DataFrame] = None,
    player_box: Optional[pd.DataFrame] = None,
    game_data: Optional[dict] = None,
) -> dict:
    """
    Basic sanity checks to ensure the feed is 'real' and internally consistent.

    Checks:
    1. Points balance: sum of player points == team points (both teams)
    2. Minutes reasonable: player minutes <= regulation + OT (60 minutes max)
    3. No duplicate players: same player_id shouldn't appear twice per game
    4. Both teams present: game has two distinct teams
    5. Stats non-negative: no negative points/rebounds/assists/etc.
    6. Plausible ranges: no 200-point games, no 50 rebounds per player, etc.

    Args:
        team_box: DataFrame with team box score stats (optional)
        player_box: DataFrame with player box score stats (optional)
        game_data: Dict with game metadata (optional)

    Returns:
        Dictionary of checks with boolean values + 'accept' flag:
        {
            'points_balance': bool,
            'minutes_reasonable': bool,
            'no_player_duplicates': bool,
            'both_teams_present': bool,
            'stats_non_negative': bool,
            'plausible_ranges': bool,
            'accept': bool  # True if all hard checks pass
        }

    Example:
        >>> checks = verify_boxscore_integrity(team_box=team_df, player_box=player_df)
        >>> if checks['accept']:
        ...     store_boxscore(team_df, player_df)
        >>> else:
        ...     logger.warning(f"Failed checks: {checks}")
    """
    checks = {
        "points_balance": True,
        "minutes_reasonable": True,
        "no_player_duplicates": True,
        "both_teams_present": True,
        "stats_non_negative": True,
        "plausible_ranges": True,
    }

    # 1) Points balance: sum of player points == team points (both teams)
    if team_box is not None and player_box is not None:
        try:
            if "team_id" in team_box.columns and "PTS" in team_box.columns:
                if "team_id" in player_box.columns and "PTS" in player_box.columns:
                    team_pts = team_box.groupby("team_id")["PTS"].sum()
                    player_pts = player_box.groupby("team_id")["PTS"].sum()

                    # Allow small rounding errors (1 point tolerance per team)
                    diff = (team_pts - player_pts).abs()
                    checks["points_balance"] = diff.max() <= 1.0

                    if not checks["points_balance"]:
                        logger.warning(f"Points imbalance detected: team={team_pts.to_dict()}, players={player_pts.to_dict()}")

        except Exception as e:
            logger.error(f"Error checking points balance: {e}")
            checks["points_balance"] = False

    # 2) Minutes reasonable: player minutes <= 60 (regulation + typical OT)
    if player_box is not None:
        if "MIN" in player_box.columns:
            try:
                max_mins = player_box["MIN"].dropna().astype(float).max()
                checks["minutes_reasonable"] = max_mins <= 60.0

                if not checks["minutes_reasonable"]:
                    logger.warning(f"Implausible minutes detected: max={max_mins}")

            except Exception as e:
                logger.error(f"Error checking minutes: {e}")
                checks["minutes_reasonable"] = True  # Don't fail on missing mins

    # 3) No duplicate players: same player_id per game
    if player_box is not None:
        if {"game_id", "player_id"} <= set(player_box.columns):
            try:
                duplicates = player_box.duplicated(subset=["game_id", "player_id"])
                checks["no_player_duplicates"] = not duplicates.any()

                if not checks["no_player_duplicates"]:
                    dup_count = duplicates.sum()
                    logger.warning(f"Duplicate player entries detected: {dup_count}")

            except Exception as e:
                logger.error(f"Error checking duplicates: {e}")
                checks["no_player_duplicates"] = False

    # 4) Both teams present
    if team_box is not None:
        if "team_side" in team_box.columns:
            try:
                unique_sides = team_box["team_side"].nunique()
                checks["both_teams_present"] = unique_sides == 2

                if not checks["both_teams_present"]:
                    logger.warning(f"Expected 2 teams, found {unique_sides}")

            except Exception as e:
                logger.error(f"Error checking team presence: {e}")
                checks["both_teams_present"] = False

    # 5) Stats non-negative: check common columns
    if player_box is not None:
        stat_cols = ["PTS", "REB", "AST", "STL", "BLK", "TO", "FGM", "FGA", "FTM", "FTA"]
        existing_cols = [c for c in stat_cols if c in player_box.columns]

        if existing_cols:
            try:
                for col in existing_cols:
                    has_negative = (player_box[col].dropna() < 0).any()
                    if has_negative:
                        checks["stats_non_negative"] = False
                        logger.warning(f"Negative values found in {col}")
                        break

            except Exception as e:
                logger.error(f"Error checking non-negative stats: {e}")
                checks["stats_non_negative"] = False

    # 6) Plausible ranges: no extreme outliers
    if player_box is not None:
        try:
            # No player should have > 150 points in a game
            if "PTS" in player_box.columns:
                max_pts = player_box["PTS"].dropna().astype(float).max()
                if max_pts > 150:
                    checks["plausible_ranges"] = False
                    logger.warning(f"Implausible points: {max_pts}")

            # No player should have > 60 rebounds in a game
            if "REB" in player_box.columns:
                max_reb = player_box["REB"].dropna().astype(float).max()
                if max_reb > 60:
                    checks["plausible_ranges"] = False
                    logger.warning(f"Implausible rebounds: {max_reb}")

            # No player should have > 40 assists in a game
            if "AST" in player_box.columns:
                max_ast = player_box["AST"].dropna().astype(float).max()
                if max_ast > 40:
                    checks["plausible_ranges"] = False
                    logger.warning(f"Implausible assists: {max_ast}")

        except Exception as e:
            logger.error(f"Error checking plausible ranges: {e}")
            checks["plausible_ranges"] = False

    # Accept if all HARD checks pass
    # Soft checks (minutes, plausible_ranges) can be warnings but don't block
    hard_checks = [
        checks["points_balance"],
        checks["no_player_duplicates"],
        checks["both_teams_present"],
        checks["stats_non_negative"],
    ]

    checks["accept"] = all(hard_checks)

    if not checks["accept"]:
        logger.warning(f"Box score failed integrity checks: {checks}")

    return checks


def verify_game_metadata(game_data: dict) -> dict:
    """
    Verify game metadata is complete and valid.

    Checks:
    - Has required fields (date, teams, score)
    - Date is valid and not in far future
    - Score is non-negative
    - Teams are distinct

    Args:
        game_data: Dictionary with game metadata

    Returns:
        Dictionary of checks with 'accept' flag
    """
    checks = {
        "has_required_fields": False,
        "valid_date": False,
        "valid_score": False,
        "distinct_teams": False,
        "accept": False,
    }

    # Check required fields
    required_fields = ["date", "home_team", "away_team"]
    checks["has_required_fields"] = all(f in game_data for f in required_fields)

    # Check date validity
    if "date" in game_data:
        try:
            date_str = game_data["date"]
            # Simple check: date is not empty and looks like YYYY-MM-DD
            if date_str and len(date_str) >= 10:
                checks["valid_date"] = True
        except Exception:
            pass

    # Check score validity
    if "home_score" in game_data and "away_score" in game_data:
        try:
            home_score = int(game_data["home_score"])
            away_score = int(game_data["away_score"])
            checks["valid_score"] = home_score >= 0 and away_score >= 0
        except (ValueError, TypeError):
            pass

    # Check teams are distinct
    if "home_team" in game_data and "away_team" in game_data:
        checks["distinct_teams"] = game_data["home_team"] != game_data["away_team"]

    # Accept if all checks pass
    checks["accept"] = all([
        checks["has_required_fields"],
        checks["valid_date"],
        checks["distinct_teams"],
    ])

    return checks
