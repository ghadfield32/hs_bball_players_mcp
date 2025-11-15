#!/usr/bin/env python3
"""
Coverage Dashboard - Measure Real Data Coverage

Computes actual coverage scores from player data in DuckDB/Parquet.
Provides distribution by segment (US HS / Europe / Canada / College cohort).

Usage:
    python scripts/report_coverage.py [--segment US_HS|Europe|Canada|All] [--limit 100]

Author: Claude Code
Date: 2025-11-15
Methodology: 8-Step Coverage Measurement Plan (Step 1)
"""

import sys
import asyncio
import csv
from pathlib import Path
from typing import List, Dict, Any
import argparse
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.forecasting import ForecastingDataAggregator
from src.services.coverage_metrics import (
    CoverageFlags,
    CoverageScore,
    extract_coverage_flags_from_profile,
    compute_coverage_score,
    get_coverage_summary,
)
from src.services.duckdb_storage import get_duckdb_storage


async def load_players_from_duckdb(
    segment: str = "All",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Load player profiles from DuckDB for coverage measurement.

    Args:
        segment: Player segment filter ("US_HS" | "Europe" | "Canada" | "All")
        limit: Max number of players to load

    Returns:
        List of player records with basic info
    """
    storage = get_duckdb_storage()

    # TODO: Once DuckDB players table is fully populated, query it directly
    # For now, return empty list (will be populated by Enhancement 9)
    # Example query when ready:
    # query = """
    #     SELECT player_uid, full_name, grad_year, country, state
    #     FROM players
    #     WHERE country = ? OR ? = 'All'
    #     LIMIT ?
    # """

    print(f"⚠️  DuckDB players table not yet populated (Enhancement 9 pending)")
    print(f"   Using sample test data for demonstration...")

    # Sample test data for demonstration
    test_players = [
        {
            "player_name": "Cooper Flagg",
            "grad_year": 2025,
            "state": "ME",
            "country": "USA",
        },
        {
            "player_name": "AJ Dybantsa",
            "grad_year": 2026,
            "state": "UT",
            "country": "USA",
        },
        {
            "player_name": "Cameron Boozer",
            "grad_year": 2025,
            "state": "FL",
            "country": "USA",
        },
    ]

    return test_players[:limit]


def load_players_from_cohort_csv(
    cohort_csv_path: Path,
    limit: int = None
) -> List[Dict[str, Any]]:
    """
    Load player profiles from college cohort CSV for REAL coverage measurement.

    Enhancement 12.2: Closes the coverage loop by loading actual D1 college players.

    Expected CSV format (from build_college_cohort.py):
        player_name,hs_name,hs_state,grad_year,birth_date,college,college_years,drafted,nba_team

    Args:
        cohort_csv_path: Path to cohort CSV file
        limit: Max number of players to load (None = all)

    Returns:
        List of player records with basic info

    Example:
        >>> players = load_players_from_cohort_csv(Path("data/college_cohort_filtered.csv"))
        >>> print(f"Loaded {len(players)} D1 college players")
    """
    if not cohort_csv_path.exists():
        print(f"❌ Cohort CSV not found: {cohort_csv_path}")
        print(f"   Run: python scripts/build_college_cohort.py --source csv")
        return []

    players = []
    with open(cohort_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map cohort CSV columns to coverage format
            players.append({
                "player_name": row.get("player_name", ""),
                "grad_year": int(row["grad_year"]) if row.get("grad_year") else None,
                "state": row.get("hs_state", ""),  # hs_state from cohort
                "hs_name": row.get("hs_name", ""),
                "country": "USA",  # D1 cohort is US-only
                "college": row.get("college", ""),
                "drafted": row.get("drafted", "").lower() == "true",
            })

            # Stop at limit if specified
            if limit and len(players) >= limit:
                break

    print(f"✅ Loaded {len(players)} players from cohort CSV: {cohort_csv_path}")
    return players


async def compute_coverage_for_players(
    players: List[Dict[str, Any]],
    verbose: bool = False
) -> List[tuple]:
    """
    Compute coverage scores for a list of players.

    Args:
        players: List of player records from DuckDB
        verbose: Print per-player details

    Returns:
        List of (player_info, flags, score) tuples
    """
    aggregator = ForecastingDataAggregator()
    results = []

    print(f"\n{'='*80}")
    print(f"Computing coverage for {len(players)} players...")
    print(f"{'='*80}\n")

    for i, player_record in enumerate(players, 1):
        player_name = player_record.get("player_name")
        grad_year = player_record.get("grad_year")
        state = player_record.get("state")

        print(f"[{i}/{len(players)}] Processing: {player_name} ({grad_year}) - {state}...")

        try:
            # Get comprehensive profile
            profile = await aggregator.get_comprehensive_player_profile(
                player_name=player_name,
                grad_year=grad_year,
                state=state,
            )

            # Extract coverage flags
            flags = extract_coverage_flags_from_profile(profile)

            # Compute coverage score
            score = compute_coverage_score(flags)

            results.append((player_record, flags, score))

            if verbose:
                print(f"   Coverage: {score.overall_score:.1f}% ({score.coverage_level})")
                print(f"   Tier 1 (Critical): {score.tier1_score:.1f}%")
                print(f"   Tier 2 (Important): {score.tier2_score:.1f}%")
                print(f"   Tier 3 (Supplemental): {score.tier3_score:.1f}%")
                if score.missing_critical:
                    print(f"   Missing Critical: {', '.join(score.missing_critical[:3])}")
                print()

        except Exception as e:
            print(f"   ❌ Error: {e}")
            # Create zero coverage for failed players
            flags = CoverageFlags()
            score = compute_coverage_score(flags)
            results.append((player_record, flags, score))

    return results


def print_coverage_report(
    results: List[tuple],
    segment: str = "All"
):
    """
    Print formatted coverage report with statistics and distributions.

    Args:
        results: List of (player_info, flags, score) tuples
        segment: Player segment for report title
    """

    scores = [score for _, _, score in results]
    summary = get_coverage_summary(scores)

    print(f"\n{'#'*80}")
    print(f"# COVERAGE REPORT - {segment} Segment")
    print(f"# Date: 2025-11-15")
    print(f"{'#'*80}\n")

    # Overall Statistics
    print(f"{'='*80}")
    print(f"OVERALL STATISTICS")
    print(f"{'='*80}")
    print(f"Total Players Analyzed: {summary['total_players']}")
    print(f"Mean Coverage:          {summary['mean_coverage']:.1f}%")
    print(f"Median Coverage:        {summary['median_coverage']:.1f}%")
    print(f"Min Coverage:           {summary['min_coverage']:.1f}%")
    print(f"Max Coverage:           {summary['max_coverage']:.1f}%")
    print()

    # Distribution by Level
    print(f"{'='*80}")
    print(f"DISTRIBUTION BY COVERAGE LEVEL")
    print(f"{'='*80}")
    dist = summary['distribution']
    dist_pct = summary['distribution_pct']

    for level in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR']:
        count = dist[level]
        pct = dist_pct[level]
        bar = '█' * int(pct / 2)  # Scale to 50 chars max
        print(f"{level:12} ({pct:5.1f}%): {bar} ({count} players)")
    print()

    # Tier Averages
    print(f"{'='*80}")
    print(f"TIER AVERAGES")
    print(f"{'='*80}")
    tier_avgs = summary['tier_averages']
    print(f"Tier 1 (Critical Predictors):   {tier_avgs['tier1_critical']:.1f}%")
    print(f"Tier 2 (Important Features):    {tier_avgs['tier2_important']:.1f}%")
    print(f"Tier 3 (Supplemental Context):  {tier_avgs['tier3_supplemental']:.1f}%")
    print()

    # Top Missing Predictors
    print(f"{'='*80}")
    print(f"TOP MISSING CRITICAL PREDICTORS")
    print(f"{'='*80}")
    top_missing = summary['top_missing_predictors']

    if top_missing:
        for item in top_missing:
            pred = item['predictor']
            count = item['missing_count']
            pct = item['missing_pct']
            bar = '▓' * int(pct / 2)  # Scale to 50 chars max
            print(f"{pred:30} ({pct:5.1f}%): {bar} ({count} players)")
    else:
        print("None - all players have full critical predictor coverage!")
    print()

    # Detailed Player Breakdown (Top 5 and Bottom 5)
    print(f"{'='*80}")
    print(f"DETAILED PLAYER BREAKDOWN")
    print(f"{'='*80}")

    sorted_results = sorted(results, key=lambda x: x[2].overall_score, reverse=True)

    print("\n🏆 TOP 5 COVERAGE (Best Data Quality):\n")
    for i, (player_info, flags, score) in enumerate(sorted_results[:5], 1):
        name = player_info.get('player_name', 'Unknown')
        grad_year = player_info.get('grad_year', '?')
        print(f"{i}. {name} ({grad_year})")
        print(f"   Overall: {score.overall_score:.1f}% ({score.coverage_level})")
        print(f"   Recruiting: {score.recruiting_score:.1f}% | Efficiency: {score.efficiency_score:.1f}% | "
              f"Development: {score.development_score:.1f}%")
        print(f"   Data Sources: {flags.total_data_sources} | Seasons: {flags.total_stats_seasons}")
        print()

    print("⚠️  BOTTOM 5 COVERAGE (Need More Data):\n")
    for i, (player_info, flags, score) in enumerate(sorted_results[-5:], 1):
        name = player_info.get('player_name', 'Unknown')
        grad_year = player_info.get('grad_year', '?')
        print(f"{i}. {name} ({grad_year})")
        print(f"   Overall: {score.overall_score:.1f}% ({score.coverage_level})")
        print(f"   Missing Critical: {', '.join(score.missing_critical[:4]) if score.missing_critical else 'None'}")
        print(f"   Missing Important: {', '.join(score.missing_important[:4]) if score.missing_important else 'None'}")
        print()

    # Recommendations
    print(f"{'='*80}")
    print(f"RECOMMENDATIONS TO IMPROVE COVERAGE")
    print(f"{'='*80}")

    recommendations = []

    # Check recruiting coverage
    recruiting_missing = sum(1 for _, flags, _ in results if flags.missing_247_profile)
    if recruiting_missing > len(results) * 0.3:
        pct = recruiting_missing / len(results) * 100
        recommendations.append(
            f"1. Add ESPN/On3/Rivals recruiting sources ({recruiting_missing} players / {pct:.1f}% missing 247Sports)"
        )

    # Check MaxPreps coverage
    maxpreps_missing = sum(1 for _, flags, _ in results if flags.missing_maxpreps_data)
    if maxpreps_missing > len(results) * 0.3:
        pct = maxpreps_missing / len(results) * 100
        recommendations.append(
            f"2. Wire MaxPreps stats fully into forecasting ({maxpreps_missing} players / {pct:.1f}% missing state-level stats)"
        )

    # Check multi-season coverage
    multi_season_missing = sum(1 for _, flags, _ in results if flags.missing_multi_season_data)
    if multi_season_missing > len(results) * 0.5:
        pct = multi_season_missing / len(results) * 100
        recommendations.append(
            f"3. Add historical snapshots table to DuckDB ({multi_season_missing} players / {pct:.1f}% have only 1 season)"
        )

    # Check international coverage
    intl_missing = sum(1 for _, flags, _ in results
                      if flags.player_segment in ['Europe', 'Other'] and flags.missing_international_data)
    if intl_missing > 0:
        recommendations.append(
            f"4. Expand FIBA/ANGT/Eurobasket coverage ({intl_missing} international players missing context)"
        )

    if recommendations:
        for rec in recommendations:
            print(f"   {rec}")
    else:
        print("   ✅ Coverage is excellent! No critical gaps identified.")

    print()
    print(f"{'#'*80}\n")


def print_state_level_breakdown(
    results: List[tuple],
    output_csv: Path = None
):
    """
    Print state-level coverage breakdown with gap analysis.

    Enhancement 12.2: Aggregate coverage by hs_state to identify which states
    need more data sources (MaxPreps, state associations, etc.)

    Args:
        results: List of (player_info, flags, score) tuples
        output_csv: Optional path to export state gaps CSV

    Example output:
        STATE COVERAGE BREAKDOWN
        ========================
        State  Players  Avg Coverage  Missing MaxPreps  Missing Recruiting  Priority
        CA     150      68.5%         15%               25%                 Medium
        TX     120      42.3%         65%               45%                 HIGH
        FL     110      71.2%         12%               18%                 Low
    """
    print(f"\n{'='*80}")
    print(f"STATE-LEVEL COVERAGE BREAKDOWN")
    print(f"{'='*80}\n")

    # Aggregate by state
    state_data = defaultdict(lambda: {
        "players": [],
        "coverage_scores": [],
        "missing_maxpreps": 0,
        "missing_recruiting": 0,
        "missing_advanced_stats": 0,
        "missing_multi_season": 0,
    })

    for player_info, flags, score in results:
        state = player_info.get("state", "Unknown")
        if not state or state == "Unknown":
            continue

        state_data[state]["players"].append(player_info)
        state_data[state]["coverage_scores"].append(score.overall_score)

        # Count missing data types
        if flags.missing_maxpreps_data:
            state_data[state]["missing_maxpreps"] += 1
        if flags.missing_247_profile:
            state_data[state]["missing_recruiting"] += 1
        if flags.missing_advanced_stats:
            state_data[state]["missing_advanced_stats"] += 1
        if flags.missing_multi_season_data:
            state_data[state]["missing_multi_season"] += 1

    # Calculate state metrics
    state_metrics = []
    for state, data in state_data.items():
        player_count = len(data["players"])
        avg_coverage = sum(data["coverage_scores"]) / player_count if player_count > 0 else 0
        maxpreps_missing_pct = (data["missing_maxpreps"] / player_count * 100) if player_count > 0 else 0
        recruiting_missing_pct = (data["missing_recruiting"] / player_count * 100) if player_count > 0 else 0
        advanced_stats_missing_pct = (data["missing_advanced_stats"] / player_count * 100) if player_count > 0 else 0

        # Calculate priority score: (players * (100 - avg_coverage))
        # Higher score = more players with lower coverage = higher priority
        priority_score = player_count * (100 - avg_coverage)

        # Determine priority level
        if avg_coverage >= 70:
            priority = "Low"
        elif avg_coverage >= 50:
            priority = "Medium"
        else:
            priority = "HIGH"

        state_metrics.append({
            "state": state,
            "player_count": player_count,
            "avg_coverage": avg_coverage,
            "maxpreps_missing_pct": maxpreps_missing_pct,
            "recruiting_missing_pct": recruiting_missing_pct,
            "advanced_stats_missing_pct": advanced_stats_missing_pct,
            "priority_score": priority_score,
            "priority": priority,
        })

    # Sort by priority score (descending)
    state_metrics.sort(key=lambda x: x["priority_score"], reverse=True)

    # Print table header
    print(f"{'State':<6} {'Players':<8} {'Avg Cov':<10} {'MaxPreps':<12} {'Recruiting':<12} {'Adv Stats':<12} {'Priority':<10}")
    print(f"{'-'*6} {'-'*8} {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")

    # Print state rows
    for metric in state_metrics:
        state = metric["state"]
        players = metric["player_count"]
        avg_cov = f"{metric['avg_coverage']:.1f}%"
        maxpreps = f"{metric['maxpreps_missing_pct']:.0f}% miss"
        recruiting = f"{metric['recruiting_missing_pct']:.0f}% miss"
        adv_stats = f"{metric['advanced_stats_missing_pct']:.0f}% miss"
        priority = metric["priority"]

        print(f"{state:<6} {players:<8} {avg_cov:<10} {maxpreps:<12} {recruiting:<12} {adv_stats:<12} {priority:<10}")

    print()

    # Export to CSV if requested
    if output_csv:
        export_coverage_gaps_csv(state_metrics, output_csv)
        print(f"✅ State coverage gaps exported to: {output_csv}\n")

    # Print top 5 priority states
    print(f"{'='*80}")
    print(f"TOP 5 PRIORITY STATES (Most Players × Lowest Coverage)")
    print(f"{'='*80}")

    for i, metric in enumerate(state_metrics[:5], 1):
        state = metric["state"]
        players = metric["player_count"]
        avg_cov = metric["avg_coverage"]
        priority = metric["priority"]

        print(f"{i}. {state} - {players} players, {avg_cov:.1f}% avg coverage ({priority} priority)")
        print(f"   MaxPreps missing: {metric['maxpreps_missing_pct']:.0f}% | "
              f"Recruiting missing: {metric['recruiting_missing_pct']:.0f}% | "
              f"Advanced stats missing: {metric['advanced_stats_missing_pct']:.0f}%")

        # Recommendations for this state
        recs = []
        if metric['maxpreps_missing_pct'] > 50:
            recs.append("Fix MaxPreps state matching (normalize_state)")
        if metric['recruiting_missing_pct'] > 50:
            recs.append("Add CSV recruiting import for this state")
        if metric['advanced_stats_missing_pct'] > 60:
            recs.append("Consider state association adapter (UIL, CIF, etc.)")

        if recs:
            print(f"   Recommendations: {', '.join(recs)}")
        print()

    print(f"{'='*80}\n")


def export_coverage_gaps_csv(
    state_metrics: List[Dict],
    output_csv: Path
):
    """
    Export state coverage gaps to CSV for further analysis.

    Enhancement 12.2: Creates CSV file with state-level gaps for prioritization.

    Args:
        state_metrics: List of state metric dicts
        output_csv: Path to output CSV file

    Output CSV columns:
        state, player_count, avg_coverage, maxpreps_missing_pct,
        recruiting_missing_pct, advanced_stats_missing_pct,
        priority_score, priority
    """
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with open(output_csv, 'w', newline='') as f:
        fieldnames = [
            "state", "player_count", "avg_coverage",
            "maxpreps_missing_pct", "recruiting_missing_pct",
            "advanced_stats_missing_pct",
            "priority_score", "priority"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(state_metrics)

    print(f"📊 State coverage gaps exported to: {output_csv}")


async def main():
    """
    Main entry point for coverage dashboard.

    Enhancement 12.2: Added --cohort argument to load from college cohort CSV
    and --state-gaps to export state-level gap analysis.
    """
    parser = argparse.ArgumentParser(description="Measure real data coverage for forecasting")
    parser.add_argument(
        "--segment",
        choices=["US_HS", "Europe", "Canada", "All"],
        default="All",
        help="Player segment to analyze (only used without --cohort)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of players to analyze (None = all)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-player details"
    )
    parser.add_argument(
        "--cohort",
        type=str,
        default=None,
        help="Path to college cohort CSV (from build_college_cohort.py)"
    )
    parser.add_argument(
        "--state-gaps",
        type=str,
        default=None,
        help="Export state coverage gaps to CSV file"
    )

    args = parser.parse_args()

    # Load players: either from cohort CSV or DuckDB
    if args.cohort:
        # Enhancement 12.2: Load from college cohort CSV for REAL coverage measurement
        print(f"📊 Loading players from cohort CSV: {args.cohort}")
        cohort_path = Path(args.cohort)
        players = load_players_from_cohort_csv(cohort_path, limit=args.limit)
        segment_name = f"College Cohort ({cohort_path.name})"
    else:
        # Original: Load from DuckDB
        print(f"📊 Loading players from DuckDB (segment: {args.segment})")
        players = await load_players_from_duckdb(
            segment=args.segment,
            limit=args.limit or 100
        )
        segment_name = args.segment

    if not players:
        print("⚠️  No players found.")
        if args.cohort:
            print(f"   Cohort CSV not found or empty: {args.cohort}")
            print("   Run: python scripts/build_college_cohort.py --source csv")
        else:
            print("   Ensure DuckDB is populated with player data.")
        return

    # Compute coverage scores
    results = await compute_coverage_for_players(
        players=players,
        verbose=args.verbose
    )

    # Print standard coverage report
    print_coverage_report(results, segment=segment_name)

    # Enhancement 12.2: Print state-level breakdown if cohort mode
    if args.cohort or len(players) > 20:  # Only for cohorts or large samples
        state_gaps_path = Path(args.state_gaps) if args.state_gaps else None
        print_state_level_breakdown(results, output_csv=state_gaps_path)


if __name__ == "__main__":
    asyncio.run(main())
