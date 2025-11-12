"""
QA Checks - Data Invariant Validation

Validates data quality and consistency after backfills.
Catches common issues like duplicate UIDs, implausible stats, etc.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import duckdb

from ..utils.logger import get_logger

logger = get_logger(__name__)


def check_duplicate_game_uids(db_path: str | Path = "data/basketball_stats.db") -> list[str]:
    """
    Check for duplicate game UIDs in fact_game table.

    Args:
        db_path: Path to DuckDB database

    Returns:
        List of error messages (empty if no issues)
    """
    errors = []
    try:
        conn = duckdb.connect(str(db_path), read_only=True)

        # Check for duplicate game_uids
        result = conn.execute(
            """
            SELECT game_uid, COUNT(*) as cnt
            FROM fact_game
            GROUP BY game_uid
            HAVING cnt > 1
            ORDER BY cnt DESC
            LIMIT 10
            """
        ).fetchall()

        if result:
            errors.append(f"Found {len(result)} duplicate game UIDs (showing top 10):")
            for game_uid, count in result:
                errors.append(f"  - {game_uid}: {count} occurrences")

        conn.close()

    except Exception as e:
        errors.append(f"Error checking duplicate game UIDs: {e}")

    return errors


def check_duplicate_team_uids(db_path: str | Path = "data/basketball_stats.db") -> list[str]:
    """
    Check for duplicate team UIDs in dim_team table.

    Args:
        db_path: Path to DuckDB database

    Returns:
        List of error messages (empty if no issues)
    """
    errors = []
    try:
        conn = duckdb.connect(str(db_path), read_only=True)

        # Check for duplicate team_uids
        result = conn.execute(
            """
            SELECT team_uid, COUNT(*) as cnt
            FROM dim_team
            GROUP BY team_uid
            HAVING cnt > 1
            ORDER BY cnt DESC
            LIMIT 10
            """
        ).fetchall()

        if result:
            errors.append(f"Found {len(result)} duplicate team UIDs (showing top 10):")
            for team_uid, count in result:
                errors.append(f"  - {team_uid}: {count} occurrences")

        conn.close()

    except Exception as e:
        errors.append(f"Error checking duplicate team UIDs: {e}")

    return errors


def check_score_ranges(db_path: str | Path = "data/basketball_stats.db") -> list[str]:
    """
    Check for implausible scores in fact_box_score table.

    Args:
        db_path: Path to DuckDB database

    Returns:
        List of error messages (empty if no issues)
    """
    errors = []
    try:
        conn = duckdb.connect(str(db_path), read_only=True)

        # Check for negative stats
        result = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM fact_box_score
            WHERE points < 0 OR rebounds < 0 OR assists < 0
               OR steals < 0 OR blocks < 0 OR turnovers < 0
            """
        ).fetchone()

        if result and result[0] > 0:
            errors.append(f"Found {result[0]} records with negative stats")

        # Check for implausibly high stats (> 100 points per game)
        result = conn.execute(
            """
            SELECT player_name, points, game_uid
            FROM fact_box_score
            WHERE points > 100
            LIMIT 10
            """
        ).fetchall()

        if result:
            errors.append(f"Found {len(result)} records with > 100 points (showing 10):")
            for player_name, points, game_uid in result:
                errors.append(f"  - {player_name}: {points} pts in {game_uid}")

        conn.close()

    except Exception as e:
        errors.append(f"Error checking score ranges: {e}")

    return errors


def check_missing_game_dates(db_path: str | Path = "data/basketball_stats.db") -> list[str]:
    """
    Check for games with missing or invalid dates.

    Args:
        db_path: Path to DuckDB database

    Returns:
        List of error messages (empty if no issues)
    """
    errors = []
    try:
        conn = duckdb.connect(str(db_path), read_only=True)

        # Check for NULL dates
        result = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM fact_game
            WHERE date_iso IS NULL OR date_iso = ''
            """
        ).fetchone()

        if result and result[0] > 0:
            errors.append(f"Found {result[0]} games with missing dates")

        # Check for invalid date formats
        result = conn.execute(
            """
            SELECT game_uid, date_iso
            FROM fact_game
            WHERE LENGTH(date_iso) != 10 OR date_iso NOT LIKE '____-__-__'
            LIMIT 10
            """
        ).fetchall()

        if result:
            errors.append(f"Found {len(result)} games with invalid date format (showing 10):")
            for game_uid, date_iso in result:
                errors.append(f"  - {game_uid}: '{date_iso}'")

        conn.close()

    except Exception as e:
        errors.append(f"Error checking game dates: {e}")

    return errors


def check_season_consistency(db_path: str | Path = "data/basketball_stats.db") -> list[str]:
    """
    Check for season consistency issues.

    Args:
        db_path: Path to DuckDB database

    Returns:
        List of error messages (empty if no issues)
    """
    errors = []
    try:
        conn = duckdb.connect(str(db_path), read_only=True)

        # Check for games where date doesn't match season
        result = conn.execute(
            """
            SELECT game_uid, season, date_iso
            FROM fact_game
            WHERE season = 'unknown' OR season IS NULL
            LIMIT 10
            """
        ).fetchall()

        if result:
            errors.append(f"Found {len(result)} games with unknown/missing season (showing 10):")
            for game_uid, season, date_iso in result:
                errors.append(f"  - {game_uid}: season='{season}', date={date_iso}")

        conn.close()

    except Exception as e:
        errors.append(f"Error checking season consistency: {e}")

    return errors


def run_all_checks(db_path: str | Path = "data/basketball_stats.db") -> dict[str, list[str]]:
    """
    Run all QA checks and return results.

    Args:
        db_path: Path to DuckDB database

    Returns:
        Dictionary mapping check name to list of errors
    """
    checks = {
        "duplicate_game_uids": check_duplicate_game_uids,
        "duplicate_team_uids": check_duplicate_team_uids,
        "score_ranges": check_score_ranges,
        "missing_game_dates": check_missing_game_dates,
        "season_consistency": check_season_consistency,
    }

    results = {}
    for check_name, check_func in checks.items():
        logger.info(f"Running check: {check_name}")
        errors = check_func(db_path)
        results[check_name] = errors

    return results


def print_check_results(results: dict[str, list[str]]) -> None:
    """
    Print check results in a readable format.

    Args:
        results: Dictionary from run_all_checks()
    """
    print()
    print("=" * 70)
    print("QA CHECK RESULTS")
    print("=" * 70)
    print()

    total_errors = 0

    for check_name, errors in results.items():
        status = "✅" if not errors else "❌"
        print(f"{status} {check_name}")

        if errors:
            for error in errors:
                print(f"    {error}")
            print()
            total_errors += len(errors)

    print("-" * 70)
    print(f"Total checks: {len(results)}")
    print(f"Checks passed: {sum(1 for e in results.values() if not e)}")
    print(f"Checks failed: {sum(1 for e in results.values() if e)}")
    print(f"Total errors: {total_errors}")
    print()


def run_checks_cli(db_path: str | Path = "data/basketball_stats.db") -> int:
    """
    CLI entry point for running checks.

    Args:
        db_path: Path to DuckDB database

    Returns:
        Exit code (0 = all passed, 1 = some failed)
    """
    results = run_all_checks(db_path)
    print_check_results(results)

    # Return error code if any checks failed
    failed_count = sum(1 for errors in results.values() if errors)
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    import sys

    exit_code = run_checks_cli()
    sys.exit(exit_code)
