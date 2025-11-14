"""
Phase 16 Adapters Smoke Test

Quick validation of Phase 16 adapters without extensive historical testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.oregon_osaa import OregonOSAADataSource
from src.datasources.us.nevada_niaa import NevadaNIAADataSource
from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.datasources.vendors.fibalivestats_federation import FIBALiveStatsFederationDataSource


async def test_adapter(name: str, source, test_brackets: bool = True):
    """Quick smoke test for an adapter."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    results = {
        "name": name,
        "initialized": False,
        "health_check": False,
        "has_brackets": False,
        "bracket_methods_exist": False,
    }

    try:
        # Check initialization
        results["initialized"] = source is not None
        print(f"[OK] Initialized: {source.source_name}")

        # Health check
        try:
            is_healthy = await asyncio.wait_for(source.health_check(), timeout=30)
            results["health_check"] = is_healthy
            print(f"[OK] Health check: {'PASS' if is_healthy else 'FAIL'}")
        except asyncio.TimeoutError:
            print(f"[FAIL] Health check: TIMEOUT (30s)")
        except Exception as e:
            print(f"[FAIL] Health check error: {e}")

        # Check for bracket methods
        if test_brackets and hasattr(source, 'get_tournament_brackets'):
            results["bracket_methods_exist"] = True
            print(f"[OK] Has get_tournament_brackets method")

            # Try to get current season brackets (quick test)
            try:
                print(f"  Testing bracket fetch (timeout: 30s)...")
                brackets = await asyncio.wait_for(
                    source.get_tournament_brackets(season="2024-25"),
                    timeout=30
                )
                if isinstance(brackets, dict):
                    game_count = len(brackets.get("games", []))
                    team_count = len(brackets.get("teams", []))
                    results["has_brackets"] = game_count > 0 or team_count > 0
                    print(f"  [OK] Brackets fetched: {game_count} games, {team_count} teams")
                else:
                    print(f"  [FAIL] Unexpected bracket format")
            except asyncio.TimeoutError:
                print(f"  [FAIL] Bracket fetch TIMEOUT (30s)")
            except Exception as e:
                print(f"  [FAIL] Bracket fetch error: {str(e)[:100]}")

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")

    return results


async def main():
    """Run smoke tests on all Phase 16 adapters."""
    print("\n" + "="*60)
    print("PHASE 16 ADAPTERS SMOKE TEST")
    print("="*60)

    # Test state association adapters
    adapters = [
        ("Arizona AIA", ArizonaAIADataSource()),
        ("Oregon OSAA", OregonOSAADataSource()),
        ("Nevada NIAA", NevadaNIAADataSource()),
        ("Washington WIAA", WashingtonWIAADataSource()),
        ("Idaho IHSAA", IdahoIHSAADataSource()),
    ]

    results = []
    for name, source in adapters:
        result = await test_adapter(name, source, test_brackets=True)
        results.append(result)
        await asyncio.sleep(1)  # Brief pause between adapters

    # Test FIBA Federation adapter (parameterized)
    print(f"\n{'='*60}")
    print("Testing: FIBA Federation (Egypt)")
    print(f"{'='*60}")
    fiba_egy = FIBALiveStatsFederationDataSource(federation_code="EGY", season="2024-25")
    fiba_result = await test_adapter("FIBA Federation (EGY)", fiba_egy, test_brackets=False)
    results.append(fiba_result)

    # Summary
    print(f"\n{'='*60}")
    print("SMOKE TEST SUMMARY")
    print(f"{'='*60}")

    for result in results:
        status = "[PASS]" if result.get("health_check") else "[FAIL]"
        print(f"{result['name']:30} {status}")

    # Overall stats
    total = len(results)
    passed = sum(1 for r in results if r.get("health_check"))
    print(f"\nTotal: {total} | Passed: {passed} | Failed: {total - passed}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
