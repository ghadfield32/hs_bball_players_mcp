"""
State Adapter Coverage Report

Provides a comprehensive view of progress toward 50/50 US state coverage.

Usage:
    python scripts/state_coverage_report.py
    python scripts/state_coverage_report.py --format json
    python scripts/state_coverage_report.py --show-planned

This script:
- Reads sources.yaml to identify all US state adapters
- Calculates coverage statistics (% of 50 states, school counts)
- Groups states by phase (17, 19, 20, etc.)
- Shows planned vs active states
- Provides actionable next steps

Outputs:
- Console report with colored formatting
- Optional JSON output for automation
- Coverage percentage tracking
- School count estimates
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List
import argparse
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_sources_config() -> Dict:
    """Load and parse sources.yaml configuration."""
    config_path = project_root / "config" / "sources.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def extract_school_count(notes: str) -> int:
    """Extract school count estimate from notes field."""
    import re
    # Look for patterns like "400+ schools" or "~500 schools"
    match = re.search(r"(\d+)\+?\s*schools", notes, re.I)
    if match:
        return int(match.group(1))
    return 0


def extract_phase(notes: str) -> str:
    """Extract phase number from notes field."""
    import re
    match = re.search(r"Phase\s+(\d+)", notes, re.I)
    if match:
        return f"Phase {match.group(1)}"
    return "Unknown"


def generate_coverage_report(show_planned: bool = False, format: str = "text") -> None:
    """Generate comprehensive coverage report."""
    config = load_sources_config()

    # Filter for US state sources
    state_sources = [
        source for source in config.get("sources", [])
        if source.get("type") == "state" and source.get("region", "").startswith("US-")
    ]

    # Categorize by status
    active_states = []
    planned_states = []

    for source in state_sources:
        status = source.get("status", "unknown")
        region = source.get("region", "").replace("US-", "")

        state_info = {
            "id": source.get("id"),
            "name": source.get("name"),
            "full_name": source.get("full_name"),
            "state": region,
            "status": status,
            "adapter_class": source.get("adapter_class"),
            "schools": extract_school_count(source.get("notes", "")),
            "phase": extract_phase(source.get("notes", "")),
            "url": source.get("url", ""),
        }

        if status == "active":
            active_states.append(state_info)
        elif status == "planned":
            planned_states.append(state_info)

    # Sort by phase and state name
    active_states.sort(key=lambda x: (x["phase"], x["state"]))
    planned_states.sort(key=lambda x: x["state"])

    # Calculate totals
    total_active = len(active_states)
    total_planned = len(planned_states)
    total_schools_active = sum(s["schools"] for s in active_states)
    coverage_pct = (total_active / 50) * 100

    # Group active states by phase
    phases = defaultdict(list)
    for state in active_states:
        phases[state["phase"]].append(state)

    if format == "json":
        import json
        output = {
            "total_active": total_active,
            "total_planned": total_planned,
            "coverage_percentage": coverage_pct,
            "total_schools": total_schools_active,
            "active_states": active_states,
            "planned_states": planned_states if show_planned else [],
            "phases": {phase: states for phase, states in phases.items()},
        }
        print(json.dumps(output, indent=2))
        return

    # Text format output
    print("=" * 70)
    print("STATE ADAPTER COVERAGE REPORT".center(70))
    print("=" * 70)
    print()

    print(f"OVERALL PROGRESS: {total_active}/50 states ({coverage_pct:.1f}%)")
    print(f"Total Schools Covered: ~{total_schools_active:,}")
    print()

    print("=" * 70)
    print("ACTIVE STATES BY PHASE")
    print("=" * 70)

    for phase in sorted(phases.keys()):
        states = phases[phase]
        state_count = len(states)
        school_count = sum(s["schools"] for s in states)

        print(f"\n{phase} ({state_count} states, ~{school_count:,} schools):")
        print("-" * 70)

        for state in states:
            school_str = f"{state['schools']:>4}" if state['schools'] > 0 else "  ??"
            print(f"  [{state['state']}] {state['name']:<15} {school_str} schools | {state['adapter_class']}")

    if show_planned and planned_states:
        print()
        print("=" * 70)
        print(f"PLANNED STATES ({total_planned} states)")
        print("=" * 70)

        for state in planned_states:
            school_str = f"{state['schools']:>4}" if state['schools'] > 0 else "  ??"
            print(f"  [{state['state']}] {state['name']:<15} {school_str} schools")

    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)

    remaining = 50 - total_active
    print(f"1. {remaining} states remaining to reach 50/50 coverage")
    print(f"2. Estimated school coverage: ~{total_schools_active:,} / ~20,000 (US total)")

    if planned_states:
        print(f"3. {total_planned} states already planned (config entries exist)")
        print(f"4. Consider activating planned states first")

    # Suggest next priority states
    suggested_next = ["MI", "NJ", "AZ", "CO", "TN", "KY", "CT", "SC"]
    active_abbrevs = {s["state"] for s in active_states}
    next_batch = [s for s in suggested_next if s not in active_abbrevs][:5]

    if next_batch:
        print(f"5. Priority 3A batch suggestion: {', '.join(next_batch)}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="State adapter coverage report")
    parser.add_argument(
        "--show-planned",
        action="store_true",
        help="Show planned (not yet active) states"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)"
    )

    args = parser.parse_args()
    generate_coverage_report(show_planned=args.show_planned, format=args.format)


if __name__ == "__main__":
    main()
