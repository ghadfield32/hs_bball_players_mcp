"""
Batch State Probe - Fast Subset Testing

Probes multiple states efficiently without full --all timeout issues.
Ideal for testing small clusters of states during development/fixing.

Usage:
    # Test a few specific states
    python scripts/probe_batch.py --states al tx az in ga --year 2024

    # Test with verbose output
    python scripts/probe_batch.py --states al tx --year 2024 --verbose

    # Save results to custom file
    python scripts/probe_batch.py --states al tx az --year 2024 --output batch_results.json

Output:
    - Console summary with status icons ([OK], [XX], [NO])
    - Optional JSON file with detailed results
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.probe_state_adapter import probe_adapter, classify_probe_result


async def probe_batch(
    states: List[str],
    year: int,
    verbose: bool = False,
    dump_html: bool = False
) -> Dict[str, Dict]:
    """
    Probe multiple states in sequence.

    Args:
        states: List of state codes (e.g., ["al", "tx", "az"])
        year: Tournament year
        verbose: Show detailed output per state
        dump_html: Save fetched HTML to data/debug/html/ for inspection

    Returns:
        Dict mapping state code to probe result
    """
    results = {}

    print(f"\n{'='*80}")
    print(f"BATCH PROBE: {len(states)} states for {year}")
    print(f"{'='*80}\n")

    for state in states:
        state_lower = state.lower()

        if verbose:
            print(f"\n[{state.upper()}] Probing...")

        try:
            result = await probe_adapter(
                state_lower,
                year=year,
                verbose=verbose,
                dump_html=dump_html
            )
            results[state.upper()] = result

            # Print summary line
            status_icon = "[OK]" if result["status"] == "OK_REAL_DATA" else "[NO]" if result["status"] == "NO_GAMES" else "[XX]"
            status_label = result["status"]
            games = result["games_found"]
            teams = result["teams_found"]

            print(f"{status_icon} {state.upper():<3} {status_label:<15} Games: {games:<4} Teams: {teams:<4}")

            if result["status"] != "OK_REAL_DATA" and result.get("error_msg"):
                error_short = result["error_msg"][:60]
                print(f"     -> {error_short}")

        except Exception as e:
            results[state.upper()] = {
                "state": state.upper(),
                "success": False,
                "status": "OTHER",
                "games_found": 0,
                "teams_found": 0,
                "error_msg": f"{type(e).__name__}: {str(e)}"
            }
            print(f"[XX] {state.upper():<3} ERROR: {str(e)[:60]}")

    # Print summary
    total = len(results)
    ok_count = sum(1 for r in results.values() if r["status"] == "OK_REAL_DATA")
    no_games = sum(1 for r in results.values() if r["status"] == "NO_GAMES")
    http_404 = sum(1 for r in results.values() if r["status"] == "HTTP_404")
    other = total - ok_count - no_games - http_404
    total_games = sum(r["games_found"] for r in results.values())
    total_teams = sum(r["teams_found"] for r in results.values())

    print(f"\n{'='*80}")
    print(f"BATCH SUMMARY: {ok_count}/{total} states with REAL DATA")
    print(f"{'='*80}")
    print(f"  [OK] OK_REAL_DATA: {ok_count}")
    print(f"  [NO] NO_GAMES:     {no_games}")
    print(f"  [XX] HTTP_404:     {http_404}")
    print(f"  [XX] OTHER:        {other}")
    print(f"  Total: {total_games} games, {total_teams} teams")
    print(f"{'='*80}\n")

    return results


def save_batch_results(
    results: Dict[str, Dict],
    year: int,
    output_path: Path
) -> None:
    """Save batch probe results to JSON."""
    payload = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "probe_year": year,
        "batch_size": len(results),
        "states": list(results.values()),
        "summary": {
            "total_states": len(results),
            "ok_real_data": sum(1 for r in results.values() if r["status"] == "OK_REAL_DATA"),
            "no_games": sum(1 for r in results.values() if r["status"] == "NO_GAMES"),
            "http_404": sum(1 for r in results.values() if r["status"] == "HTTP_404"),
            "total_games": sum(r["games_found"] for r in results.values()),
            "total_teams": sum(r["teams_found"] for r in results.values()),
        }
    }

    output_path.write_text(json.dumps(payload, indent=2))
    print(f"[SAVED] Batch results written to: {output_path}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Probe multiple states in a batch for fast testing"
    )
    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="List of state codes (e.g., al tx az in ga)"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="Tournament year (default: 2024)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each state"
    )
    parser.add_argument(
        "--dump-html",
        action="store_true",
        help="Save fetched HTML to data/debug/html/ for inspection"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional: Save results to JSON file (e.g., batch_results.json)"
    )

    args = parser.parse_args()

    # Normalize state codes to uppercase
    states = [s.strip().upper() for s in args.states]

    # Run batch probe
    results = asyncio.run(probe_batch(
        states=states,
        year=args.year,
        verbose=args.verbose,
        dump_html=args.dump_html
    ))

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        save_batch_results(results, args.year, output_path)


if __name__ == "__main__":
    main()
