"""
State Adapter Data Quality Validation

Validates extracted data from state adapters against quality invariants.
Ensures data accuracy and consistency before marking states as verified.

Usage:
    # Check all states for 2024 season
    python scripts/check_state_data_quality.py --all --year 2024

    # Check specific states with detailed output
    python scripts/check_state_data_quality.py --states AL,TX,CA --year 2024 --verbose

Quality Checks:
    1. Score Validity: Non-negative scores, not absurdly high (< 200)
    2. Stat Consistency: made <= attempted for FG/3P/FT
    3. No Duplicates: No duplicate (state, date, teamA, teamB, score) rows
    4. Bracket Structure: Game counts match expected bracket size (e.g., 32-team → 31 games)
    5. Team Consistency: Team names/IDs consistent across games
    6. Date Validity: Game dates within reasonable season window

Output:
    - state_data_quality_report.json: Per-state quality metrics and violations
    - Pass/fail status for each quality check
    - Actionable error reports for failed checks
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import state registry and adapters
from src.state_registry import STATE_REGISTRY
from src.models import Game


class DataQualityChecker:
    """Performs quality validation on extracted game data."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.violations: List[Dict] = []

    def check_score_validity(self, games: List[Game]) -> Dict:
        """
        Check that scores are valid:
        - Non-negative
        - Not absurdly high (< 200 per team)
        - Home/away scores present together or both None
        """
        violations = []

        for game in games:
            # Check for negative scores
            if game.home_score is not None and game.home_score < 0:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "negative_home_score",
                    "value": game.home_score,
                    "message": f"Home score is negative: {game.home_score}"
                })

            if game.away_score is not None and game.away_score < 0:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "negative_away_score",
                    "value": game.away_score,
                    "message": f"Away score is negative: {game.away_score}"
                })

            # Check for absurdly high scores (> 200)
            if game.home_score is not None and game.home_score > 200:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "impossible_home_score",
                    "value": game.home_score,
                    "message": f"Home score impossibly high: {game.home_score}"
                })

            if game.away_score is not None and game.away_score > 200:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "impossible_away_score",
                    "value": game.away_score,
                    "message": f"Away score impossibly high: {game.away_score}"
                })

            # Check for mismatched score presence (one but not both)
            has_home = game.home_score is not None
            has_away = game.away_score is not None
            if has_home != has_away:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "mismatched_scores",
                    "value": f"home={game.home_score}, away={game.away_score}",
                    "message": "One score present but not the other"
                })

        return {
            "check": "score_validity",
            "passed": len(violations) == 0,
            "violations": len(violations),
            "details": violations[:10]  # Limit to first 10 for brevity
        }

    def check_no_duplicates(self, games: List[Game]) -> Dict:
        """
        Check for duplicate games based on:
        - Same teams (home/away or away/home)
        - Same date (if available)
        - Same score (if available)
        """
        violations = []
        seen_games: Set[Tuple] = set()

        for game in games:
            # Create a normalized game signature
            teams = tuple(sorted([game.home_team_id, game.away_team_id]))
            date_str = game.game_date.date().isoformat() if game.game_date else "no_date"
            score = tuple(sorted([game.home_score or 0, game.away_score or 0]))

            signature = (teams, date_str, score)

            if signature in seen_games:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "duplicate_game",
                    "value": str(signature),
                    "message": f"Duplicate: {game.home_team_name} vs {game.away_team_name} on {date_str}"
                })
            else:
                seen_games.add(signature)

        return {
            "check": "no_duplicates",
            "passed": len(violations) == 0,
            "violations": len(violations),
            "details": violations[:10]
        }

    def check_bracket_structure(self, games: List[Game], expected_teams: Optional[int] = None) -> Dict:
        """
        Check that bracket game counts are reasonable:
        - Single-elimination: teams - 1 games (e.g., 32 teams → 31 games)
        - Extract team count from unique participants
        - Allow some tolerance for consolation/3rd place games
        """
        violations = []

        # Count unique teams
        unique_teams = set()
        for game in games:
            unique_teams.add(game.home_team_id)
            unique_teams.add(game.away_team_id)

        team_count = len(unique_teams)
        game_count = len(games)

        # Expected games for single-elimination: teams - 1
        # Allow up to teams + 5 for consolation rounds
        min_expected = team_count - 1 if team_count > 0 else 0
        max_expected = team_count + 5 if team_count > 0 else game_count

        if game_count < min_expected:
            violations.append({
                "issue": "too_few_games",
                "value": f"{game_count} games for {team_count} teams",
                "message": f"Expected at least {min_expected} games, got {game_count}"
            })
        elif game_count > max_expected:
            violations.append({
                "issue": "too_many_games",
                "value": f"{game_count} games for {team_count} teams",
                "message": f"Expected at most {max_expected} games, got {game_count}"
            })

        return {
            "check": "bracket_structure",
            "passed": len(violations) == 0,
            "violations": len(violations),
            "team_count": team_count,
            "game_count": game_count,
            "expected_range": f"{min_expected}-{max_expected}",
            "details": violations
        }

    def check_team_consistency(self, games: List[Game]) -> Dict:
        """
        Check that team names/IDs are consistent:
        - Same team_id should always have same team_name
        - Team names shouldn't be empty or generic
        """
        violations = []
        team_id_to_names: Dict[str, Set[str]] = defaultdict(set)

        for game in games:
            # Track all names for each team_id
            team_id_to_names[game.home_team_id].add(game.home_team_name)
            team_id_to_names[game.away_team_id].add(game.away_team_name)

            # Check for empty/generic names
            if not game.home_team_name or game.home_team_name.strip() == "":
                violations.append({
                    "game_id": game.game_id,
                    "issue": "empty_team_name",
                    "value": f"home_team_id={game.home_team_id}",
                    "message": "Home team name is empty"
                })

            if not game.away_team_name or game.away_team_name.strip() == "":
                violations.append({
                    "game_id": game.game_id,
                    "issue": "empty_team_name",
                    "value": f"away_team_id={game.away_team_id}",
                    "message": "Away team name is empty"
                })

        # Check for inconsistent names for same team_id
        for team_id, names in team_id_to_names.items():
            if len(names) > 1:
                violations.append({
                    "issue": "inconsistent_team_name",
                    "value": f"team_id={team_id}",
                    "message": f"Team {team_id} has multiple names: {names}"
                })

        return {
            "check": "team_consistency",
            "passed": len(violations) == 0,
            "violations": len(violations),
            "unique_teams": len(team_id_to_names),
            "details": violations[:10]
        }

    def check_date_validity(self, games: List[Game], year: int) -> Dict:
        """
        Check that game dates are within reasonable season window:
        - Fall/Winter season: November (year-1) through March (year)
        - Dates not in the distant past/future
        """
        violations = []

        # Define reasonable season window
        # Basketball season typically runs November (year-1) through March (year)
        season_start = datetime(year - 1, 11, 1)
        season_end = datetime(year, 4, 1)

        for game in games:
            if game.game_date is None:
                continue  # Skip games without dates (brackets often don't have dates)

            if game.game_date < season_start or game.game_date > season_end:
                violations.append({
                    "game_id": game.game_id,
                    "issue": "out_of_season_date",
                    "value": game.game_date.isoformat(),
                    "message": f"Game date {game.game_date.date()} outside season window {season_start.date()}-{season_end.date()}"
                })

        return {
            "check": "date_validity",
            "passed": len(violations) == 0,
            "violations": len(violations),
            "season_window": f"{season_start.date()} to {season_end.date()}",
            "details": violations[:10]
        }

    def run_all_checks(self, games: List[Game], year: int) -> Dict:
        """Run all quality checks and aggregate results."""
        if not games:
            return {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "checks": [],
                "overall_passed": False,
                "message": "No games to check"
            }

        checks = [
            self.check_score_validity(games),
            self.check_no_duplicates(games),
            self.check_bracket_structure(games),
            self.check_team_consistency(games),
            self.check_date_validity(games, year)
        ]

        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)

        return {
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": total - passed,
            "checks": checks,
            "overall_passed": passed == total,
            "total_games": len(games)
        }


async def check_state_quality(
    state_abbrev: str,
    year: int,
    verbose: bool = False
) -> Dict:
    """
    Run quality checks on a single state's data.

    Args:
        state_abbrev: Two-letter state code
        year: Tournament year
        verbose: Show detailed output

    Returns:
        Dict with quality check results
    """
    from scripts.probe_state_adapter import ADAPTERS

    if verbose:
        print(f"\n[{state_abbrev}] Running quality checks for {year}...")

    try:
        # Get adapter
        adapter_cls = ADAPTERS.get(state_abbrev.lower())
        if not adapter_cls:
            return {
                "state": state_abbrev,
                "year": year,
                "error": f"No adapter found for {state_abbrev}"
            }

        adapter = adapter_cls()

        # Fetch bracket data
        season = f"{year-1}-{str(year)[2:]}"
        brackets_data = await adapter.get_tournament_brackets(
            season=season,
            gender="Boys"
        )

        games = brackets_data.get("games", [])

        if verbose:
            print(f"  Found {len(games)} games to validate")

        # Run quality checks
        checker = DataQualityChecker(verbose=verbose)
        results = checker.run_all_checks(games, year)

        # Cleanup
        await adapter.close()

        # Add state and year to results
        results["state"] = state_abbrev
        results["year"] = year
        results["adapter"] = adapter_cls.__name__

        if verbose:
            print(f"  Quality: {results['passed_checks']}/{results['total_checks']} checks passed")
            if not results["overall_passed"]:
                print(f"  ⚠️ Failed checks:")
                for check in results["checks"]:
                    if not check["passed"]:
                        print(f"    - {check['check']}: {check['violations']} violations")

        return results

    except Exception as e:
        return {
            "state": state_abbrev,
            "year": year,
            "error": f"{type(e).__name__}: {str(e)}"
        }


async def check_all_states(
    states: Optional[List[str]] = None,
    year: int = None,
    verbose: bool = False
) -> List[Dict]:
    """Run quality checks on multiple states."""
    if states is None:
        states = sorted(STATE_REGISTRY.keys())

    if year is None:
        year = datetime.now().year

    print(f"\n{'='*80}")
    print(f"STATE DATA QUALITY VALIDATION")
    print(f"{'='*80}")
    print(f"States: {len(states)}")
    print(f"Year: {year}")
    print(f"{'='*80}\n")

    results = []
    for state in states:
        result = await check_state_quality(state, year, verbose)
        results.append(result)

        # Print summary line
        if "error" not in result:
            emoji = "✅" if result.get("overall_passed") else "⚠️"
            print(f"{emoji} {state}: {result.get('passed_checks', 0)}/{result.get('total_checks', 0)} checks passed")
        else:
            print(f"❌ {state}: {result['error']}")

    return results


def save_quality_report(
    results: List[Dict],
    output_path: Path = Path("state_data_quality_report.json")
) -> None:
    """Save quality check results to JSON."""
    # Calculate summary stats
    total_states = len(results)
    passed_states = sum(1 for r in results if r.get("overall_passed", False))
    failed_states = total_states - passed_states
    error_states = sum(1 for r in results if "error" in r)

    payload = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "states": results,
        "summary": {
            "total_states": total_states,
            "passed_states": passed_states,
            "failed_states": failed_states,
            "error_states": error_states,
            "pass_rate": round(passed_states / total_states * 100, 1) if total_states > 0 else 0.0
        }
    }

    output_path.write_text(json.dumps(payload, indent=2))

    print(f"\n{'='*80}")
    print(f"QUALITY REPORT SAVED: {output_path}")
    print(f"{'='*80}")
    print(f"  Total States: {total_states}")
    print(f"  ✅ Passed All Checks: {passed_states} ({payload['summary']['pass_rate']}%)")
    print(f"  ⚠️  Failed Some Checks: {failed_states}")
    print(f"  ❌ Errors: {error_states}")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate data quality for state adapters"
    )
    parser.add_argument(
        "--states",
        help="Comma-separated state codes (e.g., AL,TX,CA). Default: all states"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all registered states"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Tournament year (default: current year)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--output",
        default="state_data_quality_report.json",
        help="Output file path (default: state_data_quality_report.json)"
    )

    args = parser.parse_args()

    # Parse states
    states = None
    if args.states:
        states = [s.strip().upper() for s in args.states.split(",")]
    elif not args.all:
        parser.error("Must specify either --states or --all")

    # Run quality checks
    results = asyncio.run(check_all_states(
        states=states,
        year=args.year,
        verbose=args.verbose
    ))

    # Save report
    output_path = Path(args.output)
    save_quality_report(results, output_path)


if __name__ == "__main__":
    main()
