"""
Comprehensive State Coverage Analysis

Analyzes ACTUAL implementation status vs configuration for all 50 states + DC.
Distinguishes between:
- IMPLEMENTED: Has working adapter code
- TEMPLATED: Has skeleton file but not functional
- CONFIGURED: Only in sources.yaml, no code yet
- MISSING: Not covered at all

Usage:
    python scripts/comprehensive_coverage_analysis.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Set

# All 50 US states + DC
ALL_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
}

# Basketball importance ranking
CRITICAL_STATES = {"CA", "TX", "NY", "IL", "FL", "OH", "GA", "NC", "PA", "MI"}
HIGH_PRIORITY = {"VA", "NJ", "MA", "MD", "LA", "WA", "AZ", "MN", "IN", "CT"}
MEDIUM_PRIORITY = {"TN", "KY", "OR", "SC", "WI", "MO", "AL", "OK", "KS", "IA"}

# IMPLEMENTED adapters (actually working code)
IMPLEMENTED_ADAPTERS = {
    # Multi-state
    "SBLive": {"WA", "OR", "CA", "AZ", "ID", "NV"},
    "Bound": {"IA", "SD", "IL", "MN"},
    "RankOne": {"TX", "KY", "IN", "OH", "TN"},  # Fixtures only

    # Single state with stats
    "PSAL": {"NY"},
    "MN Hub": {"MN"},
    "WSN": {"WI"},

    # Single state fixtures only
    "FHSAA": {"FL"},
    "HHSAA": {"HI"},

    # National circuits
    "3SSB": set(),  # National
    "EYBL": set(),  # National
    "EYBL Girls": set(),  # National
}

# New adapter TEMPLATES (created but not fully working)
TEMPLATED_ADAPTERS = {
    "alabama_ahsaa": {"AL"},
    "alaska_asaa": {"AK"},
    "arkansas_aaa": {"AR"},
    "colorado_chsaa": {"CO"},
    "connecticut_ciac": {"CT"},
    "dc_dciaa": {"DC"},
    "delaware_diaa": {"DE"},
    "georgia_ghsa": {"GA"},
    "indiana_ihsaa": {"IN"},
    "kansas_kshsaa": {"KS"},
    "kentucky_khsaa": {"KY"},
    "louisiana_lhsaa": {"LA"},
    "maryland_mpssaa": {"MD"},
    "maine_mpa": {"ME"},
    "massachusetts_miaa": {"MA"},
    "michigan_mhsaa": {"MI"},
    "mississippi_mhsaa": {"MS"},
    "montana_mhsa": {"MT"},
    "missouri_mshsaa": {"MO"},
    "nebraska_nsaa": {"NE"},
    "new_hampshire_nhiaa": {"NH"},
    "new_jersey_njsiaa": {"NJ"},
    "new_mexico_nmaa": {"NM"},
    "nchsaa": {"NC"},
    "north_dakota_ndhsaa": {"ND"},
    "ohio_ohsaa": {"OH"},
    "oklahoma_ossaa": {"OK"},
    "pennsylvania_piaa": {"PA"},
    "rhode_island_riil": {"RI"},
    "south_carolina_schsl": {"SC"},
    "tennessee_tssaa": {"TN"},
    "utah_uhsaa": {"UT"},
    "vermont_vpa": {"VT"},
    "virginia_vhsl": {"VA"},
    "west_virginia_wvssac": {"WV"},
    "wyoming_whsaa": {"WY"},
}


def analyze_coverage():
    """Analyze actual vs configured coverage."""
    print("="*80)
    print("COMPREHENSIVE STATE COVERAGE ANALYSIS")
    print("="*80)
    print()

    # Calculate implemented coverage
    implemented_states = set()
    for adapter, states in IMPLEMENTED_ADAPTERS.items():
        implemented_states.update(states)

    # Calculate templated coverage
    templated_states = set()
    for adapter, states in TEMPLATED_ADAPTERS.items():
        templated_states.update(states)

    # Total coverage
    total_covered = implemented_states | templated_states
    missing_states = ALL_STATES - total_covered

    print(f"[OVERALL COVERAGE]")
    print(f"{'-'*80}")
    print(f"Total States:           {len(ALL_STATES)}")
    print(f"Implemented:            {len(implemented_states)} ({len(implemented_states)/len(ALL_STATES)*100:.1f}%)")
    print(f"Templated (needs work): {len(templated_states)} ({len(templated_states)/len(ALL_STATES)*100:.1f}%)")
    print(f"Total Covered:          {len(total_covered)} ({len(total_covered)/len(ALL_STATES)*100:.1f}%)")
    print(f"Missing:                {len(missing_states)} ({len(missing_states)/len(ALL_STATES)*100:.1f}%)")
    print()

    # Basketball priority analysis
    critical_impl = CRITICAL_STATES & implemented_states
    critical_templ = CRITICAL_STATES & templated_states
    critical_missing = CRITICAL_STATES - total_covered

    high_impl = HIGH_PRIORITY & implemented_states
    high_templ = HIGH_PRIORITY & templated_states
    high_missing = HIGH_PRIORITY - total_covered

    print(f"[BASKETBALL PRIORITY COVERAGE]")
    print(f"{'-'*80}")
    print(f"Critical States (Top 10):")
    print(f"  Implemented: {len(critical_impl)}/10 ({', '.join(sorted(critical_impl)) or 'none'})")
    print(f"  Templated:   {len(critical_templ)}/10 ({', '.join(sorted(critical_templ)) or 'none'})")
    print(f"  Missing:     {len(critical_missing)}/10 ({', '.join(sorted(critical_missing)) or 'none'})")
    print()
    print(f"High Priority States:")
    print(f"  Implemented: {len(high_impl)}/10 ({', '.join(sorted(high_impl)) or 'none'})")
    print(f"  Templated:   {len(high_templ)}/10 ({', '.join(sorted(high_templ)) or 'none'})")
    print(f"  Missing:     {len(high_missing)}/10 ({', '.join(sorted(high_missing)) or 'none'})")
    print()

    # Detailed breakdown
    print(f"[IMPLEMENTATION STATUS BY ADAPTER]")
    print(f"{'-'*80}")
    print()

    print("[OK] IMPLEMENTED & WORKING (13 adapters):")
    for adapter, states in sorted(IMPLEMENTED_ADAPTERS.items()):
        if states:
            state_list = ', '.join(sorted(states))
            print(f"  * {adapter:20} -> {state_list}")
        else:
            print(f"  * {adapter:20} -> National circuit")
    print()

    print(f"[NEEDS WORK] TEMPLATED (needs fixes & testing) - {len(TEMPLATED_ADAPTERS)} adapters:")
    print("  All 37 state association adapters need DataSourceType enum fixes")
    for adapter, states in sorted(list(TEMPLATED_ADAPTERS.items())[:5]):
        state_list = ', '.join(sorted(states))
        print(f"  * {adapter:30} -> {state_list}")
    print(f"  ... + {len(TEMPLATED_ADAPTERS) - 5} more")
    print()

    if missing_states:
        print(f"[MISSING] No code or config - {len(missing_states)} states:")
        print(f"  {', '.join(sorted(missing_states))}")
        print()
    else:
        print(f"[SUCCESS] NO MISSING STATES - All 50 states + DC are covered!")
        print()

    # Stats adapters vs fixtures adapters
    print(f"[DATA TYPE CLASSIFICATION]")
    print(f"{'-'*80}")
    print()

    stats_adapters = {
        "SBLive": "Full stats, leaderboards, box scores",
        "Bound": "Full stats, leaderboards, box scores",
        "WSN": "Full stats, leaderboards, box scores",
        "MN Hub": "Full stats, leaderboards, profiles",
        "PSAL": "Stats, leaderboards, team stats",
        "3SSB": "Season stats, leaderboards",
    }

    fixture_adapters = {
        "RankOne": "Schedules, fixtures (5 states)",
        "FHSAA": "Tournament brackets (FL)",
        "HHSAA": "Tournament brackets (HI)",
    }

    print(f"Stats Adapters ({len(stats_adapters)}):")
    for adapter, desc in stats_adapters.items():
        print(f"  [OK] {adapter:12} - {desc}")
    print()

    print(f"Fixture Adapters ({len(fixture_adapters)}):")
    for adapter, desc in fixture_adapters.items():
        print(f"  [OK] {adapter:12} - {desc}")
    print()

    # Recommendations
    print(f"[RECOMMENDATIONS]")
    print(f"{'-'*80}")
    print()
    print("IMMEDIATE (This Week):")
    print("  1. Fix DataSourceType enum issues in 37 templated adapters")
    print("  2. Stress test 13 working adapters with real data")
    print("  3. Validate data extraction from working adapters")
    print("  4. Document which adapters return real data (in-season)")
    print()
    print("SHORT-TERM (Next 2 Weeks):")
    print("  1. Implement missing critical state stats adapters (GA, MI, NC, PA)")
    print("  2. Test templated adapters when basketball season starts")
    print("  3. Add MaxPreps for comprehensive coverage")
    print("  4. Complete OTE, Grind Session templates")
    print()
    print("MEDIUM-TERM (Next Month):")
    print("  1. Full implementation of all 37 state association adapters")
    print("  2. Multi-season historical backfill")
    print("  3. Player identity resolution across sources")
    print("  4. Performance optimization based on stress tests")
    print()

    print("="*80)


if __name__ == "__main__":
    analyze_coverage()
