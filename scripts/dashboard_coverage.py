#!/usr/bin/env python3
"""
Coverage Dashboard - Visual State Coverage Analysis

Simple ASCII dashboard for understanding coverage gaps at a glance.

Enhancement 12.4: Coverage Dashboard

**Purpose**: Make coverage gaps instantly visible without reading raw numbers

**Usage**:
    # Run on college cohort
    python scripts/dashboard_coverage.py --cohort data/college_cohort_filtered.csv

    # Run on sample players
    python scripts/dashboard_coverage.py --limit 50

**Output**:
    - ASCII bar charts for coverage by state
    - Priority ranking (player_count × coverage_gap)
    - Specific recommendations per state
    - Export-ready gap analysis

Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.report_coverage import (
    load_players_from_cohort_csv,
    load_players_from_duckdb,
    compute_coverage_for_players,
)


def print_ascii_bar(
    label: str,
    value: float,
    max_value: float = 100.0,
    width: int = 40,
    fill_char: str = "#",
    empty_char: str = "."
) -> None:
    """
    Print an ASCII bar chart.

    NOTE: Changed from emoji chars (█, ░) to ASCII (#, .) for Windows console compatibility.

    Args:
        label: Label for the bar
        value: Value to visualize (0-100)
        max_value: Maximum value for scaling
        width: Width of bar in characters
        fill_char: Character for filled portion (default: #)
        empty_char: Character for empty portion (default: .)
    """
    pct = min(value / max_value, 1.0) if max_value > 0 else 0
    filled = int(pct * width)
    empty = width - filled

    bar = fill_char * filled + empty_char * empty
    print(f"{label:20} {bar} {value:.1f}%")


def print_state_coverage_dashboard(results: List[tuple]) -> Dict[str, Dict]:
    """
    Print visual dashboard of state-level coverage.

    Args:
        results: List of (player_info, flags, score) tuples from coverage measurement

    Returns:
        Dictionary of state metrics for further analysis
    """
    print(f"\n{'='*80}")
    print(f"{'STATE COVERAGE DASHBOARD':^80}")
    print(f"{'='*80}\n")

    # Aggregate by state
    state_data = defaultdict(lambda: {
        "players": [],
        "coverage_scores": [],
        "missing_maxpreps": 0,
        "missing_recruiting": 0,
        "missing_advanced_stats": 0,
    })

    for player_info, flags, score in results:
        state = player_info.get("state", "Unknown")
        if not state or state == "Unknown":
            continue

        state_data[state]["players"].append(player_info)
        state_data[state]["coverage_scores"].append(score.overall_score)

        if flags.missing_maxpreps_data:
            state_data[state]["missing_maxpreps"] += 1
        if flags.missing_247_profile:
            state_data[state]["missing_recruiting"] += 1
        if flags.missing_advanced_stats:
            state_data[state]["missing_advanced_stats"] += 1

    # Calculate metrics
    state_metrics = {}
    for state, data in state_data.items():
        player_count = len(data["players"])
        avg_coverage = sum(data["coverage_scores"]) / player_count if player_count > 0 else 0

        # Priority: players × gap
        priority_score = player_count * (100 - avg_coverage)

        state_metrics[state] = {
            "player_count": player_count,
            "avg_coverage": avg_coverage,
            "coverage_gap": 100 - avg_coverage,
            "priority_score": priority_score,
            "missing_maxpreps_pct": (data["missing_maxpreps"] / player_count * 100) if player_count > 0 else 0,
            "missing_recruiting_pct": (data["missing_recruiting"] / player_count * 100) if player_count > 0 else 0,
            "missing_advanced_stats_pct": (data["missing_advanced_stats"] / player_count * 100) if player_count > 0 else 0,
        }

    # Sort by priority score (descending)
    sorted_states = sorted(
        state_metrics.items(),
        key=lambda x: x[1]["priority_score"],
        reverse=True
    )

    # Print top 10 states by priority
    print(f"*** TOP 10 PRIORITY STATES (Player Count x Coverage Gap)\n")
    print(f"{'State':<6} {'Players':<8} {'Coverage':<10} {'Gap':<10} {'Priority':<12}")
    print(f"{'-'*6} {'-'*8} {'-'*10} {'-'*10} {'-'*12}")

    for i, (state, metrics) in enumerate(sorted_states[:10], 1):
        players = metrics["player_count"]
        coverage = metrics["avg_coverage"]
        gap = metrics["coverage_gap"]
        priority = metrics["priority_score"]

        # Priority level indicators (ASCII instead of emoji for Windows compatibility)
        if priority > 3000:
            priority_str = f"[HIGH] {priority:.0f}"
        elif priority > 1500:
            priority_str = f"[MED]  {priority:.0f}"
        else:
            priority_str = f"[LOW]  {priority:.0f}"

        print(f"{state:<6} {players:<8} {coverage:>6.1f}%   {gap:>6.1f}%   {priority_str}")

    print(f"\n{'='*80}\n")

    # Coverage distribution bars
    print(f"[DATA] COVERAGE DISTRIBUTION (Top 10 States)\n")

    for i, (state, metrics) in enumerate(sorted_states[:10], 1):
        coverage = metrics["avg_coverage"]
        players = metrics["player_count"]

        # Bar color based on coverage level (ASCII characters for Windows compatibility)
        if coverage >= 70:
            fill_char = "#"  # Green (was █)
        elif coverage >= 50:
            fill_char = "="  # Yellow (was ▓)
        else:
            fill_char = "-"  # Red (was ░)

        label = f"{i:2}. {state} ({players}p)"
        print_ascii_bar(label, coverage, 100.0, width=50, fill_char=fill_char, empty_char=".")

    print(f"\n{'='*80}\n")

    # Gap analysis
    print(f"[?] GAP ANALYSIS (Top 5 Priority States)\n")

    for i, (state, metrics) in enumerate(sorted_states[:5], 1):
        print(f"{i}. {state} - {metrics['player_count']} players, {metrics['avg_coverage']:.1f}% coverage")
        print(f"   Missing Breakdown:")
        print(f"     MaxPreps:      {metrics['missing_maxpreps_pct']:>5.0f}%")
        print(f"     Recruiting:    {metrics['missing_recruiting_pct']:>5.0f}%")
        print(f"     Advanced Stats:{metrics['missing_advanced_stats_pct']:>5.0f}%")

        # Recommendations
        recs = []
        if metrics['missing_maxpreps_pct'] > 50:
            recs.append("- Fix MaxPreps state normalization")
        if metrics['missing_recruiting_pct'] > 50:
            recs.append(f"- Import {state} recruiting CSV (247/ESPN)")
        if metrics['missing_advanced_stats_pct'] > 60:
            recs.append(f"- Implement {state} state datasource adapter")

        if recs:
            print(f"   *** Actions:")
            for rec in recs:
                print(f"      {rec}")
        print()

    print(f"{'='*80}\n")

    return state_metrics


def print_summary_stats(results: List[tuple]) -> None:
    """Print overall summary statistics."""

    total_players = len(results)

    # Calculate overall coverage
    coverage_scores = [score.overall_score for _, _, score in results]
    avg_coverage = sum(coverage_scores) / total_players if total_players > 0 else 0

    # Distribution
    excellent = sum(1 for _, _, s in results if s.coverage_level == "EXCELLENT")
    good = sum(1 for _, _, s in results if s.coverage_level == "GOOD")
    fair = sum(1 for _, _, s in results if s.coverage_level == "FAIR")
    poor = sum(1 for _, _, s in results if s.coverage_level == "POOR")

    print(f"\n{'='*80}")
    print(f"{'OVERALL SUMMARY':^80}")
    print(f"{'='*80}\n")

    print(f"Total Players:    {total_players}")
    print(f"Average Coverage: {avg_coverage:.1f}%")
    print()

    print(f"Distribution:")
    print_ascii_bar("  EXCELLENT (>=80%)", excellent / total_players * 100, 100, 40, "#", ".")
    print_ascii_bar("  GOOD (>=60%)", good / total_players * 100, 100, 40, "=", ".")
    print_ascii_bar("  FAIR (>=40%)", fair / total_players * 100, 100, 40, "-", ".")
    print_ascii_bar("  POOR (<40%)", poor / total_players * 100, 100, 40, ".", " ")

    print(f"\n{'='*80}\n")


async def main():
    """Main entry point for coverage dashboard."""

    parser = argparse.ArgumentParser(
        description="Visual coverage dashboard - see gaps at a glance"
    )
    parser.add_argument(
        "--cohort",
        type=str,
        default=None,
        help="Path to college cohort CSV"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max players to analyze (None = all)"
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export state gaps to CSV"
    )

    args = parser.parse_args()

    # Load players
    if args.cohort:
        print(f"[DATA] Loading college cohort: {args.cohort}\n")
        players = load_players_from_cohort_csv(Path(args.cohort), limit=args.limit)
        cohort_name = Path(args.cohort).name
    else:
        print(f"[DATA] Loading sample players from DuckDB\n")
        players = await load_players_from_duckdb(segment="All", limit=args.limit or 50)
        cohort_name = "Sample Players"

    if not players:
        print("[X] No players loaded. Exiting.")
        return

    # Compute coverage
    print(f"[...] Computing coverage for {len(players)} players...\n")
    results = await compute_coverage_for_players(players, verbose=False)

    # Print dashboard
    print(f"\n{'#'*80}")
    print(f"{'COVERAGE DASHBOARD':^80}")
    print(f"{cohort_name:^80}")
    print(f"{'#'*80}")

    # Summary stats
    print_summary_stats(results)

    # State-level dashboard
    state_metrics = print_state_coverage_dashboard(results)

    # Export if requested
    if args.export:
        export_path = Path(args.export)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        with open(export_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "state", "player_count", "avg_coverage", "coverage_gap",
                "priority_score", "missing_maxpreps_pct", "missing_recruiting_pct",
                "missing_advanced_stats_pct"
            ])
            writer.writeheader()

            for state, metrics in state_metrics.items():
                writer.writerow({
                    "state": state,
                    **metrics
                })

        print(f"[OK] State gaps exported to: {export_path}\n")

    # Final recommendations
    print(f"{'='*80}")
    print(f"NEXT STEPS")
    print(f"{'='*80}")
    print()
    print(f"1. Review top priority states above")
    print(f"2. For HIGH priority states ([HIGH]):")
    print(f"   - Add recruiting CSV: data/recruiting/{{state}}_rankings.csv")
    print(f"   - Consider state datasource: src/datasources/us/state/{{state}}_*.py")
    print(f"3. Re-run dashboard to measure improvement")
    print(f"4. Focus on top 5-10 states for 80/20 rule impact")
    print()
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
