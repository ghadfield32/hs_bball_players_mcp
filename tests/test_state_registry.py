"""
Tests for State Registry - Real Data Coverage Tracking

Validates STATE_REGISTRY structure and ensures registry-driven
routing works correctly. NO SYNTHETIC DATA - tests routing only.
"""

import pytest

from src.state_registry import (
    STATE_REGISTRY,
    StateCoverage,
    get_state_config,
    list_verified_states,
    get_coverage_summary,
)


class TestStateRegistryStructure:
    """Validate STATE_REGISTRY data structure and integrity."""

    def test_registry_not_empty(self):
        """Registry should contain all 35 Phase 17-22 states."""
        assert len(STATE_REGISTRY) == 35, \
            f"Expected 35 states, got {len(STATE_REGISTRY)}"

    def test_all_keys_are_uppercase(self):
        """State abbreviations should be uppercase for consistency."""
        for key in STATE_REGISTRY.keys():
            assert key.isupper(), f"State key {key!r} should be uppercase"
            assert len(key) == 2, f"State key {key!r} should be 2 letters"

    def test_all_entries_are_state_coverage(self):
        """All registry values should be StateCoverage instances."""
        for abbrev, cfg in STATE_REGISTRY.items():
            assert isinstance(cfg, StateCoverage), \
                f"State {abbrev} config should be StateCoverage instance"

    def test_all_entries_have_required_fields(self):
        """Every StateCoverage entry should have required attributes."""
        required_fields = ["id", "abbrev", "org", "datasource_cls"]

        for abbrev, cfg in STATE_REGISTRY.items():
            for field in required_fields:
                assert hasattr(cfg, field), \
                    f"State {abbrev} missing required field: {field}"
                assert getattr(cfg, field), \
                    f"State {abbrev} field {field} is empty"

    def test_abbreviations_match_keys(self):
        """StateCoverage.abbrev should match registry key."""
        for key, cfg in STATE_REGISTRY.items():
            assert cfg.abbrev == key, \
                f"Key {key} doesn't match abbrev {cfg.abbrev}"

    def test_verified_seasons_implies_has_brackets(self):
        """If verified_seasons exists, has_brackets should be True."""
        for abbrev, cfg in STATE_REGISTRY.items():
            if cfg.verified_seasons:
                assert cfg.has_brackets, \
                    f"State {abbrev} has verified_seasons but has_brackets=False"

    def test_known_verified_state_alabama(self):
        """Alabama (AL) should be marked as verified from Phase 23 probe."""
        al_cfg = STATE_REGISTRY["AL"]
        assert al_cfg.has_brackets is True, \
            "Alabama should have has_brackets=True from probe"
        assert 2024 in al_cfg.verified_seasons, \
            "Alabama should have 2024 in verified_seasons"
        assert al_cfg.id == "ahsaa"
        assert al_cfg.org == "AHSAA"


class TestGetStateConfig:
    """Test get_state_config() helper function."""

    def test_get_state_config_valid_state(self):
        """Should return StateCoverage for valid state."""
        cfg = get_state_config("AL")
        assert isinstance(cfg, StateCoverage)
        assert cfg.abbrev == "AL"
        assert cfg.org == "AHSAA"

    def test_get_state_config_case_insensitive(self):
        """Should work with lowercase state codes."""
        cfg_upper = get_state_config("AL")
        cfg_lower = get_state_config("al")
        cfg_mixed = get_state_config("Al")

        assert cfg_upper.abbrev == cfg_lower.abbrev == cfg_mixed.abbrev == "AL"

    def test_get_state_config_invalid_state(self):
        """Should raise KeyError for unknown states."""
        with pytest.raises(KeyError) as exc_info:
            get_state_config("ZZ")

        assert "Unknown state abbreviation" in str(exc_info.value)
        assert "Available states" in str(exc_info.value)


class TestListVerifiedStates:
    """Test list_verified_states() helper function."""

    def test_list_verified_states_includes_alabama(self):
        """Alabama should be in verified states list."""
        verified = list_verified_states()
        assert "AL" in verified, \
            "Alabama should be in verified states (probe confirmed 2024)"

    def test_verified_states_are_uppercase(self):
        """All verified state codes should be uppercase."""
        verified = list_verified_states()
        for abbrev in verified:
            assert abbrev.isupper()
            assert len(abbrev) == 2

    def test_verified_states_subset_of_registry(self):
        """Verified states should be subset of registry keys."""
        verified = set(list_verified_states())
        all_states = set(STATE_REGISTRY.keys())
        assert verified.issubset(all_states)


class TestGetCoverageSummary:
    """Test get_coverage_summary() stats function."""

    def test_coverage_summary_structure(self):
        """Summary should have expected keys."""
        summary = get_coverage_summary()

        required_keys = [
            "total_states",
            "verified_states",
            "unverified_states",
            "coverage_pct",
            "needs_url_discovery",
            "has_ssl_issues",
            "pending_probe",
        ]

        for key in required_keys:
            assert key in summary, f"Summary missing key: {key}"

    def test_coverage_summary_totals(self):
        """Total and verified counts should match expectations."""
        summary = get_coverage_summary()

        assert summary["total_states"] == 35
        assert summary["verified_states"] >= 1, \
            "At least Alabama should be verified"
        assert summary["unverified_states"] == \
            summary["total_states"] - summary["verified_states"]

    def test_coverage_percentage_calculation(self):
        """Coverage percentage should be correct."""
        summary = get_coverage_summary()

        expected_pct = round(
            summary["verified_states"] / summary["total_states"] * 100, 1
        )
        assert summary["coverage_pct"] == expected_pct


@pytest.mark.integration
class TestAdapterClassReferences:
    """Validate adapter class references are importable."""

    def test_adapter_classes_are_callable(self):
        """All datasource_cls references should be instantiable."""
        for abbrev, cfg in STATE_REGISTRY.items():
            # Should not raise ImportError or AttributeError
            adapter = cfg.datasource_cls()
            assert adapter is not None, \
                f"State {abbrev} adapter failed to instantiate"
            assert hasattr(adapter, "source_type"), \
                f"State {abbrev} adapter missing source_type"
            assert hasattr(adapter, "source_name"), \
                f"State {abbrev} adapter missing source_name"
