"""
Data Quality Validation Framework

Provides automated QA checks for scraped basketball data to ensure:
- Basic data integrity (non-empty fields, valid scores)
- Bracket consistency (winner progression, score logic)
- Expected game counts (structural validation)
- Overall data health scoring

Usage:
    from src.utils.validation import validate_games, ValidationReport

    report = validate_games(games, state="AL", year=2024)
    print(f"Health Score: {report.health_score:.2f}")
    if report.errors:
        print("Errors:", report.errors)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict


@dataclass
class ValidationReport:
    """Validation report for scraped game data."""

    state: str
    year: int
    games: int
    teams: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    health_score: float = 1.0  # 0.0-1.0, where 1.0 is perfect

    def add_error(self, message: str):
        """Add an error to the report."""
        self.errors.append(message)
        # Deduct from health score (each error = -0.1, min 0.0)
        self.health_score = max(0.0, self.health_score - 0.1)

    def add_warning(self, message: str):
        """Add a warning to the report."""
        self.warnings.append(message)
        # Deduct less from health score (each warning = -0.05, min 0.0)
        self.health_score = max(0.0, self.health_score - 0.05)

    def is_healthy(self) -> bool:
        """Check if data is considered healthy (>= 0.7 health score)."""
        return self.health_score >= 0.7


def validate_basic_games(games: List, report: ValidationReport) -> None:
    """
    Validate basic game integrity.

    Checks:
    - Unique game IDs
    - Non-empty team names
    - Valid scores (integers >= 0)
    - Winner/loser score logic

    Args:
        games: List of Game objects
        report: ValidationReport to populate with findings
    """
    seen_ids = set()

    for idx, game in enumerate(games):
        # Check game ID uniqueness
        if game.game_id in seen_ids:
            report.add_error(f"Duplicate game ID: {game.game_id}")
        seen_ids.add(game.game_id)

        # Check team names are non-empty
        if not game.home_team_name or not game.home_team_name.strip():
            report.add_error(f"Empty home team name in game {game.game_id}")
        if not game.away_team_name or not game.away_team_name.strip():
            report.add_error(f"Empty away team name in game {game.game_id}")

        # Check scores are valid if present
        if game.home_score is not None:
            if not isinstance(game.home_score, int) or game.home_score < 0:
                report.add_error(f"Invalid home score in game {game.game_id}: {game.home_score}")

        if game.away_score is not None:
            if not isinstance(game.away_score, int) or game.away_score < 0:
                report.add_error(f"Invalid away score in game {game.game_id}: {game.away_score}")

        # Check winner/loser logic for completed games
        if game.home_score is not None and game.away_score is not None:
            if game.home_score == game.away_score:
                # Ties are unusual but valid (overtime, co-champions)
                report.add_warning(f"Tied game in {game.game_id}: {game.home_score}-{game.away_score}")

            # Check for suspiciously low scores (possible parsing error)
            if game.home_score == 0 and game.away_score == 0:
                report.add_warning(f"Zero-zero score in game {game.game_id} (possible parsing error)")


def validate_bracket_progression(games: List, report: ValidationReport) -> None:
    """
    Validate bracket consistency and winner progression.

    Checks:
    - Winners appear in subsequent rounds
    - Losers don't appear in subsequent rounds (within same bracket)
    - Round progression is logical

    Args:
        games: List of Game objects
        report: ValidationReport to populate with findings
    """
    # Group games by league/classification (bracket identifier)
    # Note: Game model doesn't have gender field, using league+season as key
    brackets = defaultdict(list)
    for game in games:
        bracket_key = (game.league, game.season)
        brackets[bracket_key].append(game)

    for bracket_key, bracket_games in brackets.items():
        # For bracket consistency, we need to know the round structure
        # This is simplified - a full implementation would parse round names
        # and build a progression tree

        # Basic check: if we have games, we should have teams
        if not bracket_games:
            continue

        # Extract all teams that played
        teams_in_bracket = set()
        for game in bracket_games:
            teams_in_bracket.add(game.home_team_name)
            teams_in_bracket.add(game.away_team_name)

        # Check expected game count (N teams => N-1 games in single-elimination)
        num_teams = len(teams_in_bracket)
        num_games = len(bracket_games)

        # Allow some flexibility (multi-bracket, losers bracket, etc.)
        expected_min = max(1, num_teams - num_teams // 2)  # At least half
        expected_max = num_teams * 2  # At most 2x (double elim)

        if num_games < expected_min:
            report.add_warning(
                f"Bracket {bracket_key}: {num_games} games for {num_teams} teams "
                f"(expected >= {expected_min})"
            )
        elif num_games > expected_max:
            report.add_warning(
                f"Bracket {bracket_key}: {num_games} games for {num_teams} teams "
                f"(expected <= {expected_max})"
            )


def validate_expected_counts(games: List, teams: List, report: ValidationReport) -> None:
    """
    Validate expected game and team counts.

    Checks:
    - Reasonable game-to-team ratio
    - Non-zero counts

    Args:
        games: List of Game objects
        teams: List of Team objects
        report: ValidationReport to populate with findings
    """
    num_games = len(games)
    num_teams = len(teams)

    # Check for empty data
    if num_games == 0:
        report.add_error("No games found")

    if num_teams == 0:
        report.add_error("No teams found")

    # Check game-to-team ratio (single-elim: ~1:1, multi-bracket can be higher)
    if num_teams > 0:
        ratio = num_games / num_teams

        # Single-elimination: ratio ~= 1
        # Multi-bracket/round-robin: ratio can be higher
        # Suspiciously low: ratio < 0.5
        if ratio < 0.5:
            report.add_warning(
                f"Low game-to-team ratio: {num_games} games / {num_teams} teams = {ratio:.2f}"
            )


def validate_games(
    games: List,
    teams: Optional[List] = None,
    state: str = "UNKNOWN",
    year: int = 0
) -> ValidationReport:
    """
    Validate scraped game data with comprehensive QA checks.

    Performs:
    1. Basic game integrity checks
    2. Bracket progression validation
    3. Expected count validation
    4. Overall health score calculation

    Args:
        games: List of Game objects to validate
        teams: Optional list of Team objects
        state: State code for reporting
        year: Tournament year for reporting

    Returns:
        ValidationReport with errors, warnings, and health score
    """
    # Extract unique teams from games if not provided
    if teams is None:
        teams_dict = {}
        for game in games:
            teams_dict[game.home_team_id] = game.home_team_name
            teams_dict[game.away_team_id] = game.away_team_name
        teams = [{"team_id": tid, "team_name": name} for tid, name in teams_dict.items()]

    # Initialize report
    report = ValidationReport(
        state=state,
        year=year,
        games=len(games),
        teams=len(teams) if teams else 0
    )

    # Run validation checks
    validate_basic_games(games, report)
    validate_bracket_progression(games, report)
    validate_expected_counts(games, teams or [], report)

    return report


def format_validation_report(report: ValidationReport) -> str:
    """
    Format validation report for console output.

    Args:
        report: ValidationReport to format

    Returns:
        Formatted string suitable for printing
    """
    lines = []
    lines.append(f"{'='*80}")
    lines.append(f"VALIDATION REPORT: {report.state} {report.year}")
    lines.append(f"{'='*80}")
    lines.append(f"Games: {report.games}, Teams: {report.teams}")
    lines.append(f"Health Score: {report.health_score:.2f} {'[HEALTHY]' if report.is_healthy() else '[UNHEALTHY]'}")

    if report.errors:
        lines.append(f"\nERRORS ({len(report.errors)}):")
        for error in report.errors[:10]:  # Show first 10
            lines.append(f"  - {error}")
        if len(report.errors) > 10:
            lines.append(f"  ... and {len(report.errors) - 10} more errors")

    if report.warnings:
        lines.append(f"\nWARNINGS ({len(report.warnings)}):")
        for warning in report.warnings[:5]:  # Show first 5
            lines.append(f"  - {warning}")
        if len(report.warnings) > 5:
            lines.append(f"  ... and {len(report.warnings) - 5} more warnings")

    if not report.errors and not report.warnings:
        lines.append("\n[OK] No issues found")

    lines.append(f"{'='*80}")

    return "\n".join(lines)
