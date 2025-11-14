#!/usr/bin/env python
"""
Debug US Datasource Adapter Imports

Tests import of US datasource adapters to diagnose dependency issues.
Shows EXACT error with full traceback instead of vague ImportError.

Usage:
    # Test single adapter
    python scripts/debug_state_imports.py --adapter WisconsinWiaaDataSource

    # Test by state code
    python scripts/debug_state_imports.py --state WI

    # Test all adapters
    python scripts/debug_state_imports.py --all

    # Test specific category
    python scripts/debug_state_imports.py --category state_southeast

Examples:
    # Debug Wisconsin WIAA import
    python scripts/debug_state_imports.py --state WI

    # Test all national circuits
    python scripts/debug_state_imports.py --category national

    # Find all broken adapters
    python scripts/debug_state_imports.py --all --summary-only
"""

import argparse
import sys
import traceback
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import registry (this is lightweight, no actual adapters loaded yet)
from src.datasources.us.registry import (
    ADAPTERS,
    STATE_TO_ADAPTER,
    get_adapter_class,
    get_state_adapter_class,
)

# Categorize adapters for targeted testing
CATEGORIES: Dict[str, List[str]] = {
    "national": [
        "BoundDataSource",
        "EYBLDataSource",
        "EYBLGirlsDataSource",
        "GrindSessionDataSource",
        "OTEDataSource",
        "RankOneDataSource",
        "SBLiveDataSource",
        "ThreeSSBDataSource",
        "ThreeSSBGirlsDataSource",
        "UAADataSource",
        "UAAGirlsDataSource",
    ],
    "regional": [
        "FHSAADataSource",
        "HHSAADataSource",
        "MNHubDataSource",
        "PSALDataSource",
        "WSNDataSource",
    ],
    "state_southeast": [
        "AlabamaAhsaaDataSource",
        "ArkansasAaaDataSource",
        "GeorgiaGhsaDataSource",
        "KentuckyKhsaaDataSource",
        "LouisianaLhsaaDataSource",
        "MississippiMhsaaDataSource",
        "NCHSAADataSource",
        "SouthCarolinaSchslDataSource",
        "TennesseeTssaaDataSource",
        "VirginiaVhslDataSource",
        "WestVirginiaWvssacDataSource",
    ],
    "state_northeast": [
        "ConnecticutCiacDataSource",
        "DelawareDiaaDataSource",
        "MaineMpaDataSource",
        "MarylandMpssaaDataSource",
        "MassachusettsMiaaDataSource",
        "NEPSACDataSource",
        "NewHampshireNhiaaDataSource",
        "NewJerseyNjsiaaDataSource",
        "PennsylvaniaPiaaDataSource",
        "RhodeIslandRiilDataSource",
        "VermontVpaDataSource",
    ],
    "state_midwest": [
        "IndianaIhsaaDataSource",
        "KansasKshsaaDataSource",
        "MichiganMhsaaDataSource",
        "MissouriMshsaaDataSource",
        "NebraskaNsaaDataSource",
        "NorthDakotaNdhsaaDataSource",
        "OhioOhsaaDataSource",
        "WisconsinWiaaDataSource",
    ],
    "state_west": [
        "AlaskaAsaaDataSource",
        "ColoradoChsaaDataSource",
        "DcDciaaDataSource",
        "MontanaMhsaDataSource",
        "NewMexicoNmaaDataSource",
        "OklahomaOssaaDataSource",
        "UtahUhsaaDataSource",
        "WyomingWhsaaDataSource",
    ],
}


def test_adapter_import(adapter_name: str, verbose: bool = True) -> bool:
    """
    Test import of a single adapter.

    Args:
        adapter_name: Name of adapter class to test
        verbose: If True, print full traceback on failure

    Returns:
        True if import succeeded, False otherwise
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f"Testing: {adapter_name}")
        print(f"{'='*80}")

    try:
        cls = get_adapter_class(adapter_name)
        module_path = ADAPTERS[adapter_name].split(":")[0]

        if verbose:
            print(f"✅ SUCCESS")
            print(f"   Module: {module_path}")
            print(f"   Class:  {cls.__name__}")
            print(f"   Bases:  {[b.__name__ for b in cls.__bases__]}")

            # Try to instantiate to catch __init__ errors
            try:
                instance = cls()
                print(f"   Init:   ✅ Can instantiate")
                # Clean up
                if hasattr(instance, "close"):
                    import asyncio

                    asyncio.run(instance.close())
            except Exception as e:
                print(f"   Init:   ⚠️  Instantiation failed: {e}")

        return True

    except KeyError as e:
        print(f"❌ FAILED: Adapter not in registry")
        if verbose:
            print(f"   Error: {e}")
        return False

    except ImportError as e:
        print(f"❌ FAILED: Import error")
        if verbose:
            print(f"\nRoot Cause Analysis:")
            print(f"   {e}")
            print(f"\nFull Traceback:")
            traceback.print_exc()
            print(f"\n💡 Tip: This usually means a missing dependency.")
            print(f"   Try: pip install -e . (to install all deps)")
        return False

    except AttributeError as e:
        print(f"❌ FAILED: Attribute error")
        if verbose:
            print(f"   {e}")
            traceback.print_exc()
        return False

    except Exception as e:
        print(f"❌ FAILED: Unexpected error")
        if verbose:
            print(f"   {type(e).__name__}: {e}")
            traceback.print_exc()
        return False


def main() -> int:
    """Run adapter import diagnostics."""
    parser = argparse.ArgumentParser(
        description="Debug US datasource adapter imports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--adapter", help="Test specific adapter by class name (e.g., WisconsinWiaaDataSource)"
    )
    group.add_argument(
        "--state", help="Test adapter by state code (e.g., WI)"
    )
    group.add_argument(
        "--category",
        choices=list(CATEGORIES.keys()),
        help="Test all adapters in category",
    )
    group.add_argument(
        "--all", action="store_true", help="Test all adapters"
    )

    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show summary only, not full tracebacks",
    )

    args = parser.parse_args()

    # Determine which adapters to test
    adapters_to_test: List[str] = []

    if args.adapter:
        adapters_to_test = [args.adapter]
    elif args.state:
        state_code = args.state.upper()
        if state_code not in STATE_TO_ADAPTER:
            print(f"❌ Error: No adapter for state '{state_code}'")
            print(f"Available states: {', '.join(sorted(STATE_TO_ADAPTER.keys()))}")
            return 1
        adapter_name = STATE_TO_ADAPTER[state_code]
        adapters_to_test = [adapter_name]
    elif args.category:
        adapters_to_test = CATEGORIES[args.category]
    elif args.all:
        adapters_to_test = sorted(ADAPTERS.keys())

    # Run tests
    verbose = not args.summary_only
    results = {}

    print(f"\n🔍 Testing {len(adapters_to_test)} adapter(s)...\n")

    for adapter_name in adapters_to_test:
        success = test_adapter_import(adapter_name, verbose=verbose)
        results[adapter_name] = success

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed

    print(f"✅ Passed: {passed}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")

    if failed > 0:
        print(f"\nFailed adapters:")
        for adapter_name, success in results.items():
            if not success:
                print(f"  - {adapter_name}")

        print(f"\n💡 To debug a specific adapter:")
        failed_adapter = next(name for name, success in results.items() if not success)
        print(f"   python scripts/debug_state_imports.py --adapter {failed_adapter}")

    # Exit code: 0 if all passed, 1 if any failed
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
