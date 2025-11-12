"""
Categorical Validation Tests

Tests for unified schema categorical encodings and normalization functions.
Ensures all sources are properly mapped and categories are consistent.
"""

import pytest

from src.unified.categories import (
    CIRCUIT_KEYS,
    SOURCE_TYPES,
    SourceType,
    normalize_gender,
    normalize_level,
    map_source_meta,
)


class TestCircuitKeysCoverage:
    """Test that all sources have circuit keys defined."""

    def test_all_active_sources_have_circuit_keys(self):
        """All active sources from aggregator should have circuit keys."""
        # Active sources from aggregator.py (as of Phase 11)
        active_sources = [
            # US National Circuits
            "eybl",
            "eybl_girls",
            "three_ssb",
            "three_ssb_girls",
            "uaa",
            "uaa_girls",
            # US Multi-State
            "bound",
            "sblive",
            "rankone",
            # US Single-State
            "mn_hub",
            "psal",
            "wsn",
            # US State Associations
            "fhsaa",
            "hhsaa",
            # US Event Platforms (Phase 10/11)
            "cifsshome",
            "uil_brackets",
            "exposure_events",
            "tourneymachine",
            # Europe Youth Leagues
            "nbbl",
            "feb",
            "mkl",
            "lnb_espoirs",
            # Canada
            "npa",
            # Global
            "fiba_youth",
            "fiba_livestats",
        ]

        missing = [s for s in active_sources if s not in CIRCUIT_KEYS]
        assert not missing, f"Missing circuit keys for active sources: {missing}"

    def test_circuit_keys_are_uppercase(self):
        """All circuit key values should be uppercase."""
        for source_key, circuit_key in CIRCUIT_KEYS.items():
            assert circuit_key.isupper(), f"Circuit key '{circuit_key}' for '{source_key}' should be uppercase"

    def test_circuit_keys_unique(self):
        """Circuit keys should be unique across sources."""
        values = list(CIRCUIT_KEYS.values())
        duplicates = [v for v in set(values) if values.count(v) > 1]
        assert not duplicates, f"Duplicate circuit keys found: {duplicates}"


class TestSourceTypesCoverage:
    """Test that all sources have source types defined."""

    def test_all_active_sources_have_source_types(self):
        """All active sources should have source types defined."""
        active_sources = [
            "eybl",
            "eybl_girls",
            "three_ssb",
            "three_ssb_girls",
            "uaa",
            "uaa_girls",
            "bound",
            "sblive",
            "rankone",
            "mn_hub",
            "psal",
            "wsn",
            "fhsaa",
            "hhsaa",
            "cifsshome",
            "uil_brackets",
            "exposure_events",
            "tourneymachine",
            "nbbl",
            "feb",
            "mkl",
            "lnb_espoirs",
            "npa",
            "fiba_youth",
            "fiba_livestats",
        ]

        missing = [s for s in active_sources if s not in SOURCE_TYPES]
        assert not missing, f"Missing source types for active sources: {missing}"

    def test_source_types_are_valid_enums(self):
        """All source type values should be valid SourceType enum members."""
        valid_types = {st.value for st in SourceType}

        for source_key, source_type in SOURCE_TYPES.items():
            assert (
                source_type in valid_types
            ), f"Source '{source_key}' has invalid type '{source_type}'. Valid: {valid_types}"

    def test_source_type_distribution(self):
        """Test that source types are distributed as expected."""
        type_counts = {}
        for source_type in SOURCE_TYPES.values():
            type_counts[source_type] = type_counts.get(source_type, 0) + 1

        # Verify we have sources of each type
        assert "CIRCUIT" in type_counts, "Should have CIRCUIT sources"
        assert "ASSOCIATION" in type_counts, "Should have ASSOCIATION sources"
        assert "PLATFORM" in type_counts, "Should have PLATFORM sources"
        assert "LEAGUE" in type_counts, "Should have LEAGUE sources"
        assert "EVENT" in type_counts, "Should have EVENT sources"

        # Associations should be the largest category (all state associations)
        assert type_counts["ASSOCIATION"] > 20, "Should have 20+ state associations"


class TestGenderNormalization:
    """Test gender normalization function."""

    def test_normalize_male_variants(self):
        """Test various male gender inputs."""
        male_inputs = ["m", "M", "boys", "BOYS", "men", "MEN", "male", "MALE"]
        for input_val in male_inputs:
            assert normalize_gender(input_val) == "M", f"'{input_val}' should normalize to 'M'"

    def test_normalize_female_variants(self):
        """Test various female gender inputs."""
        female_inputs = ["f", "F", "girls", "GIRLS", "women", "WOMEN", "female", "FEMALE", "w", "W"]
        for input_val in female_inputs:
            assert normalize_gender(input_val) == "F", f"'{input_val}' should normalize to 'F'"

    def test_normalize_empty_defaults_to_male(self):
        """Empty/None gender should default to male."""
        assert normalize_gender(None) == "M"
        assert normalize_gender("") == "M"
        assert normalize_gender("  ") == "M"

    def test_normalize_unknown_defaults_to_male(self):
        """Unknown gender strings should default to male."""
        assert normalize_gender("unknown") == "M"
        assert normalize_gender("other") == "M"


class TestLevelNormalization:
    """Test level normalization function."""

    def test_normalize_age_groups(self):
        """Test age group normalization."""
        assert normalize_level("eybl", "U17") == "U17"
        assert normalize_level("eybl", "u17") == "U17"
        assert normalize_level("feb", "U16") == "U16"
        assert normalize_level("mkl", "U20") == "U20"

    def test_normalize_prep_sources(self):
        """Test prep school level normalization."""
        assert normalize_level("nepsac", None) == "PREP"
        assert normalize_level("npa", None) == "PREP"

    def test_normalize_high_school_sources(self):
        """Test high school level normalization."""
        assert normalize_level("psal", None) == "HS"
        assert normalize_level("mn_hub", None) == "HS"
        assert normalize_level("fhsaa", None) == "HS"
        assert normalize_level("ghsa", None) == "HS"

    def test_normalize_grassroots_defaults_to_high_school(self):
        """Grassroots circuits should default to HS."""
        assert normalize_level("eybl", None) == "HS"
        assert normalize_level("three_ssb", None) == "HS"
        assert normalize_level("uaa", None) == "HS"

    def test_age_group_overrides_source_default(self):
        """Age group should override source-based level."""
        # Even though PSAL is HS, U17 should take precedence
        assert normalize_level("psal", "U17") == "U17"
        assert normalize_level("nepsac", "U16") == "U16"


class TestSourceMetaMapping:
    """Test source metadata mapping function."""

    def test_map_source_meta_returns_all_fields(self):
        """map_source_meta should return circuit, source_type, and gender."""
        meta = map_source_meta("eybl")
        assert "circuit" in meta
        assert "source_type" in meta
        assert "gender" in meta

    def test_map_source_meta_circuits(self):
        """Test metadata for circuit sources."""
        eybl_meta = map_source_meta("eybl")
        assert eybl_meta["circuit"] == "EYBL"
        assert eybl_meta["source_type"] == "CIRCUIT"
        assert eybl_meta["gender"] == "M"

        eybl_girls_meta = map_source_meta("eybl_girls")
        assert eybl_girls_meta["circuit"] == "EYBL_GIRLS"
        assert eybl_girls_meta["source_type"] == "CIRCUIT"
        assert eybl_girls_meta["gender"] == "F"

    def test_map_source_meta_state_associations(self):
        """Test metadata for state association sources."""
        fhsaa_meta = map_source_meta("fhsaa")
        assert fhsaa_meta["circuit"] == "FHSAA"
        assert fhsaa_meta["source_type"] == "ASSOCIATION"
        assert fhsaa_meta["gender"] == "M"  # Default

    def test_map_source_meta_event_platforms(self):
        """Test metadata for event platform sources (Phase 10/11)."""
        exposure_meta = map_source_meta("exposure_events")
        assert exposure_meta["circuit"] == "EXPOSURE_EVENTS"
        assert exposure_meta["source_type"] == "EVENT"
        assert exposure_meta["gender"] == "M"

        tourney_meta = map_source_meta("tourneymachine")
        assert tourney_meta["circuit"] == "TOURNEYMACHINE"
        assert tourney_meta["source_type"] == "EVENT"
        assert tourney_meta["gender"] == "M"

    def test_map_source_meta_european_leagues(self):
        """Test metadata for European youth leagues."""
        nbbl_meta = map_source_meta("nbbl")
        assert nbbl_meta["circuit"] == "NBBL"
        assert nbbl_meta["source_type"] == "LEAGUE"
        assert nbbl_meta["gender"] == "M"


class TestPhase10And11SourcesCoverage:
    """Test that Phase 10/11 sources are properly registered."""

    def test_phase_10_11_sources_in_circuit_keys(self):
        """Phase 10/11 sources should be in CIRCUIT_KEYS."""
        phase_10_11_sources = ["cifsshome", "uil_brackets", "exposure_events", "tourneymachine"]

        for source in phase_10_11_sources:
            assert source in CIRCUIT_KEYS, f"Phase 10/11 source '{source}' missing from CIRCUIT_KEYS"

    def test_phase_10_11_sources_in_source_types(self):
        """Phase 10/11 sources should be in SOURCE_TYPES."""
        phase_10_11_sources = ["cifsshome", "uil_brackets", "exposure_events", "tourneymachine"]

        for source in phase_10_11_sources:
            assert source in SOURCE_TYPES, f"Phase 10/11 source '{source}' missing from SOURCE_TYPES"

    def test_event_platforms_classified_correctly(self):
        """Event platforms should be classified as EVENT type."""
        assert SOURCE_TYPES["exposure_events"] == "EVENT"
        assert SOURCE_TYPES["tourneymachine"] == "EVENT"

    def test_state_platforms_classified_correctly(self):
        """State-specific platforms should be classified as ASSOCIATION."""
        assert SOURCE_TYPES["cifsshome"] == "ASSOCIATION"
        assert SOURCE_TYPES["uil_brackets"] == "ASSOCIATION"


class TestComprehensiveCoverage:
    """Test comprehensive coverage across all sources."""

    def test_circuit_keys_and_source_types_aligned(self):
        """All sources in CIRCUIT_KEYS should also be in SOURCE_TYPES."""
        circuit_keys_sources = set(CIRCUIT_KEYS.keys())
        source_types_sources = set(SOURCE_TYPES.keys())

        missing_from_types = circuit_keys_sources - source_types_sources
        assert not missing_from_types, f"Sources in CIRCUIT_KEYS but not SOURCE_TYPES: {missing_from_types}"

        # Note: SOURCE_TYPES may have additional sources that are state-specific
        # or not yet fully implemented, so we don't check the reverse

    def test_all_source_types_have_at_least_one_source(self):
        """Each SourceType enum should have at least one source."""
        used_types = set(SOURCE_TYPES.values())

        for source_type in SourceType:
            assert (
                source_type.value in used_types
            ), f"SourceType '{source_type.value}' is not used by any source"
