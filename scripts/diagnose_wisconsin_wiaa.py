#!/usr/bin/env python3
"""
Wisconsin WIAA Diagnostic Script

Validates Wisconsin WIAA tournament bracket data quality.

Checks:
- Self-games (team playing itself) - should be 0
- Duplicate games - should be 0
- Invalid scores (out of range) - should be 0
- Round distribution - "Unknown Round" should be < 20%
- Games per division/sectional
- Team count and uniqueness

Usage:
    python scripts/diagnose_wisconsin_wiaa.py --year 2025 --gender Boys
    python scripts/diagnose_wisconsin_wiaa.py --year 2024 --gender Girls --verbose
    python scripts/diagnose_wisconsin_wiaa.py --backfill 2015-2025
"""

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from src.models import Game


class WisconsinDiagnostics:
    """Diagnostic checker for Wisconsin WIAA data."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.datasource = WisconsinWiaaDataSource()

    async def diagnose_year(self, year: int, gender: str) -> Dict:
        """
        Diagnose data quality for a specific year and gender.

        Args:
            year: Tournament year (e.g., 2025)
            gender: "Boys" or "Girls"

        Returns:
            Dict with diagnostic results
        """
        print(f"\n{'='*80}")
        print(f"Diagnosing Wisconsin WIAA - {year} {gender} Basketball")
        print(f"{'='*80}\n")

        # Fetch games
        print(f"Fetching tournament brackets...")
        games = await self.datasource.get_tournament_brackets(
            year=year,
            gender=gender
        )

        print(f"✓ Fetched {len(games)} games\n")

        # Run diagnostics
        results = {
            "year": year,
            "gender": gender,
            "total_games": len(games),
            "issues": []
        }

        # Check 1: Self-games
        print("Check 1: Self-games (team vs itself)")
        print("-" * 40)
        self_games = [
            g for g in games
            if g.home_team_name.lower() == g.away_team_name.lower()
        ]
        results["self_games"] = len(self_games)

        if self_games:
            print(f"❌ FAIL: Found {len(self_games)} self-games")
            results["issues"].append(f"Found {len(self_games)} self-games")
            if self.verbose:
                for game in self_games[:5]:
                    print(f"   - {game.home_team_name} vs {game.away_team_name}")
        else:
            print(f"✓ PASS: No self-games found")

        # Check 2: Duplicate games
        print("\nCheck 2: Duplicate games")
        print("-" * 40)
        game_signatures: Set = set()
        duplicates: List[Game] = []

        for game in games:
            # Create signature (normalize team order)
            teams_sorted = tuple(sorted([game.home_team_name, game.away_team_name]))
            scores_sorted = tuple(sorted([game.home_score or 0, game.away_score or 0]))
            signature = (teams_sorted[0], teams_sorted[1], scores_sorted[0], scores_sorted[1])

            if signature in game_signatures:
                duplicates.append(game)
            else:
                game_signatures.add(signature)

        results["duplicate_games"] = len(duplicates)

        if duplicates:
            print(f"❌ FAIL: Found {len(duplicates)} duplicate games")
            results["issues"].append(f"Found {len(duplicates)} duplicate games")
            if self.verbose:
                for game in duplicates[:5]:
                    print(f"   - {game.home_team_name} vs {game.away_team_name}: {game.home_score}-{game.away_score}")
        else:
            print(f"✓ PASS: No duplicate games found")

        # Check 3: Invalid scores
        print("\nCheck 3: Invalid scores")
        print("-" * 40)
        invalid_scores = [
            g for g in games
            if (g.home_score is not None and (g.home_score < 0 or g.home_score > 200)) or
               (g.away_score is not None and (g.away_score < 0 or g.away_score > 200))
        ]
        results["invalid_scores"] = len(invalid_scores)

        if invalid_scores:
            print(f"❌ FAIL: Found {len(invalid_scores)} games with invalid scores")
            results["issues"].append(f"Found {len(invalid_scores)} invalid scores")
            if self.verbose:
                for game in invalid_scores[:5]:
                    print(f"   - {game.home_team_name} vs {game.away_team_name}: {game.home_score}-{game.away_score}")
        else:
            print(f"✓ PASS: All scores within valid range (0-200)")

        # Check 4: Round distribution
        print("\nCheck 4: Round distribution")
        print("-" * 40)
        round_counts = Counter(g.round for g in games)
        total = len(games)
        unknown_pct = (round_counts.get("Unknown Round", 0) / total * 100) if total > 0 else 0

        results["round_distribution"] = dict(round_counts)
        results["unknown_round_pct"] = unknown_pct

        for round_name, count in round_counts.most_common():
            pct = (count / total * 100) if total > 0 else 0
            print(f"   {round_name}: {count} ({pct:.1f}%)")

        if unknown_pct > 20:
            print(f"\n❌ WARN: {unknown_pct:.1f}% of games have 'Unknown Round' (target: <20%)")
            results["issues"].append(f"High unknown round percentage: {unknown_pct:.1f}%")
        else:
            print(f"\n✓ PASS: Unknown rounds at {unknown_pct:.1f}% (< 20%)")

        # Check 5: Division distribution
        print("\nCheck 5: Division distribution")
        print("-" * 40)
        division_counts = Counter(g.division for g in games if hasattr(g, 'division'))

        for div, count in sorted(division_counts.items()):
            print(f"   {div}: {count} games")

        results["division_distribution"] = dict(division_counts)

        # Check 6: Team statistics
        print("\nCheck 6: Team statistics")
        print("-" * 40)
        teams: Set[str] = set()

        for game in games:
            if game.home_team_name:
                teams.add(game.home_team_name)
            if game.away_team_name:
                teams.add(game.away_team_name)

        results["unique_teams"] = len(teams)
        print(f"   Unique teams: {len(teams)}")

        # Games per team
        team_game_counts = defaultdict(int)
        for game in games:
            if game.home_team_name:
                team_game_counts[game.home_team_name] += 1
            if game.away_team_name:
                team_game_counts[game.away_team_name] += 1

        if team_game_counts:
            avg_games = sum(team_game_counts.values()) / len(team_game_counts)
            min_games = min(team_game_counts.values())
            max_games = max(team_game_counts.values())

            print(f"   Games per team: avg={avg_games:.1f}, min={min_games}, max={max_games}")

            results["avg_games_per_team"] = avg_games
            results["min_games_per_team"] = min_games
            results["max_games_per_team"] = max_games

        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total games: {len(games)}")
        print(f"Unique teams: {len(teams)}")
        print(f"Issues found: {len(results['issues'])}")

        if results['issues']:
            print("\nIssues:")
            for issue in results['issues']:
                print(f"  - {issue}")
            results["status"] = "FAIL"
        else:
            print("\n✓ All checks passed!")
            results["status"] = "PASS"

        return results

    async def backfill_diagnosis(self, start_year: int, end_year: int):
        """
        Diagnose data quality for historical range.

        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
        """
        print(f"\n{'='*80}")
        print(f"Wisconsin WIAA Historical Backfill Diagnosis ({start_year}-{end_year})")
        print(f"{'='*80}\n")

        summary_results = []

        for year in range(start_year, end_year + 1):
            for gender in ["Boys", "Girls"]:
                try:
                    result = await self.diagnose_year(year, gender)
                    summary_results.append({
                        "year": year,
                        "gender": gender,
                        "games": result["total_games"],
                        "teams": result["unique_teams"],
                        "status": result["status"],
                        "issues": len(result["issues"])
                    })
                except Exception as e:
                    print(f"\n❌ Error for {year} {gender}: {e}\n")
                    summary_results.append({
                        "year": year,
                        "gender": gender,
                        "games": 0,
                        "teams": 0,
                        "status": "ERROR",
                        "issues": 1
                    })

        # Print summary table
        print(f"\n{'='*80}")
        print("BACKFILL SUMMARY")
        print(f"{'='*80}\n")
        print(f"{'Year':<6} {'Gender':<8} {'Games':<8} {'Teams':<8} {'Status':<10} {'Issues':<8}")
        print("-" * 80)

        for result in summary_results:
            print(
                f"{result['year']:<6} {result['gender']:<8} {result['games']:<8} "
                f"{result['teams']:<8} {result['status']:<10} {result['issues']:<8}"
            )

        # Overall statistics
        total_games = sum(r["games"] for r in summary_results)
        failed_count = sum(1 for r in summary_results if r["status"] == "FAIL")
        error_count = sum(1 for r in summary_results if r["status"] == "ERROR")

        print(f"\n{'='*80}")
        print(f"Total games across all years: {total_games}")
        print(f"Failed diagnostics: {failed_count}/{len(summary_results)}")
        print(f"Errors: {error_count}/{len(summary_results)}")
        print(f"{'='*80}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Diagnose Wisconsin WIAA tournament bracket data quality"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Tournament year (e.g., 2025)"
    )
    parser.add_argument(
        "--gender",
        choices=["Boys", "Girls"],
        help="Gender (Boys or Girls)"
    )
    parser.add_argument(
        "--backfill",
        type=str,
        help="Backfill range (e.g., '2015-2025')"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with example issues"
    )

    args = parser.parse_args()

    diagnostics = WisconsinDiagnostics(verbose=args.verbose)

    if args.backfill:
        # Parse backfill range
        start, end = map(int, args.backfill.split("-"))
        await diagnostics.backfill_diagnosis(start, end)
    elif args.year and args.gender:
        await diagnostics.diagnose_year(args.year, args.gender)
    else:
        # Default: diagnose current year Boys
        from datetime import datetime
        now = datetime.now()
        current_year = now.year + 1 if now.month >= 8 else now.year
        await diagnostics.diagnose_year(current_year, "Boys")


if __name__ == "__main__":
    asyncio.run(main())
