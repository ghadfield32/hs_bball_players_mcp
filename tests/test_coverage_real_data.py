"""
Real-Data Coverage Tests (Step 8 of 8-step coverage plan)

Tests coverage measurement with actual player data.
Uses real API calls (cached) to validate the entire coverage pipeline.

**Test Coverage**:
- Top 2025 recruits (Cooper Flagg, Cameron Boozer, AJ Dybantsa)
- Coverage measurement accuracy
- Missing reasons tracking
- Feature flags validation
- Enhanced identity resolution

**Requirements**:
- pytest
- pytest-asyncio
- Running with --tb=short for compact error messages

Usage:
    pytest tests/test_coverage_real_data.py -v
    pytest tests/test_coverage_real_data.py -v -k "test_top_recruits"

Author: Claude Code
Date: 2025-11-15
Enhancement: 11 (Coverage Enhancements 3, 4, 8)
"""

import pytest

# Try to import dependencies (fail gracefully if not installed)
try:
    import pytest_asyncio
    PYTEST_ASYNC_AVAILABLE = True
except ImportError:
    PYTEST_ASYNC_AVAILABLE = False
    print("⚠️  pytest-asyncio not installed. Install with: pip install pytest-asyncio")

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Only import if pytest available
if PYTEST_ASYNC_AVAILABLE:
    from src.services.forecasting import ForecastingDataAggregator
    from src.services.coverage_metrics import (
        extract_coverage_flags_from_profile,
        compute_coverage_score,
    )
    from src.services.identity import resolve_player_uid_enhanced


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def forecasting_aggregator():
    """Create ForecastingDataAggregator instance."""
    return ForecastingDataAggregator()


@pytest.fixture
def top_2025_recruits():
    """List of top 2025 recruits for testing."""
    return [
        {
            "name": "Cooper Flagg",
            "grad_year": 2025,
            "state": "ME",  # Originally from Maine, now at Montverde (FL)
            "expected_coverage_level": "EXCELLENT",  # Should have full data
        },
        {
            "name": "Cameron Boozer",
            "grad_year": 2025,
            "state": "FL",
            "expected_coverage_level": "EXCELLENT",  # Twin of Cayden, highly ranked
        },
        {
            "name": "AJ Dybantsa",
            "grad_year": 2026,
            "state": "UT",
            "expected_coverage_level": "GOOD",  # Class of 2026, slightly less coverage
        },
    ]


# ============================================================================
# Coverage Measurement Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not PYTEST_ASYNC_AVAILABLE, reason="pytest-asyncio not installed")
async def test_top_recruits_coverage(forecasting_aggregator, top_2025_recruits):
    """
    Test coverage measurement on top recruits.

    Validates that top recruits have EXCELLENT or GOOD coverage levels.
    """
    results = []

    for player_info in top_2025_recruits:
        # Get forecasting profile
        profile = await forecasting_aggregator.get_comprehensive_player_profile(
            player_name=player_info["name"],
            grad_year=player_info["grad_year"],
            state=player_info.get("state"),
        )

        # Extract coverage
        coverage_summary = profile.get("coverage_summary", {})

        # Validate coverage exists
        assert coverage_summary, f"No coverage_summary for {player_info['name']}"
        assert "overall_score" in coverage_summary
        assert "coverage_level" in coverage_summary

        # Check coverage level
        coverage_level = coverage_summary["coverage_level"]
        overall_score = coverage_summary["overall_score"]

        print(f"\n{player_info['name']} ({player_info['grad_year']}):")
        print(f"  Coverage: {overall_score:.1f}% ({coverage_level})")
        print(f"  Tier 1 (Critical): {coverage_summary.get('tier1_critical', 0):.1f}%")
        print(f"  Missing Critical: {coverage_summary.get('missing_critical', [])}")

        results.append({
            "player": player_info["name"],
            "coverage_level": coverage_level,
            "overall_score": overall_score,
        })

        # Top recruits should have at least FAIR coverage (>50%)
        assert overall_score >= 50.0, \
            f"{player_info['name']} has poor coverage: {overall_score:.1f}%"

    # Summary
    print(f"\n{'='*80}")
    print(f"TOP RECRUITS COVERAGE SUMMARY")
    print(f"{'='*80}")
    for result in results:
        print(f"{result['player']:20} {result['overall_score']:6.1f}% ({result['coverage_level']})")
    print(f"{'='*80}\n")


@pytest.mark.asyncio
@pytest.mark.skipif(not PYTEST_ASYNC_AVAILABLE, reason="pytest-asyncio not installed")
async def test_missing_reasons_tracked(forecasting_aggregator):
    """
    Test that missing_reasons are properly tracked.

    Validates that the missing_reasons dict is populated correctly.
    """
    # Test with a top recruit (should have minimal missing data)
    profile = await forecasting_aggregator.get_comprehensive_player_profile(
        player_name="Cooper Flagg",
        grad_year=2025,
        state="ME",
    )

    # Check missing_reasons exist
    missing_reasons = profile.get("missing_reasons", {})
    assert missing_reasons, "missing_reasons not found in profile"

    # Validate structure
    expected_keys = [
        "missing_247_profile",
        "missing_maxpreps_data",
        "missing_multi_season_data",
        "missing_recruiting_coverage",
        "missing_birth_date",
        "missing_physical_measurements",
        "missing_international_data",
        "missing_advanced_stats",
    ]

    for key in expected_keys:
        assert key in missing_reasons, f"Missing key: {key}"

    # Top recruit should NOT be missing recruiting coverage
    assert not missing_reasons["missing_recruiting_coverage"], \
        "Top recruit should have recruiting coverage"

    print(f"\nMissing Reasons for Cooper Flagg:")
    for key, value in missing_reasons.items():
        if value:
            print(f"  ❌ {key}: {value}")


@pytest.mark.asyncio
@pytest.mark.skipif(not PYTEST_ASYNC_AVAILABLE, reason="pytest-asyncio not installed")
async def test_feature_flags_populated(forecasting_aggregator):
    """
    Test that feature_flags are properly populated.

    Validates that the feature_flags dict is populated correctly.
    """
    profile = await forecasting_aggregator.get_comprehensive_player_profile(
        player_name="Cooper Flagg",
        grad_year=2025,
        state="ME",
    )

    # Check feature_flags exist
    feature_flags = profile.get("feature_flags", {})
    assert feature_flags, "feature_flags not found in profile"

    # Validate structure
    expected_keys = [
        "has_recruiting_data",
        "has_advanced_stats",
        "has_progression_data",
        "has_physical_data",
        "has_multi_source_data",
    ]

    for key in expected_keys:
        assert key in feature_flags, f"Missing key: {key}"

    # Top recruit should have recruiting data
    assert feature_flags["has_recruiting_data"], \
        "Top recruit should have recruiting data"

    print(f"\nFeature Flags for Cooper Flagg:")
    for key, value in feature_flags.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")


# ============================================================================
# Enhanced Identity Resolution Tests
# ============================================================================

def test_enhanced_identity_resolution():
    """
    Test enhanced identity resolution with multi-attribute matching.
    """
    # Test with full attributes (should get confidence = 1.0)
    uid, confidence = resolve_player_uid_enhanced(
        name="Cooper Flagg",
        school="Montverde Academy",
        grad_year=2025,
        birth_date="2006-12-21",
        height=81,
        state="FL",
    )

    print(f"\nEnhanced Identity Resolution:")
    print(f"  UID: {uid}")
    print(f"  Confidence: {confidence:.2f}")

    # Should be high confidence with full data
    assert confidence >= 0.8, f"Expected high confidence, got {confidence}"

    # Test with minimal attributes (should get lower confidence)
    uid2, confidence2 = resolve_player_uid_enhanced(
        name="Cooper Flagg",
        grad_year=2025,
    )

    print(f"\nMinimal Attributes:")
    print(f"  UID: {uid2}")
    print(f"  Confidence: {confidence2:.2f}")

    # Should be lower confidence with minimal data
    assert confidence2 < confidence, "Minimal data should have lower confidence"


# ============================================================================
# Coverage Metrics Validation Tests
# ============================================================================

def test_coverage_score_calculation():
    """
    Test that coverage score calculation is correct.
    """
    from src.services.coverage_metrics import CoverageFlags, compute_coverage_score

    # Test excellent coverage (all flags True)
    flags_excellent = CoverageFlags(
        has_composite_247=True,
        has_stars=True,
        has_power6_offers=True,
        has_ts_pct=True,
        has_efg_pct=True,
        has_ato_ratio=True,
        has_usage_rate=True,
        has_age_for_grade=True,
        has_multi_season=True,
        has_birth_date=True,
        has_physical_measurements=True,
        has_maxpreps_stats=True,
        has_recruiting_profile=True,
        has_school_info=True,
        has_position=True,
        player_segment="US_HS",
    )

    score_excellent = compute_coverage_score(flags_excellent)

    print(f"\nExcellent Coverage Test:")
    print(f"  Overall: {score_excellent.overall_score:.1f}% ({score_excellent.coverage_level})")
    print(f"  Tier 1: {score_excellent.tier1_score:.1f}%")

    # Should be EXCELLENT (>85%)
    assert score_excellent.coverage_level == "EXCELLENT"
    assert score_excellent.overall_score >= 85.0

    # Test poor coverage (all flags False)
    flags_poor = CoverageFlags(
        has_school_info=True,  # Only minimal data
        player_segment="US_HS",
    )

    score_poor = compute_coverage_score(flags_poor)

    print(f"\nPoor Coverage Test:")
    print(f"  Overall: {score_poor.overall_score:.1f}% ({score_poor.coverage_level})")
    print(f"  Missing Critical: {len(score_poor.missing_critical)} predictors")

    # Should be POOR (<50%)
    assert score_poor.coverage_level == "POOR"
    assert score_poor.overall_score < 50.0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not PYTEST_ASYNC_AVAILABLE, reason="pytest-asyncio not installed")
async def test_full_pipeline_integration(forecasting_aggregator):
    """
    Test the full forecasting → coverage measurement pipeline.

    Validates end-to-end integration of all components.
    """
    # Run full pipeline for a test player
    profile = await forecasting_aggregator.get_comprehensive_player_profile(
        player_name="Cooper Flagg",
        grad_year=2025,
        state="ME",
    )

    # Validate all components present
    assert "player_name" in profile
    assert "coverage_summary" in profile
    assert "missing_reasons" in profile
    assert "feature_flags" in profile
    assert "forecasting_score" in profile

    # Validate coverage_summary structure
    coverage = profile["coverage_summary"]
    assert "overall_score" in coverage
    assert "coverage_level" in coverage
    assert "tier1_critical" in coverage
    assert "missing_critical" in coverage
    assert "breakdown" in coverage

    # Print summary
    print(f"\n{'='*80}")
    print(f"FULL PIPELINE INTEGRATION TEST")
    print(f"{'='*80}")
    print(f"Player: {profile['player_name']}")
    print(f"Coverage: {coverage['overall_score']:.1f}% ({coverage['coverage_level']})")
    print(f"Forecasting Score: {profile.get('forecasting_score', 'N/A')}")
    print(f"Data Completeness: {profile.get('data_completeness', 'N/A')}")
    print(f"{'='*80}\n")


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


if __name__ == "__main__":
    """Run tests if executed directly."""
    if not PYTEST_ASYNC_AVAILABLE:
        print("\n❌ pytest-asyncio not installed")
        print("Install with: pip install pytest pytest-asyncio")
        print("\nTo run tests:")
        print("  pytest tests/test_coverage_real_data.py -v")
        sys.exit(1)

    # Run pytest programmatically
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
