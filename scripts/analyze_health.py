"""
State Adapter Health Analyzer

Quick diagnostic tool to categorize states by error type from health snapshot.
Helps prioritize fixing efforts by identifying "easy lane" states vs complex ones.

Usage:
    python scripts/analyze_health.py
    python scripts/analyze_health.py --health-file state_adapter_health.json

Outputs:
    - Lane A: HTTP_404 states (URL pattern issues - easy fixes)
    - Lane B: NO_GAMES states (parser issues - medium fixes)
    - Lane C: Complex states (JS/PDF/API - hard fixes)
    - Summary statistics
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def analyze_health(health_file: Path) -> Dict:
    """
    Analyze state adapter health and categorize by repair complexity.

    Returns dict with:
        - lanes: Dict of error categories with state lists
        - summary: Aggregate statistics
        - recommendations: Suggested next actions
    """
    if not health_file.exists():
        return {
            "error": f"Health file not found: {health_file}",
            "hint": "Run: .venv/Scripts/python.exe scripts/probe_state_adapter.py --all --year 2024"
        }

    data = json.loads(health_file.read_text())
    states = data.get("states", [])
    summary = data.get("summary", {})

    # Categorize states by status
    lanes = defaultdict(list)
    for state in states:
        status = state.get("status", "OTHER")
        state_code = state.get("state")
        adapter = state.get("adapter", "Unknown")
        games = state.get("games_found", 0)
        error = state.get("error_msg", "")[:60]

        lanes[status].append({
            "state": state_code,
            "adapter": adapter,
            "games": games,
            "error": error
        })

    # Calculate lane priorities
    lane_a = lanes.get("HTTP_404", [])  # Easy - URL pattern fixes
    lane_b = lanes.get("NO_GAMES", [])  # Medium - parser fixes
    lane_c = (
        lanes.get("SSL_ERROR", []) +
        lanes.get("HTTP_403", []) +
        lanes.get("NETWORK_ERROR", [])
    )  # Hard - infrastructure issues
    lane_complex = lanes.get("OTHER", [])  # Unknown - needs investigation

    ok_real_data = lanes.get("OK_REAL_DATA", [])

    # Generate recommendations
    recommendations = []
    if len(lane_a) > 0:
        recommendations.append(f"[A] Lane A (HTTP_404): {len(lane_a)} states - URL pattern fixes (highest ROI)")
    if len(lane_b) > 0:
        recommendations.append(f"[B] Lane B (NO_GAMES): {len(lane_b)} states - parser/selector fixes (medium ROI)")
    if len(lane_c) > 0:
        recommendations.append(f"[C] Lane C (Infrastructure): {len(lane_c)} states - SSL/auth/network issues (defer)")
    if len(lane_complex) > 0:
        recommendations.append(f"[?] Complex/Unknown: {len(lane_complex)} states - needs investigation (defer)")

    return {
        "lanes": {
            "lane_a_http_404": lane_a,
            "lane_b_no_games": lane_b,
            "lane_c_infrastructure": lane_c,
            "lane_complex_unknown": lane_complex,
            "ok_real_data": ok_real_data
        },
        "summary": {
            "total_states": len(states),
            "ok_real_data": len(ok_real_data),
            "needs_url_fix": len(lane_a),
            "needs_parser_fix": len(lane_b),
            "infrastructure_issues": len(lane_c),
            "unknown_complex": len(lane_complex),
            "coverage_pct": round(len(ok_real_data) / len(states) * 100, 1) if states else 0.0,
            "quick_win_potential": len(lane_a) + len(lane_b)  # States that can be fixed quickly
        },
        "recommendations": recommendations,
        "probe_metadata": {
            "generated_at": data.get("generated_at"),
            "probe_year": data.get("probe_year"),
            "total_games": summary.get("total_games", 0),
            "total_teams": summary.get("total_teams", 0)
        }
    }


def print_health_report(analysis: Dict) -> None:
    """Print formatted health analysis report."""
    if "error" in analysis:
        print(f"\n❌ Error: {analysis['error']}")
        if "hint" in analysis:
            print(f"💡 Hint: {analysis['hint']}")
        return

    lanes = analysis["lanes"]
    summary = analysis["summary"]
    metadata = analysis["probe_metadata"]

    print("\n" + "="*80)
    print("STATE ADAPTER HEALTH ANALYSIS")
    print("="*80)
    print(f"Generated: {metadata['generated_at']}")
    print(f"Probe Year: {metadata['probe_year']}")
    print(f"Total States: {summary['total_states']}")
    print(f"Coverage: {summary['ok_real_data']}/{summary['total_states']} states ({summary['coverage_pct']}%)")
    print(f"Games/Teams: {metadata['total_games']} games, {metadata['total_teams']} teams")
    print("="*80)

    # OK states
    ok_states = lanes["ok_real_data"]
    print(f"\n[OK] OK_REAL_DATA: {len(ok_states)} states")
    if ok_states:
        for s in ok_states:
            print(f"     {s['state']}: {s['games']} games")

    # Lane A - Easy fixes
    lane_a = lanes["lane_a_http_404"]
    print(f"\n[A] LANE A (HTTP_404 - URL Pattern Issues): {len(lane_a)} states")
    print("    Priority: HIGH (easy URL fixes -> quick wins)")
    if lane_a:
        for s in lane_a[:10]:  # Show first 10
            print(f"    {s['state']}: {s['adapter']:<30} Error: {s['error']}")
        if len(lane_a) > 10:
            print(f"    ... and {len(lane_a) - 10} more")

    # Lane B - Medium fixes
    lane_b = lanes["lane_b_no_games"]
    print(f"\n[B] LANE B (NO_GAMES - Parser/Selector Issues): {len(lane_b)} states")
    print("    Priority: MEDIUM (parser fixes -> moderate effort)")
    if lane_b:
        for s in lane_b[:10]:
            print(f"    {s['state']}: {s['adapter']:<30} Error: {s['error']}")
        if len(lane_b) > 10:
            print(f"    ... and {len(lane_b) - 10} more")

    # Lane C - Infrastructure
    lane_c = lanes["lane_c_infrastructure"]
    print(f"\n[C] LANE C (Infrastructure Issues): {len(lane_c)} states")
    print("    Priority: LOW (defer - SSL/auth/network issues)")
    if lane_c:
        for s in lane_c[:5]:
            print(f"    {s['state']}: {s['adapter']:<30} Error: {s['error']}")

    # Complex/Unknown
    lane_complex = lanes["lane_complex_unknown"]
    print(f"\n[?] COMPLEX/UNKNOWN: {len(lane_complex)} states")
    print("    Priority: LOW (defer - needs investigation)")
    if lane_complex:
        for s in lane_complex[:5]:
            print(f"    {s['state']}: {s['adapter']:<30} Error: {s['error']}")

    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print("="*80)
    for rec in analysis["recommendations"]:
        print(f"  {rec}")

    print(f"\n[>>] Quick Win Potential: {summary['quick_win_potential']} states (Lane A + Lane B)")
    print(f"[>>] Next Milestone: Fix {min(5, summary['quick_win_potential'])} Lane A states -> {summary['ok_real_data'] + min(5, len(lane_a))}/{summary['total_states']} coverage")
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze state adapter health from probe results"
    )
    parser.add_argument(
        "--health-file",
        default="state_adapter_health.json",
        help="Path to health JSON file (default: state_adapter_health.json)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted report"
    )

    args = parser.parse_args()

    analysis = analyze_health(Path(args.health_file))

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print_health_report(analysis)


if __name__ == "__main__":
    main()
