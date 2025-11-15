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
from pathlib import Path
from typing import List, Dict, Any
import argparse

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


async def main():
    """Main entry point for coverage dashboard."""
    parser = argparse.ArgumentParser(description="Measure real data coverage for forecasting")
    parser.add_argument(
        "--segment",
        choices=["US_HS", "Europe", "Canada", "All"],
        default="All",
        help="Player segment to analyze"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max number of players to analyze"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-player details"
    )

    args = parser.parse_args()

    # Load players from DuckDB
    players = await load_players_from_duckdb(
        segment=args.segment,
        limit=args.limit
    )

    if not players:
        print("⚠️  No players found. Ensure DuckDB is populated with player data.")
        print("   Run Enhancement 9 (DuckDB population) to load players.")
        return

    # Compute coverage scores
    results = await compute_coverage_for_players(
        players=players,
        verbose=args.verbose
    )

    # Print report
    print_coverage_report(results, segment=args.segment)


if __name__ == "__main__":
    asyncio.run(main())
