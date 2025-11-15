"""
Advanced Basketball Statistics Calculator

Calculates advanced metrics from basic box score stats.
All formulas based on Basketball Reference and NBA Analytics standards.

Author: Claude Code
Date: 2025-11-15
"""

from typing import Optional

from ..models import PlayerGameStats, PlayerSeasonStats


def calculate_true_shooting_percentage(
    points: Optional[int],
    field_goals_attempted: Optional[int],
    free_throws_attempted: Optional[int],
) -> Optional[float]:
    """
    Calculate True Shooting Percentage.

    TS% = PTS / (2 * (FGA + 0.44 * FTA))

    True Shooting % accounts for the fact that 3-pointers are worth more
    and free throws don't count as FGA. It's the best single measure of
    shooting efficiency.

    Args:
        points: Total points scored
        field_goals_attempted: Total field goal attempts
        free_throws_attempted: Total free throw attempts

    Returns:
        True Shooting % as decimal (0.0-1.0), or None if data missing

    Example:
        >>> calculate_true_shooting_percentage(500, 400, 100)
        0.568  # 56.8% TS%
    """
    if points is None or field_goals_attempted is None or free_throws_attempted is None:
        return None

    if field_goals_attempted == 0 and free_throws_attempted == 0:
        return None

    # TS% formula uses 0.44 as FTA coefficient (accounts for and-1s)
    true_shot_attempts = 2 * (field_goals_attempted + 0.44 * free_throws_attempted)

    if true_shot_attempts == 0:
        return None

    return points / true_shot_attempts


def calculate_effective_fg_percentage(
    field_goals_made: Optional[int],
    three_pointers_made: Optional[int],
    field_goals_attempted: Optional[int],
) -> Optional[float]:
    """
    Calculate Effective Field Goal Percentage.

    eFG% = (FGM + 0.5 * 3PM) / FGA

    Adjusts field goal % to account for the fact that 3-pointers are
    worth more than 2-pointers. More accurate than raw FG%.

    Args:
        field_goals_made: Total field goals made
        three_pointers_made: Total 3-pointers made
        field_goals_attempted: Total field goal attempts

    Returns:
        Effective FG% as decimal (0.0-1.0), or None if data missing

    Example:
        >>> calculate_effective_fg_percentage(200, 50, 400)
        0.563  # 56.3% eFG%
    """
    if field_goals_made is None or three_pointers_made is None or field_goals_attempted is None:
        return None

    if field_goals_attempted == 0:
        return None

    # Add 0.5 * 3PM to account for extra point value
    effective_fg_made = field_goals_made + 0.5 * three_pointers_made

    return effective_fg_made / field_goals_attempted


def calculate_assist_to_turnover_ratio(
    assists: Optional[int],
    turnovers: Optional[int],
) -> Optional[float]:
    """
    Calculate Assist-to-Turnover Ratio.

    A/TO = AST / TOV

    Measures decision making and ball security.
    Higher is better. Elite guards: 3.0+, Good: 2.0+, Average: 1.5

    Args:
        assists: Total assists
        turnovers: Total turnovers

    Returns:
        A/TO ratio, or None if data missing

    Example:
        >>> calculate_assist_to_turnover_ratio(150, 50)
        3.0  # Excellent decision making
    """
    if assists is None or turnovers is None:
        return None

    if turnovers == 0:
        # Avoid division by zero, cap at reasonable max
        return 99.0 if assists > 0 else 0.0

    return assists / turnovers


def calculate_two_point_percentage(
    field_goals_made: Optional[int],
    three_pointers_made: Optional[int],
    field_goals_attempted: Optional[int],
    three_pointers_attempted: Optional[int],
) -> Optional[float]:
    """
    Calculate 2-Point Field Goal Percentage.

    2P% = (FGM - 3PM) / (FGA - 3PA)

    Isolates 2-point shooting efficiency from 3-point shooting.

    Args:
        field_goals_made: Total field goals made
        three_pointers_made: Total 3-pointers made
        field_goals_attempted: Total field goal attempts
        three_pointers_attempted: Total 3-point attempts

    Returns:
        2P% as decimal (0.0-1.0), or None if data missing
    """
    if any(x is None for x in [field_goals_made, three_pointers_made,
                                field_goals_attempted, three_pointers_attempted]):
        return None

    two_point_made = field_goals_made - three_pointers_made
    two_point_attempted = field_goals_attempted - three_pointers_attempted

    if two_point_attempted == 0:
        return None

    return two_point_made / two_point_attempted


def calculate_three_point_attempt_rate(
    three_pointers_attempted: Optional[int],
    field_goals_attempted: Optional[int],
) -> Optional[float]:
    """
    Calculate 3-Point Attempt Rate.

    3PAr = 3PA / FGA

    Measures shot selection (percentage of shots that are 3-pointers).
    Modern analytics favor higher rates (35-45% for guards, 25-35% for bigs).

    Args:
        three_pointers_attempted: Total 3-point attempts
        field_goals_attempted: Total field goal attempts

    Returns:
        3PAr as decimal (0.0-1.0), or None if data missing
    """
    if three_pointers_attempted is None or field_goals_attempted is None:
        return None

    if field_goals_attempted == 0:
        return None

    return three_pointers_attempted / field_goals_attempted


def calculate_free_throw_rate(
    free_throws_attempted: Optional[int],
    field_goals_attempted: Optional[int],
) -> Optional[float]:
    """
    Calculate Free Throw Rate.

    FTr = FTA / FGA

    Measures ability to get to the free throw line.
    Higher rates indicate aggressiveness and drawing fouls.
    Elite: 0.40+, Good: 0.30+, Average: 0.20

    Args:
        free_throws_attempted: Total free throw attempts
        field_goals_attempted: Total field goal attempts

    Returns:
        FTr as decimal, or None if data missing
    """
    if free_throws_attempted is None or field_goals_attempted is None:
        return None

    if field_goals_attempted == 0:
        return None

    return free_throws_attempted / field_goals_attempted


def calculate_points_per_shot_attempt(
    points: Optional[int],
    field_goals_attempted: Optional[int],
    free_throws_attempted: Optional[int],
) -> Optional[float]:
    """
    Calculate Points Per Shot Attempt.

    PPS = PTS / (FGA + 0.44 * FTA)

    Similar to TS% but in points rather than percentage.
    Good scorers: 1.15+, Elite: 1.25+

    Args:
        points: Total points
        field_goals_attempted: Total FGA
        free_throws_attempted: Total FTA

    Returns:
        Points per shot attempt, or None if data missing
    """
    if points is None or field_goals_attempted is None or free_throws_attempted is None:
        return None

    total_shot_attempts = field_goals_attempted + 0.44 * free_throws_attempted

    if total_shot_attempts == 0:
        return None

    return points / total_shot_attempts


def calculate_rebounds_per_40(
    total_rebounds: Optional[int],
    minutes_played: Optional[float],
) -> Optional[float]:
    """
    Calculate Rebounds Per 40 Minutes.

    REB40 = (REB / MIN) * 40

    Normalizes rebounding to per-40-minute rate for comparison.

    Args:
        total_rebounds: Total rebounds
        minutes_played: Total minutes played

    Returns:
        Rebounds per 40 minutes, or None if data missing
    """
    if total_rebounds is None or minutes_played is None:
        return None

    if minutes_played == 0:
        return None

    return (total_rebounds / minutes_played) * 40


def calculate_points_per_40(
    points: Optional[int],
    minutes_played: Optional[float],
) -> Optional[float]:
    """
    Calculate Points Per 40 Minutes.

    PTS40 = (PTS / MIN) * 40

    Normalizes scoring to per-40-minute rate for comparison.

    Args:
        points: Total points
        minutes_played: Total minutes played

    Returns:
        Points per 40 minutes, or None if data missing
    """
    if points is None or minutes_played is None:
        return None

    if minutes_played == 0:
        return None

    return (points / minutes_played) * 40


def enrich_player_season_stats(stats: PlayerSeasonStats) -> PlayerSeasonStats:
    """
    Calculate and add all advanced metrics to PlayerSeasonStats.

    Takes existing PlayerSeasonStats and adds calculated advanced metrics
    as custom attributes. Does not modify the original Pydantic model,
    but adds calculated fields dynamically.

    Args:
        stats: PlayerSeasonStats object with basic box score stats

    Returns:
        Same PlayerSeasonStats object with added calculated fields

    Calculated Fields Added:
        - true_shooting_pct: True Shooting %
        - effective_fg_pct: Effective FG %
        - assist_to_turnover: Assist/Turnover ratio
        - two_point_pct: 2-Point FG %
        - three_point_attempt_rate: 3PA rate
        - free_throw_rate: FT rate
        - points_per_shot: Points per shot attempt
        - rebounds_per_40: Rebounds per 40 min
        - points_per_40: Points per 40 min

    Example:
        >>> stats = PlayerSeasonStats(points=500, field_goals_attempted=400, ...)
        >>> enriched = enrich_player_season_stats(stats)
        >>> print(enriched.true_shooting_pct)
        0.568
    """
    # Calculate all advanced metrics
    ts_pct = calculate_true_shooting_percentage(
        stats.points,
        stats.field_goals_attempted,
        stats.free_throws_attempted,
    )

    efg_pct = calculate_effective_fg_percentage(
        stats.field_goals_made,
        stats.three_pointers_made,
        stats.field_goals_attempted,
    )

    ast_to = calculate_assist_to_turnover_ratio(
        stats.assists,
        stats.turnovers,
    )

    two_pt_pct = calculate_two_point_percentage(
        stats.field_goals_made,
        stats.three_pointers_made,
        stats.field_goals_attempted,
        stats.three_pointers_attempted,
    )

    three_pt_rate = calculate_three_point_attempt_rate(
        stats.three_pointers_attempted,
        stats.field_goals_attempted,
    )

    ft_rate = calculate_free_throw_rate(
        stats.free_throws_attempted,
        stats.field_goals_attempted,
    )

    pts_per_shot = calculate_points_per_shot_attempt(
        stats.points,
        stats.field_goals_attempted,
        stats.free_throws_attempted,
    )

    reb_per_40 = calculate_rebounds_per_40(
        stats.total_rebounds,
        stats.minutes_played,
    )

    pts_per_40 = calculate_points_per_40(
        stats.points,
        stats.minutes_played,
    )

    # Add calculated fields as attributes (not Pydantic fields)
    # These can be accessed but won't be part of model schema
    setattr(stats, "true_shooting_pct", ts_pct)
    setattr(stats, "effective_fg_pct", efg_pct)
    setattr(stats, "assist_to_turnover", ast_to)
    setattr(stats, "two_point_pct", two_pt_pct)
    setattr(stats, "three_point_attempt_rate", three_pt_rate)
    setattr(stats, "free_throw_rate", ft_rate)
    setattr(stats, "points_per_shot", pts_per_shot)
    setattr(stats, "rebounds_per_40", reb_per_40)
    setattr(stats, "points_per_40", pts_per_40)

    return stats


def enrich_player_game_stats(stats: PlayerGameStats) -> PlayerGameStats:
    """
    Calculate and add all advanced metrics to PlayerGameStats.

    Same as enrich_player_season_stats but for individual games.

    Args:
        stats: PlayerGameStats object

    Returns:
        Same PlayerGameStats object with added calculated fields
    """
    # Use same calculations as season stats
    ts_pct = calculate_true_shooting_percentage(
        stats.points,
        stats.field_goals_attempted,
        stats.free_throws_attempted,
    )

    efg_pct = calculate_effective_fg_percentage(
        stats.field_goals_made,
        stats.three_pointers_made,
        stats.field_goals_attempted,
    )

    ast_to = calculate_assist_to_turnover_ratio(
        stats.assists,
        stats.turnovers,
    )

    # Add calculated fields
    setattr(stats, "true_shooting_pct", ts_pct)
    setattr(stats, "effective_fg_pct", efg_pct)
    setattr(stats, "assist_to_turnover", ast_to)

    return stats


def get_advanced_stats_summary(stats: PlayerSeasonStats) -> dict:
    """
    Get dictionary of all calculated advanced stats.

    Useful for API responses or database storage.

    Args:
        stats: Enriched PlayerSeasonStats object

    Returns:
        Dictionary with all advanced metrics

    Example:
        >>> enriched = enrich_player_season_stats(stats)
        >>> summary = get_advanced_stats_summary(enriched)
        >>> print(summary["true_shooting_pct"])
        0.568
    """
    return {
        "true_shooting_pct": getattr(stats, "true_shooting_pct", None),
        "effective_fg_pct": getattr(stats, "effective_fg_pct", None),
        "assist_to_turnover": getattr(stats, "assist_to_turnover", None),
        "two_point_pct": getattr(stats, "two_point_pct", None),
        "three_point_attempt_rate": getattr(stats, "three_point_attempt_rate", None),
        "free_throw_rate": getattr(stats, "free_throw_rate", None),
        "points_per_shot": getattr(stats, "points_per_shot", None),
        "rebounds_per_40": getattr(stats, "rebounds_per_40", None),
        "points_per_40": getattr(stats, "points_per_40", None),
    }
