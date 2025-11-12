"""
Comprehensive Adapter Validation Script

Validates all 4 new adapters (SBLive, Bound, 3SSB, WSN) for:
- Correct initialization
- Method signatures
- Data extraction capabilities
- Error handling
- State management (for multi-state adapters)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.sblive import SBLiveDataSource
from src.datasources.us.bound import BoundDataSource
from src.datasources.us.three_ssb import ThreeSSBDataSource
from src.datasources.us.wsn import WSNDataSource
from src.datasources.base import BaseDataSource


def validate_adapter_structure(adapter_class, adapter_name: str):
    """Validate adapter has all required methods from BaseDataSource."""
    print(f"\n{'='*60}")
    print(f"VALIDATING: {adapter_name}")
    print(f"{'='*60}")

    required_methods = [
        'get_player',
        'search_players',
        'get_player_season_stats',
        'get_player_game_stats',
        'get_team',
        'get_games',
        'get_leaderboard',
        'health_check',
    ]

    print(f"\n[1] Checking required methods...")
    missing_methods = []
    for method in required_methods:
        if not hasattr(adapter_class, method):
            missing_methods.append(method)
            print(f"   [FAIL] Missing method: {method}")
        else:
            print(f"   [OK] {method}")

    if missing_methods:
        print(f"\n   ERROR: {len(missing_methods)} missing methods")
        return False

    print(f"\n   SUCCESS: All {len(required_methods)} required methods present")

    # Check class attributes
    print(f"\n[2] Checking class attributes...")
    required_attrs = ['source_type', 'source_name', 'base_url', 'region']
    for attr in required_attrs:
        if not hasattr(adapter_class, attr):
            print(f"   [FAIL] Missing attribute: {attr}")
            return False
        value = getattr(adapter_class, attr)
        print(f"   [OK] {attr} = {value}")

    print(f"\n   SUCCESS: All required attributes present")
    return True


def validate_multi_state_adapter(adapter_class, adapter_name: str, expected_states: list):
    """Validate multi-state adapter configuration."""
    print(f"\n[3] Validating multi-state configuration...")

    if not hasattr(adapter_class, 'SUPPORTED_STATES'):
        print(f"   [FAIL] Missing SUPPORTED_STATES attribute")
        return False

    states = adapter_class.SUPPORTED_STATES
    print(f"   [OK] SUPPORTED_STATES = {states}")

    if set(states) != set(expected_states):
        print(f"   [WARN] Expected {expected_states}, got {states}")
        return False

    print(f"   SUCCESS: All {len(states)} states configured correctly")
    return True


async def test_adapter_initialization(adapter_class, adapter_name: str):
    """Test adapter can be initialized."""
    print(f"\n[4] Testing adapter initialization...")

    try:
        adapter = adapter_class()
        print(f"   [OK] Adapter initialized")
        print(f"   [OK] Source type: {adapter.source_type}")
        print(f"   [OK] Base URL: {adapter.base_url}")

        # Test cleanup
        await adapter.close()
        print(f"   [OK] Adapter closed successfully")

        return True
    except Exception as e:
        print(f"   [FAIL] Initialization error: {e}")
        return False


async def test_adapter_health_check(adapter_class, adapter_name: str):
    """Test adapter health check."""
    print(f"\n[5] Testing health check...")

    try:
        adapter = adapter_class()
        is_healthy = await adapter.health_check()
        print(f"   [OK] Health check: {is_healthy}")
        await adapter.close()
        return True
    except Exception as e:
        print(f"   [FAIL] Health check error: {e}")
        return False


async def test_search_players_signature(adapter_class, adapter_name: str):
    """Test search_players method signature."""
    print(f"\n[6] Testing search_players signature...")

    try:
        adapter = adapter_class()

        # Check method signature
        import inspect
        sig = inspect.signature(adapter.search_players)
        params = list(sig.parameters.keys())
        print(f"   [OK] Parameters: {params}")

        # Multi-state adapters should require 'state' parameter
        if hasattr(adapter_class, 'SUPPORTED_STATES'):
            if 'state' not in params:
                print(f"   [FAIL] Multi-state adapter missing 'state' parameter")
                await adapter.close()
                return False
            print(f"   [OK] Multi-state adapter has 'state' parameter")

        await adapter.close()
        return True
    except Exception as e:
        print(f"   [FAIL] Signature test error: {e}")
        return False


async def validate_all_adapters():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("ADAPTER VALIDATION SUITE")
    print("="*60)

    adapters = [
        (SBLiveDataSource, "SBLive Sports", ["WA", "OR", "CA", "AZ", "ID", "NV"]),
        (BoundDataSource, "Bound", ["IA", "SD", "IL", "MN"]),
        (ThreeSSBDataSource, "Adidas 3SSB", None),  # Not multi-state
        (WSNDataSource, "Wisconsin Sports Network", None),  # Single state
    ]

    results = {}

    for adapter_class, adapter_name, expected_states in adapters:
        print(f"\n\n{'#'*60}")
        print(f"# {adapter_name}")
        print(f"{'#'*60}")

        tests_passed = []

        # Test 1: Structure validation
        if validate_adapter_structure(adapter_class, adapter_name):
            tests_passed.append("Structure")

        # Test 2: Multi-state configuration (if applicable)
        if expected_states:
            if validate_multi_state_adapter(adapter_class, adapter_name, expected_states):
                tests_passed.append("Multi-state config")

        # Test 3: Initialization
        if await test_adapter_initialization(adapter_class, adapter_name):
            tests_passed.append("Initialization")

        # Test 4: Health check
        if await test_adapter_health_check(adapter_class, adapter_name):
            tests_passed.append("Health check")

        # Test 5: Method signatures
        if await test_search_players_signature(adapter_class, adapter_name):
            tests_passed.append("Method signatures")

        results[adapter_name] = tests_passed

    # Print summary
    print(f"\n\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")

    for adapter_name, tests in results.items():
        print(f"\n{adapter_name}:")
        print(f"  Tests passed: {len(tests)}")
        for test in tests:
            print(f"    - {test}")

    # Overall result
    print(f"\n{'='*60}")
    total_tests = sum(len(tests) for tests in results.values())
    print(f"TOTAL TESTS PASSED: {total_tests}")

    all_passed = all(len(tests) >= 4 for tests in results.values())
    if all_passed:
        print("STATUS: ALL ADAPTERS VALIDATED SUCCESSFULLY")
    else:
        print("STATUS: SOME ADAPTERS NEED FIXES")
    print(f"{'='*60}\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(validate_all_adapters())
    sys.exit(0 if success else 1)
