#!/usr/bin/env python3
"""
Pick First State - Helper for Step 4

Analyzes state gaps CSV and recommends which state to implement first.

Priority factors:
1. High player count (volume)
2. High coverage gap (impact)
3. Priority score = players × gap

Usage:
    python scripts/helpers/pick_first_state.py

Or with custom CSV:
    python scripts/helpers/pick_first_state.py --gaps data/state_gaps_baseline.csv

Author: Claude Code
Date: 2025-11-16
"""

import argparse
import csv
from pathlib import Path


def analyze_state_gaps(gaps_csv: Path) -> None:
    """
    Analyze state gaps CSV and recommend first state to implement.

    Args:
        gaps_csv: Path to state gaps CSV from dashboard
    """
    if not gaps_csv.exists():
        print(f"❌ State gaps CSV not found: {gaps_csv}")
        print()
        print("📝 Run baseline measurement first:")
        print("   bash scripts/helpers/run_coverage_baseline.sh")
        return

    # Load state data
    states = []
    with open(gaps_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            states.append({
                "state": row["state"],
                "player_count": int(row["player_count"]),
                "avg_coverage": float(row["avg_coverage"]),
                "coverage_gap": float(row["coverage_gap"]),
                "priority_score": float(row["priority_score"]),
                "missing_maxpreps_pct": float(row["missing_maxpreps_pct"]),
                "missing_recruiting_pct": float(row["missing_recruiting_pct"]),
                "missing_advanced_stats_pct": float(row["missing_advanced_stats_pct"]),
            })

    # Sort by priority score
    states.sort(key=lambda x: x["priority_score"], reverse=True)

    print(f"\n{'='*80}")
    print(f"{'STATE DATASOURCE RECOMMENDATION':^80}")
    print(f"{'='*80}\n")

    print("🎯 TOP 5 CANDIDATES FOR FIRST STATE DATASOURCE:\n")

    # Show top 5
    for i, state in enumerate(states[:5], 1):
        print(f"{i}. {state['state']} - Priority Score: {state['priority_score']:.0f}")
        print(f"   Players:      {state['player_count']}")
        print(f"   Coverage:     {state['avg_coverage']:.1f}%")
        print(f"   Gap:          {state['coverage_gap']:.1f}%")
        print(f"   Missing:")
        print(f"     MaxPreps:       {state['missing_maxpreps_pct']:.0f}%")
        print(f"     Recruiting:     {state['missing_recruiting_pct']:.0f}%")
        print(f"     Advanced Stats: {state['missing_advanced_stats_pct']:.0f}%")
        print()

    # Recommendation logic
    top_state = states[0]
    print(f"{'='*80}\n")
    print(f"🏆 RECOMMENDED FIRST STATE: {top_state['state']}\n")
    print(f"Why {top_state['state']}?")
    print(f"  - Highest priority score ({top_state['priority_score']:.0f})")
    print(f"  - {top_state['player_count']} players (high volume)")
    print(f"  - {top_state['coverage_gap']:.1f}% gap (high impact)")
    print()

    # Specific action items
    print("📝 ACTION PLAN:\n")

    # Check if recruiting or MaxPreps is the main issue
    if top_state["missing_recruiting_pct"] > 60:
        print("1. QUICK WIN: Import recruiting CSV first")
        print("   - Create data/recruiting/247_rankings.csv with your recruiting data")
        print("   - Or activate example: bash scripts/helpers/activate_recruiting.sh")
        print("   - Expected improvement: +20-30% for top-ranked players")
        print()
        print("2. THEN: Implement state datasource")
    else:
        print("1. Implement state-specific datasource:")

    print(f"   - Copy template: cp src/datasources/us/state/state_template.py \\")
    print(f"                       src/datasources/us/state/{top_state['state'].lower()}_*.py")
    print(f"   - Find {top_state['state']} HS athletics data source (state association, stats site)")
    print(f"   - Implement search_players() for {top_state['state']}")
    print(f"   - Wire into aggregator in src/services/aggregator.py")
    print()

    # State-specific hints
    state_hints = {
        "FL": "Florida FHSAA (fhsaa.org) or partner stats sites",
        "TX": "Texas UIL (uiltexas.org) or MaxPreps state pages",
        "CA": "California CIF (cifstate.org) or MaxPreps",
        "GA": "Georgia GHSA (ghsa.net) or partner sites",
        "NY": "New York state athletics or section sites",
        "IL": "Illinois IHSA (ihsa.org)",
        "NJ": "New Jersey NJSIAA (njsiaa.org)",
        "PA": "Pennsylvania PIAA (piaa.org)",
    }

    if top_state["state"] in state_hints:
        print(f"💡 {top_state['state']} HINT:")
        print(f"   {state_hints[top_state['state']]}")
        print()

    print(f"3. After implementation, re-measure coverage:")
    print(f"   python scripts/dashboard_coverage.py \\")
    print(f"     --cohort data/college_cohort_d1_2018_2020.csv \\")
    print(f"     --export data/state_gaps_after_{top_state['state'].lower()}.csv")
    print()
    print(f"4. Compare improvement:")
    print(f"   bash scripts/helpers/compare_coverage.sh \\")
    print(f"     data/state_gaps_baseline.csv \\")
    print(f"     data/state_gaps_after_{top_state['state'].lower()}.csv")
    print()

    print(f"{'='*80}\n")

    # Alternative: Focus on recruiting first
    print("🔄 ALTERNATIVE: Quick Win with Recruiting CSV\n")
    print("If implementing a state datasource seems too heavy right now:")
    print("1. Activate recruiting CSV first (easier, faster)")
    print("   bash scripts/helpers/activate_recruiting.sh")
    print()
    print("2. Re-measure coverage")
    print("   bash scripts/helpers/run_coverage_baseline.sh")
    print()
    print("3. THEN tackle the top state with better visibility")
    print()
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze state gaps and recommend first state to implement"
    )
    parser.add_argument(
        "--gaps",
        type=str,
        default="data/state_gaps_baseline.csv",
        help="Path to state gaps CSV"
    )

    args = parser.parse_args()
    gaps_csv = Path(args.gaps)

    analyze_state_gaps(gaps_csv)


if __name__ == "__main__":
    main()
