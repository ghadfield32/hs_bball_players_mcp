"""
Quick coverage summary from STATE_REGISTRY

Shows real-data verification status for all 35 states.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.state_registry import (
    STATE_REGISTRY,
    list_verified_states,
    get_coverage_summary,
)


def main():
    """Display coverage summary."""
    summary = get_coverage_summary()
    verified = list_verified_states()

    print("=" * 80)
    print("STATE ADAPTER REAL-DATA COVERAGE SUMMARY")
    print("=" * 80)
    print()
    print(f"Total States: {summary['total_states']}")
    print(f"Verified with Real Data: {summary['verified_states']} ({summary['coverage_pct']}%)")
    print(f"Pending Verification: {summary['unverified_states']}")
    print()
    print(f"States Needing URL Discovery: {summary['needs_url_discovery']}")
    print(f"States with SSL Issues: {summary['has_ssl_issues']}")
    print(f"States Pending Probe: {summary['pending_probe']}")
    print()

    if verified:
        print(f"[VERIFIED STATES] ({len(verified)}):")
        for abbrev in sorted(verified):
            cfg = STATE_REGISTRY[abbrev]
            seasons_str = ", ".join(str(y) for y in cfg.verified_seasons)
            print(f"  {abbrev}: {cfg.org} - Seasons: {seasons_str}")
    else:
        print("[WARNING] No states verified yet. Run probe_state_adapter.py --all --year 2024")

    print()
    print("=" * 80)
    print("Next: Run probe_state_adapter.py --all --year 2024 to verify more states")
    print("=" * 80)


if __name__ == "__main__":
    main()
