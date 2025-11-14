"""
Lightweight recency smoke: confirms pages are reachable and contain a 2025 token
(or returns structured diagnostic if not). Does NOT treat 404 as success.

This script validates that data sources are reachable and have 2025 season data.
It surfaces data availability truthfully with no silent failures.

Usage:
    python scripts/smoke_recent_results_2025.py

Exit codes:
    0: All checks passed
    1: One or more checks failed or data not found
"""

import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.datasources.us.nevada_niaa import NevadaNIAADataSource


async def check_arizona() -> dict:
    """
    Check Arizona AIA for 2025 season data.

    Returns:
        dict with keys: source, reachable, has_2025, url, note
    """
    ds = ArizonaAIADataSource()
    try:
        # First check if API is reachable
        is_healthy = await ds.health_check()
        if not is_healthy:
            return {
                "source": "Arizona AIA",
                "reachable": False,
                "has_2025": False,
                "url": ds.base_url,
                "note": "Health check failed - API unreachable"
            }

        # Try to fetch 2025 data (just one conference to keep it fast)
        brackets = await ds.get_tournament_brackets(season="2024-25", conference="6A", gender="Boys")

        has_2025 = False
        if brackets and brackets.get("games"):
            # Check if any games have 2025 data
            for game in brackets["games"]:
                if game.season and "24-25" in game.season:
                    has_2025 = True
                    break

        return {
            "source": "Arizona AIA",
            "reachable": True,
            "has_2025": has_2025,
            "url": ds.base_url,
            "note": f"Found {len(brackets.get('games', []))} games" if has_2025 else "No 2024-25 games found yet"
        }
    except Exception as e:
        # If we get here, API is reachable but returned an error
        return {
            "source": "Arizona AIA",
            "reachable": True,
            "has_2025": False,
            "url": ds.base_url,
            "note": f"API reachable, data fetch failed: {str(e)[:60]}"
        }
    finally:
        await ds.close()


async def check_idaho() -> dict:
    """
    Check Idaho IHSAA for 2025 season data.

    Returns:
        dict with keys: source, reachable, has_2025, url, note
    """
    ds = IdahoIHSAADataSource()
    try:
        # First check if API is reachable
        is_healthy = await ds.health_check()
        if not is_healthy:
            return {
                "source": "Idaho IHSAA",
                "reachable": False,
                "has_2025": False,
                "url": ds.base_url,
                "note": "Health check failed - API unreachable"
            }

        # Try to fetch 2025 data (just one classification to keep it fast)
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="5A", gender="Boys")

        has_2025 = False
        if brackets and brackets.get("games"):
            for game in brackets["games"]:
                if game.season and "24-25" in game.season:
                    has_2025 = True
                    break

        return {
            "source": "Idaho IHSAA",
            "reachable": True,
            "has_2025": has_2025,
            "url": ds.base_url,
            "note": f"Found {len(brackets.get('games', []))} games" if has_2025 else "No 2024-25 games found yet"
        }
    except Exception as e:
        return {
            "source": "Idaho IHSAA",
            "reachable": True,
            "has_2025": False,
            "url": ds.base_url,
            "note": f"API reachable, data fetch failed: {str(e)[:60]}"
        }
    finally:
        await ds.close()


async def check_washington() -> dict:
    """
    Check Washington WIAA for 2025 season data.

    Returns:
        dict with keys: source, reachable, has_2025, url, note
    """
    ds = WashingtonWIAADataSource()
    try:
        # First check if API is reachable
        is_healthy = await ds.health_check()
        if not is_healthy:
            return {
                "source": "Washington WIAA",
                "reachable": False,
                "has_2025": False,
                "url": ds.base_url,
                "note": "Health check failed - API unreachable"
            }

        # Try to fetch 2025 data (just one classification to keep it fast)
        brackets = await ds.get_tournament_brackets(season="2024-25", classification="4A", gender="Boys")

        has_2025 = False
        if brackets and brackets.get("games"):
            for game in brackets["games"]:
                if game.season and "24-25" in game.season:
                    has_2025 = True
                    break

        return {
            "source": "Washington WIAA",
            "reachable": True,
            "has_2025": has_2025,
            "url": ds.base_url,
            "note": f"Found {len(brackets.get('games', []))} games" if has_2025 else "No 2024-25 games found yet"
        }
    except Exception as e:
        return {
            "source": "Washington WIAA",
            "reachable": True,
            "has_2025": False,
            "url": ds.base_url,
            "note": f"API reachable, data fetch failed: {str(e)[:60]}"
        }
    finally:
        await ds.close()


async def check_nevada() -> dict:
    """
    Check Nevada NIAA for 2025 season data.

    Returns:
        dict with keys: source, reachable, has_2025, url, note
    """
    ds = NevadaNIAADataSource()
    try:
        # First check if API is reachable
        is_healthy = await ds.health_check()
        if not is_healthy:
            return {
                "source": "Nevada NIAA",
                "reachable": False,
                "has_2025": False,
                "url": ds.base_url,
                "note": "Health check failed - API unreachable"
            }

        # Try to fetch 2025 data (just one division to keep it fast - Nevada uses PDFs)
        brackets = await ds.get_tournament_brackets(season="2024-25", division="5A", gender="Boys")

        has_2025 = False
        if brackets and brackets.get("games"):
            for game in brackets["games"]:
                if game.season and "24-25" in game.season:
                    has_2025 = True
                    break

        return {
            "source": "Nevada NIAA",
            "reachable": True,
            "has_2025": has_2025,
            "url": ds.base_url,
            "note": f"Found {len(brackets.get('games', []))} games" if has_2025 else "No 2024-25 games found yet"
        }
    except Exception as e:
        return {
            "source": "Nevada NIAA",
            "reachable": True,
            "has_2025": False,
            "url": ds.base_url,
            "note": f"API reachable, data fetch failed: {str(e)[:60]}"
        }
    finally:
        await ds.close()


async def main():
    """
    Run all smoke tests and print structured output.

    Exit codes:
        0: All checks passed (all reachable and have 2025 data)
        1: One or more checks failed
    """
    print("=" * 80)
    print("Phase 16 Smoke Test: 2025 Season Data Availability")
    print("=" * 80)
    print()

    # Run all checks concurrently
    results = await asyncio.gather(
        check_arizona(),
        check_idaho(),
        check_washington(),
        check_nevada(),
        return_exceptions=True
    )

    # Print header
    print(f"{'Source':<20} | {'Status':<12} | {'Has 2025':<10} | {'Note':<40}")
    print("-" * 80)

    all_passed = True

    for result in results:
        if isinstance(result, Exception):
            print(f"{'UNKNOWN':<20} | {'ERROR':<12} | {'NO':<10} | {str(result)[:40]}")
            all_passed = False
            continue

        source = result["source"]
        reachable = result["reachable"]
        has_2025 = result["has_2025"]
        note = result["note"]

        # Determine status (using ASCII to avoid Windows console Unicode errors)
        if reachable and has_2025:
            status = "[PASS]"
        elif reachable and not has_2025:
            status = "[NO DATA]"
            all_passed = False
        else:
            status = "[FAIL]"
            all_passed = False

        has_2025_str = "YES" if has_2025 else "NO"

        print(f"{source:<20} | {status:<12} | {has_2025_str:<10} | {note:<40}")

    print()
    print("=" * 80)

    if all_passed:
        print("[PASS] All checks passed: All sources reachable with 2025 data")
        print()
        return 0
    else:
        print("[FAIL] Some checks failed: See details above")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
