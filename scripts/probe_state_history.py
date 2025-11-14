"""
State Adapter Multi-Year Historical Probe

Tests state adapters across multiple years to build historical coverage matrix.
Generates state_adapter_coverage.json showing year×state grid of data availability.

Usage:
    # Probe all states for last 5 years (2020-2024)
    python scripts/probe_state_history.py --years 2020-2024

    # Probe specific states for historical window
    python scripts/probe_state_history.py --states AL,TX,CA --years 2013-2024

    # Probe single state with verbose output
    python scripts/probe_state_history.py --states OH --years 2022-2024 --verbose

Output:
    - state_adapter_coverage.json: Year×state matrix with status for each cell
    - Summary statistics per state and per year
    - Coverage gap analysis for backfill prioritization
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import state registry for adapter access
from src.state_registry import STATE_REGISTRY

# Import probe logic from existing probe script
# We'll reuse the probe_adapter and classify_probe_result functions
from scripts.probe_state_adapter import probe_adapter, classify_probe_result


async def probe_state_year(
    state_abbrev: str,
    year: int,
    verbose: bool = False
) -> Dict:
    """
    Probe a single state for a single year.

    Args:
        state_abbrev: Two-letter state code (e.g., "AL", "TX")
        year: Tournament year (e.g., 2024)
        verbose: Show detailed output

    Returns:
        Dict with status, games_found, teams_found, error_msg
    """
    if verbose:
        print(f"  Probing {state_abbrev} for {year}...")

    result = await probe_adapter(
        state_code=state_abbrev.lower(),
        year=year,
        verbose=verbose
    )

    return {
        "state": state_abbrev,
        "year": year,
        "status": result.get("status", "OTHER"),
        "games_found": result.get("games_found", 0),
        "teams_found": result.get("teams_found", 0),
        "error_msg": result.get("error_msg", "")
    }


async def probe_historical_coverage(
    states: Optional[List[str]] = None,
    year_range: Optional[tuple] = None,
    verbose: bool = False
) -> Dict:
    """
    Probe multiple states across multiple years to build coverage matrix.

    Args:
        states: List of state abbreviations (None = all states)
        year_range: Tuple of (start_year, end_year) inclusive
        verbose: Show detailed output

    Returns:
        Dict with coverage matrix, summary stats, gap analysis
    """
    # Default to all registered states
    if states is None:
        states = sorted(STATE_REGISTRY.keys())

    # Default to modern era (last 5 years)
    if year_range is None:
        current_year = datetime.now().year
        year_range = (current_year - 4, current_year)

    start_year, end_year = year_range
    years = list(range(start_year, end_year + 1))

    print(f"\n{'='*80}")
    print(f"HISTORICAL COVERAGE PROBE")
    print(f"{'='*80}")
    print(f"States: {len(states)} ({', '.join(states[:10])}{'...' if len(states) > 10 else ''})")
    print(f"Years: {len(years)} ({start_year}-{end_year})")
    print(f"Total probes: {len(states) * len(years)}")
    print(f"{'='*80}\n")

    # Build coverage matrix: state → year → status
    coverage: Dict[str, Dict[int, str]] = defaultdict(dict)
    all_results: List[Dict] = []

    # Probe each state×year combination
    for state in states:
        print(f"\n[{state}] Probing {len(years)} years...")
        for year in years:
            try:
                result = await probe_state_year(state, year, verbose=verbose)
                coverage[state][year] = result["status"]
                all_results.append(result)

                # Print inline status
                status_emoji = "✅" if result["status"] == "OK_REAL_DATA" else "⚠️" if result["status"] == "NO_GAMES" else "❌"
                print(f"  {status_emoji} {year}: {result['status']:<15} ({result['games_found']} games)")

            except Exception as e:
                print(f"  ❌ {year}: ERROR - {str(e)[:60]}")
                coverage[state][year] = "ERROR"
                all_results.append({
                    "state": state,
                    "year": year,
                    "status": "ERROR",
                    "games_found": 0,
                    "teams_found": 0,
                    "error_msg": str(e)
                })

    # Calculate summary statistics
    summary = calculate_coverage_summary(coverage, years, states)

    # Identify coverage gaps for backfill prioritization
    gaps = identify_coverage_gaps(coverage, years, states)

    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "years": years,
        "states": {state: coverage[state] for state in states},
        "summary": summary,
        "gaps": gaps,
        "raw_results": all_results
    }


def calculate_coverage_summary(
    coverage: Dict[str, Dict[int, str]],
    years: List[int],
    states: List[str]
) -> Dict:
    """Calculate summary statistics for coverage matrix."""
    total_cells = len(states) * len(years)
    ok_real_data = sum(
        1 for state in states for year in years
        if coverage[state].get(year) == "OK_REAL_DATA"
    )
    no_games = sum(
        1 for state in states for year in years
        if coverage[state].get(year) == "NO_GAMES"
    )
    errors = sum(
        1 for state in states for year in years
        if coverage[state].get(year) not in ["OK_REAL_DATA", "NO_GAMES"]
    )

    # Per-state summary
    states_with_any_data = sum(
        1 for state in states
        if any(coverage[state].get(year) == "OK_REAL_DATA" for year in years)
    )

    # Per-year summary
    year_coverage = {
        year: sum(
            1 for state in states
            if coverage[state].get(year) == "OK_REAL_DATA"
        )
        for year in years
    }

    return {
        "total_cells": total_cells,
        "ok_real_data": ok_real_data,
        "no_games": no_games,
        "errors": errors,
        "coverage_pct": round(ok_real_data / total_cells * 100, 1) if total_cells > 0 else 0.0,
        "states_with_data": states_with_any_data,
        "states_without_data": len(states) - states_with_any_data,
        "year_coverage": year_coverage
    }


def identify_coverage_gaps(
    coverage: Dict[str, Dict[int, str]],
    years: List[int],
    states: List[str]
) -> Dict:
    """Identify coverage gaps for backfill prioritization."""
    # States with partial coverage (some years work, some don't)
    partial_coverage_states = []
    for state in states:
        has_some_data = any(coverage[state].get(year) == "OK_REAL_DATA" for year in years)
        has_some_gaps = any(coverage[state].get(year) != "OK_REAL_DATA" for year in years)
        if has_some_data and has_some_gaps:
            partial_coverage_states.append({
                "state": state,
                "years_ok": sum(1 for year in years if coverage[state].get(year) == "OK_REAL_DATA"),
                "years_missing": sum(1 for year in years if coverage[state].get(year) != "OK_REAL_DATA")
            })

    # States with no data at all
    no_data_states = [
        state for state in states
        if all(coverage[state].get(year) != "OK_REAL_DATA" for year in years)
    ]

    # Years with poor coverage
    poor_coverage_years = [
        {
            "year": year,
            "states_ok": sum(1 for state in states if coverage[state].get(year) == "OK_REAL_DATA"),
            "states_missing": sum(1 for state in states if coverage[state].get(year) != "OK_REAL_DATA")
        }
        for year in years
        if sum(1 for state in states if coverage[state].get(year) == "OK_REAL_DATA") < len(states) * 0.5
    ]

    return {
        "partial_coverage_states": partial_coverage_states,
        "no_data_states": no_data_states,
        "poor_coverage_years": poor_coverage_years
    }


def save_coverage_matrix(
    coverage_data: Dict,
    output_path: Path = Path("state_adapter_coverage.json")
) -> None:
    """Save coverage matrix to JSON file."""
    output_path.write_text(json.dumps(coverage_data, indent=2))

    summary = coverage_data["summary"]
    print(f"\n{'='*80}")
    print(f"COVERAGE MATRIX SAVED: {output_path}")
    print(f"{'='*80}")
    print(f"  Total Cells: {summary['total_cells']}")
    print(f"  ✅ OK_REAL_DATA: {summary['ok_real_data']} ({summary['coverage_pct']}%)")
    print(f"  ⚠️  NO_GAMES: {summary['no_games']}")
    print(f"  ❌ ERRORS: {summary['errors']}")
    print(f"\n  States with Data: {summary['states_with_data']}/{len(coverage_data['states'])}")
    print(f"  States without Data: {summary['states_without_data']}")

    # Print year coverage breakdown
    print(f"\n  Year-by-Year Coverage:")
    for year, count in sorted(coverage_data["summary"]["year_coverage"].items()):
        pct = round(count / len(coverage_data["states"]) * 100, 1) if len(coverage_data["states"]) > 0 else 0.0
        print(f"    {year}: {count}/{len(coverage_data['states'])} states ({pct}%)")

    # Print gap analysis
    gaps = coverage_data["gaps"]
    if gaps["no_data_states"]:
        print(f"\n  ⚠️  States with NO data: {len(gaps['no_data_states'])}")
        print(f"    {', '.join(gaps['no_data_states'][:10])}{'...' if len(gaps['no_data_states']) > 10 else ''}")

    if gaps["partial_coverage_states"]:
        print(f"\n  📊 States with PARTIAL coverage: {len(gaps['partial_coverage_states'])}")
        for item in gaps["partial_coverage_states"][:5]:
            print(f"    {item['state']}: {item['years_ok']}/{item['years_ok'] + item['years_missing']} years")

    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Probe state adapters across multiple years for historical coverage"
    )
    parser.add_argument(
        "--states",
        help="Comma-separated state codes (e.g., AL,TX,CA). Default: all states"
    )
    parser.add_argument(
        "--years",
        help="Year range in format 'START-END' (e.g., 2020-2024). Default: last 5 years"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--output",
        default="state_adapter_coverage.json",
        help="Output file path (default: state_adapter_coverage.json)"
    )

    args = parser.parse_args()

    # Parse states
    states = None
    if args.states:
        states = [s.strip().upper() for s in args.states.split(",")]

    # Parse years
    year_range = None
    if args.years:
        try:
            start, end = args.years.split("-")
            year_range = (int(start), int(end))
        except ValueError:
            print(f"Error: Invalid year range format. Use 'START-END' (e.g., 2020-2024)")
            sys.exit(1)

    # Run historical probe
    coverage_data = asyncio.run(probe_historical_coverage(
        states=states,
        year_range=year_range,
        verbose=args.verbose
    ))

    # Save results
    output_path = Path(args.output)
    save_coverage_matrix(coverage_data, output_path)


if __name__ == "__main__":
    main()
