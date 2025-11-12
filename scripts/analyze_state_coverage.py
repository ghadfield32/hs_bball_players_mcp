"""
US State Coverage Analysis Script

Analyzes current basketball stats coverage across all 50 US states + DC.
Identifies gaps and priorities for expansion.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# All US states + DC
ALL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
]

# State full names for reporting
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
}

# Basketball prominence ranking (based on population, programs, D1 colleges)
BASKETBALL_HOTBEDS = {
    "Critical": ["TX", "CA", "FL", "NY", "GA", "NC", "IN", "OH", "PA", "MI"],
    "High": ["IL", "VA", "TN", "MD", "NJ", "MA", "WA", "MO", "LA", "SC"],
    "Medium": ["KY", "AZ", "WI", "MN", "CO", "OR", "CT", "AL", "MS", "KS"],
    "Low": ["IA", "NV", "AR", "UT", "OK", "NM", "NE", "WV", "HI", "ID"],
    "Minimal": ["ME", "SD", "ND", "MT", "WY", "NH", "VT", "DE", "RI", "AK", "DC"]
}

def analyze_coverage():
    """Analyze state coverage from adapters."""

    # Import adapters
    from src.datasources.us.sblive import SBLiveDataSource
    from src.datasources.us.bound import BoundDataSource
    from src.datasources.us.rankone import RankOneDataSource
    from src.datasources.us.psal import PSALDataSource
    from src.datasources.us.mn_hub import MNHubDataSource
    from src.datasources.us.wsn import WSNDataSource
    from src.datasources.us.fhsaa import FHSAADataSource
    from src.datasources.us.hhsaa import HHSAADataSource

    # Build coverage map
    coverage: Dict[str, List[str]] = {}

    # Multi-state adapters
    for state in SBLiveDataSource.SUPPORTED_STATES:
        coverage.setdefault(state, []).append("SBLive")

    for state in BoundDataSource.SUPPORTED_STATES:
        coverage.setdefault(state, []).append("Bound")

    for state in RankOneDataSource.SUPPORTED_STATES:
        coverage.setdefault(state, []).append("RankOne")

    # Single-state adapters
    coverage.setdefault("NY", []).append("PSAL (NYC)")
    coverage.setdefault("MN", []).append("MN Hub")
    coverage.setdefault("WI", []).append("WSN")
    coverage.setdefault("FL", []).append("FHSAA")
    coverage.setdefault("HI", []).append("HHSAA")

    # Calculate statistics
    covered_states = set(coverage.keys())
    missing_states = set(ALL_STATES) - covered_states

    # Print detailed analysis
    print("="*70)
    print("US STATE COVERAGE ANALYSIS")
    print("="*70)
    print(f"\nTotal States: {len(ALL_STATES)}")
    print(f"Covered: {len(covered_states)} ({len(covered_states)/len(ALL_STATES)*100:.1f}%)")
    print(f"Missing: {len(missing_states)} ({len(missing_states)/len(ALL_STATES)*100:.1f}%)")

    # Covered states by adapter
    print(f"\n{'='*70}")
    print("COVERED STATES (ALPHABETICAL)")
    print(f"{'='*70}")

    for state in sorted(covered_states):
        adapters = ", ".join(coverage[state])
        print(f"  {state} - {STATE_NAMES[state]:20s} [{adapters}]")

    # Missing states by priority
    print(f"\n{'='*70}")
    print("MISSING STATES (BY BASKETBALL PRIORITY)")
    print(f"{'='*70}")

    for priority in ["Critical", "High", "Medium", "Low", "Minimal"]:
        priority_states = [s for s in BASKETBALL_HOTBEDS[priority] if s in missing_states]
        if priority_states:
            print(f"\n{priority} Priority ({len(priority_states)} states):")
            for state in sorted(priority_states):
                print(f"  {state} - {STATE_NAMES[state]}")

    # Coverage by basketball priority
    print(f"\n{'='*70}")
    print("COVERAGE BY BASKETBALL IMPORTANCE")
    print(f"{'='*70}")

    for priority in ["Critical", "High", "Medium", "Low", "Minimal"]:
        total = len(BASKETBALL_HOTBEDS[priority])
        covered = len([s for s in BASKETBALL_HOTBEDS[priority] if s in covered_states])
        pct = covered/total*100 if total > 0 else 0
        print(f"{priority:12s}: {covered:2d}/{total:2d} covered ({pct:5.1f}%)")

    # Multi-coverage states
    multi_coverage = {s: adapters for s, adapters in coverage.items() if len(adapters) > 1}
    if multi_coverage:
        print(f"\n{'='*70}")
        print(f"STATES WITH MULTIPLE ADAPTERS ({len(multi_coverage)})")
        print(f"{'='*70}")
        for state in sorted(multi_coverage.keys()):
            adapters = ", ".join(multi_coverage[state])
            print(f"  {state} - {STATE_NAMES[state]:20s} [{adapters}]")

    # Summary statistics
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")
    print(f"Total Adapters Analyzed: 8")
    print(f"Multi-state Adapters: 3 (SBLive, Bound, RankOne)")
    print(f"Single-state Adapters: 5 (PSAL, MN Hub, WSN, FHSAA, HHSAA)")
    print(f"States with Multiple Sources: {len(multi_coverage)}")
    print(f"Average Sources per Covered State: {sum(len(a) for a in coverage.values())/len(coverage):.2f}")

    # Critical gaps
    critical_missing = [s for s in BASKETBALL_HOTBEDS["Critical"] if s in missing_states]
    if critical_missing:
        print(f"\n{'='*70}")
        print("CRITICAL GAPS (TOP-10 BASKETBALL STATES MISSING)")
        print(f"{'='*70}")
        for state in sorted(critical_missing):
            print(f"  ❌ {state} - {STATE_NAMES[state]}")

    # Recommendations
    print(f"\n{'='*70}")
    print("EXPANSION RECOMMENDATIONS")
    print(f"{'='*70}")
    print("\n1. CRITICAL (Immediate Priority):")
    for state in ["GA", "PA", "MI", "NC"]:
        if state in missing_states:
            print(f"   - {STATE_NAMES[state]} ({state})")

    print("\n2. HIGH (Short-term Priority):")
    for state in ["VA", "MO", "LA", "SC", "NJ", "MA", "MD"]:
        if state in missing_states:
            print(f"   - {STATE_NAMES[state]} ({state})")

    print("\n3. RESEARCH NEEDED:")
    print("   - MaxPreps API/scraping (covers all states)")
    print("   - State association websites (GHSA, PIAA, MHSAA, etc.)")
    print("   - Regional platforms similar to SBLive/Bound")

    return covered_states, missing_states, coverage


if __name__ == "__main__":
    analyze_coverage()
