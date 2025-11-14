"""
Tests for US Datasource Registry

Validates that all registered adapters can be imported and instantiated.
This test catches:
- Missing adapters in registry (forgot to add after creating adapter)
- Typos in module paths or class names
- Missing dependencies (e.g., bs4, pydantic)
- Syntax errors in adapter modules

Design:
- Tests each adapter independently (broken adapter doesn't fail all tests)
- Provides clear error messages showing exactly which adapter is broken
- Runs quickly (lazy imports, no HTTP calls)
"""

import pytest

from src.datasources.us.registry import (
    ADAPTERS,
    STATE_TO_ADAPTER,
    get_adapter_class,
    get_state_adapter_class,
    list_adapters,
    list_states,
)


def test_all_registry_adapters_importable():
    """
    Test that all adapters in ADAPTERS registry can be imported.

    This is the "CI version" of debug_state_imports.py --all.
    If this test fails, it shows exactly which adapter(s) are broken.
    """
    broken = []

    for name in ADAPTERS:
        try:
            cls = get_adapter_class(name)
            # Verify it's actually a class
            assert callable(cls), f"{name} is not callable"
            # Verify it has a __name__ attribute (sanity check it's a class)
            assert hasattr(cls, "__name__"), f"{name} has no __name__ attribute"
        except Exception as e:
            # Capture: (adapter_name, exception_type, exception_message)
            error_msg = str(e)[:200]  # Limit message length for readability
            broken.append((name, type(e).__name__, error_msg))

    # If any adapters are broken, fail test with detailed list
    if broken:
        error_summary = "\n".join(
            f"  - {name}: {exc_type}: {msg}"
            for name, exc_type, msg in broken
        )
        pytest.fail(
            f"Found {len(broken)} broken adapter(s) in registry:\n{error_summary}\n\n"
            f"To debug specific adapter:\n"
            f"  python scripts/debug_state_imports.py --adapter {broken[0][0]}"
        )


def test_state_to_adapter_mapping():
    """
    Test that STATE_TO_ADAPTER mappings point to valid adapters in ADAPTERS.

    Catches:
    - Typo in state mapping (e.g., "WisconsinWiaaDataSource" vs "WisconsinWIAADataSource")
    - State code mapping to non-existent adapter
    """
    broken_mappings = []

    for state_code, adapter_name in STATE_TO_ADAPTER.items():
        if adapter_name not in ADAPTERS:
            broken_mappings.append((state_code, adapter_name))

    if broken_mappings:
        error_summary = "\n".join(
            f"  - {state}: {adapter} (not in ADAPTERS)"
            for state, adapter in broken_mappings
        )
        pytest.fail(
            f"Found {len(broken_mappings)} invalid state mapping(s):\n{error_summary}"
        )


def test_get_state_adapter_class():
    """
    Test get_state_adapter_class() for a known working adapter.

    Uses Wisconsin WIAA as reference (already validated in other tests).
    """
    cls = get_state_adapter_class("WI")
    assert cls.__name__ == "WisconsinWiaaDataSource"
    assert "wisconsin" in cls.__module__.lower()


def test_get_state_adapter_class_invalid_state():
    """Test that invalid state code raises clear KeyError."""
    with pytest.raises(KeyError, match="No adapter registered for state"):
        get_state_adapter_class("XX")


def test_get_adapter_class_invalid_name():
    """Test that invalid adapter name raises clear KeyError."""
    with pytest.raises(KeyError, match="not found in registry"):
        get_adapter_class("NonExistentDataSource")


def test_list_adapters():
    """Test that list_adapters() returns expected count and format."""
    adapters = list_adapters()

    # Should have a reasonable number of US adapters (at least 40)
    # As of Phase 14: 54 adapters (11 national + 5 regional + 38 states/template)
    assert len(adapters) >= 40, f"Expected at least 40 adapters, got {len(adapters)}"

    # Should be sorted
    assert adapters == sorted(adapters)

    # Should all end with "DataSource"
    assert all(name.endswith("DataSource") for name in adapters)

    # Wisconsin WIAA should be in the list
    assert "WisconsinWiaaDataSource" in adapters


def test_list_states():
    """Test that list_states() returns expected count and format."""
    states = list_states()

    # Should have state mappings (not all 50 states are covered yet)
    assert len(states) >= 20, f"Expected at least 20 states, got {len(states)}"

    # Should be sorted
    assert states == sorted(states)

    # Should all be 2-letter codes
    assert all(len(code) == 2 for code in states)

    # Should all be uppercase
    assert all(code.isupper() for code in states)

    # Wisconsin should be in the list
    assert "WI" in states


def test_adapter_instantiation_smoke_test():
    """
    Smoke test: verify Wisconsin WIAA adapter can be instantiated.

    This tests the full path: registry -> import -> instantiation.
    If this fails, it likely means:
    - Missing dependencies in adapter
    - Broken __init__ in adapter
    - Import-time side effects causing failures
    """
    cls = get_adapter_class("WisconsinWiaaDataSource")
    instance = cls()

    # Verify basic attributes
    assert hasattr(instance, "source_type")
    assert hasattr(instance, "source_name")
    assert hasattr(instance, "base_url")

    # Clean up
    import asyncio
    if hasattr(instance, "close"):
        asyncio.run(instance.close())


def test_registry_categories():
    """
    Test that registry contains expected categories of adapters.

    Validates:
    - National circuits (EYBL, 3SSB, UAA, etc.)
    - Regional platforms (Bound, SBLive, etc.)
    - State associations (State-specific adapters)
    """
    adapters = set(list_adapters())

    # National circuits (should have boys + girls variants)
    national_circuits = ["EYBLDataSource", "EYBLGirlsDataSource", "ThreeSSBDataSource",
                         "ThreeSSBGirlsDataSource", "UAADataSource", "UAAGirlsDataSource"]
    for adapter in national_circuits:
        assert adapter in adapters, f"Missing national circuit adapter: {adapter}"

    # Regional platforms
    regional = ["BoundDataSource", "SBLiveDataSource", "RankOneDataSource"]
    for adapter in regional:
        assert adapter in adapters, f"Missing regional adapter: {adapter}"

    # State platforms
    state_platforms = ["MNHubDataSource", "PSALDataSource", "FHSAADataSource", "HHSAADataSource"]
    for adapter in state_platforms:
        assert adapter in adapters, f"Missing state platform adapter: {adapter}"

    # State associations (sample check - not exhaustive)
    state_associations = ["WisconsinWiaaDataSource", "AlabamaAhsaaDataSource",
                          "OhioOhsaaDataSource", "VirginiaVhslDataSource"]
    for adapter in state_associations:
        assert adapter in adapters, f"Missing state association adapter: {adapter}"


@pytest.mark.parametrize("state_code,expected_adapter", [
    ("WI", "WisconsinWiaaDataSource"),
    ("AL", "AlabamaAhsaaDataSource"),
    ("OH", "OhioOhsaaDataSource"),
    ("FL", "FHSAADataSource"),
    ("HI", "HHSAADataSource"),
])
def test_state_code_mappings(state_code, expected_adapter):
    """
    Parametrized test: verify specific state code -> adapter mappings.

    Tests a representative sample of states across different categories:
    - State associations (WI, AL, OH)
    - State platforms (FL, HI)
    """
    assert STATE_TO_ADAPTER[state_code] == expected_adapter
    cls = get_state_adapter_class(state_code)
    assert cls.__name__ == expected_adapter
