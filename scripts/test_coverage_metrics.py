#!/usr/bin/env python3
"""
Simple validation of Coverage Metrics System

Tests coverage calculation logic without network requests.

Usage:
    python scripts/test_coverage_metrics.py

Author: Claude Code
Date: 2025-11-15
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.coverage_metrics import (
    CoverageFlags,
    compute_coverage_score,
    extract_coverage_flags_from_profile,
)


def test_excellent_coverage():
    """Test player with excellent coverage (>85%)."""
    print("\n" + "="*80)
    print("TEST 1: Excellent Coverage (All Critical Predictors)")
    print("="*80)

    flags = CoverageFlags(
        # Tier 1: Critical (60%)
        has_composite_247=True,
        has_stars=True,
        has_power6_offers=True,
        has_ts_pct=True,
        has_efg_pct=True,
        has_ato_ratio=True,
        has_usage_rate=True,
        # Tier 2: Important (30%)
        has_age_for_grade=True,
        has_multi_season=True,
        has_birth_date=True,
        has_physical_measurements=True,
        has_maxpreps_stats=True,
        has_recruiting_profile=True,
        # Tier 3: Supplemental (10%)
        has_school_info=True,
        has_position=True,
        # Context
        player_segment="US_HS",
        total_data_sources=10,
        total_stats_seasons=3,
    )

    score = compute_coverage_score(flags)

    print(f"Overall Score: {score.overall_score:.1f}% ({score.coverage_level})")
    print(f"Tier 1 (Critical): {score.tier1_score:.1f}%")
    print(f"Tier 2 (Important): {score.tier2_score:.1f}%")
    print(f"Tier 3 (Supplemental): {score.tier3_score:.1f}%")
    print(f"Missing Critical: {score.missing_critical}")

    assert score.coverage_level == "EXCELLENT", f"Expected EXCELLENT, got {score.coverage_level}"
    assert score.overall_score >= 85, f"Expected >=85%, got {score.overall_score}"
    assert len(score.missing_critical) == 0, "Should have no missing critical predictors"

    print("✅ PASS - Excellent coverage validated!")
    return True


def test_poor_coverage():
    """Test player with poor coverage (<50%)."""
    print("\n" + "="*80)
    print("TEST 2: Poor Coverage (Missing Critical Predictors)")
    print("="*80)

    flags = CoverageFlags(
        # Only basic info, no critical predictors
        has_school_info=True,
        has_position=True,
        player_segment="US_HS",
        total_data_sources=1,
        total_stats_seasons=1,
        missing_247_profile=True,
        missing_maxpreps_data=True,
        missing_multi_season_data=True,
    )

    score = compute_coverage_score(flags)

    print(f"Overall Score: {score.overall_score:.1f}% ({score.coverage_level})")
    print(f"Tier 1 (Critical): {score.tier1_score:.1f}%")
    print(f"Missing Critical: {score.missing_critical}")
    print(f"Missing Important: {score.missing_important}")

    assert score.coverage_level == "POOR", f"Expected POOR, got {score.coverage_level}"
    assert score.overall_score < 50, f"Expected <50%, got {score.overall_score}"
    assert len(score.missing_critical) > 0, "Should have missing critical predictors"

    print("✅ PASS - Poor coverage validated!")
    return True


def test_partial_coverage():
    """Test player with partial coverage (50-70%)."""
    print("\n" + "="*80)
    print("TEST 3: Partial Coverage (Some Critical, Some Missing)")
    print("="*80)

    flags = CoverageFlags(
        # Some recruiting data
        has_stars=True,
        has_recruiting_profile=True,
        # Some stats
        has_ts_pct=True,
        has_efg_pct=True,
        # Physical
        has_physical_measurements=True,
        has_position=True,
        has_school_info=True,
        # Missing
        missing_247_profile=True,  # No composite rating
        missing_multi_season_data=True,  # Only 1 season
        player_segment="US_HS",
        total_data_sources=3,
        total_stats_seasons=1,
    )

    score = compute_coverage_score(flags)

    print(f"Overall Score: {score.overall_score:.1f}% ({score.coverage_level})")
    print(f"Recruiting: {score.recruiting_score:.1f}% | Efficiency: {score.efficiency_score:.1f}%")
    print(f"Missing Critical: {score.missing_critical}")

    assert score.coverage_level in ["FAIR", "GOOD"], f"Expected FAIR or GOOD, got {score.coverage_level}"
    assert 40 <= score.overall_score <= 80, f"Expected 40-80%, got {score.overall_score}"

    print("✅ PASS - Partial coverage validated!")
    return True


def test_extract_from_profile():
    """Test extraction from forecasting profile."""
    print("\n" + "="*80)
    print("TEST 4: Extract Coverage from Forecasting Profile")
    print("="*80)

    # Mock profile from ForecastingDataAggregator
    profile = {
        "player_name": "Test Player",
        "grad_year": 2025,
        "state": "CA",
        "country": "USA",
        # Critical predictors
        "composite_247_rating": 0.98,
        "stars_247": 5,
        "power_6_offer_count": 12,
        "best_ts_pct": 0.625,
        "best_efg_pct": 0.580,
        "best_ato_ratio": 2.5,
        # Important features
        "age_for_grade": -0.5,
        "birth_date": "2006-03-15",
        "height": 79,
        "weight": 210,
        # Context
        "school_name": "Test High School",
        "position": "PG",
        "circuits_played": ["EYBL", "Peach Jam"],
        "raw_stats": [],  # Will test multi-season separately
        "raw_players": [],
    }

    flags = extract_coverage_flags_from_profile(profile)

    print(f"Player Segment: {flags.player_segment}")
    print(f"Has 247 Composite: {flags.has_composite_247}")
    print(f"Has Stars: {flags.has_stars}")
    print(f"Has Power 6 Offers: {flags.has_power6_offers}")
    print(f"Has TS%: {flags.has_ts_pct}")
    print(f"Has Age-for-Grade: {flags.has_age_for_grade}")

    assert flags.player_segment == "US_HS", "Should be US_HS segment"
    assert flags.has_composite_247 is True, "Should have 247 composite"
    assert flags.has_stars is True, "Should have stars"
    assert flags.has_power6_offers is True, "Should have offers"
    assert flags.has_ts_pct is True, "Should have TS%"
    assert flags.has_age_for_grade is True, "Should have age-for-grade"

    score = compute_coverage_score(flags)
    print(f"\nCoverage Score: {score.overall_score:.1f}% ({score.coverage_level})")

    print("✅ PASS - Profile extraction validated!")
    return True


def test_weighted_scoring():
    """Test that weights match forecasting importance."""
    print("\n" + "="*80)
    print("TEST 5: Weighted Scoring Matches Forecasting Importance")
    print("="*80)

    # Test: 247 composite (15%) should be worth more than TS% (8%)
    flags_247 = CoverageFlags(has_composite_247=True)
    score_247 = compute_coverage_score(flags_247)

    flags_ts = CoverageFlags(has_ts_pct=True)
    score_ts = compute_coverage_score(flags_ts)

    print(f"247 Composite alone: {score_247.overall_score:.1f}%")
    print(f"TS% alone: {score_ts.overall_score:.1f}%")

    assert score_247.overall_score > score_ts.overall_score, \
        "247 composite (15%) should score higher than TS% (8%)"

    # Test: All Tier 1 (60%) should score much higher than all Tier 3 (10%)
    flags_tier1 = CoverageFlags(
        has_composite_247=True,
        has_stars=True,
        has_power6_offers=True,
        has_ts_pct=True,
        has_efg_pct=True,
        has_ato_ratio=True,
        has_usage_rate=True,
    )
    score_tier1 = compute_coverage_score(flags_tier1)

    flags_tier3 = CoverageFlags(
        has_school_info=True,
        has_position=True,
    )
    score_tier3 = compute_coverage_score(flags_tier3)

    print(f"\nTier 1 complete: {score_tier1.overall_score:.1f}%")
    print(f"Tier 3 complete: {score_tier3.overall_score:.1f}%")

    assert score_tier1.overall_score > 50, "Tier 1 should be >50%"
    assert score_tier3.overall_score < 15, "Tier 3 should be <15%"

    print("✅ PASS - Weighted scoring validated!")
    return True


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "#"*80)
    print("# Coverage Metrics Validation")
    print("#"*80)

    tests = [
        ("Excellent Coverage", test_excellent_coverage),
        ("Poor Coverage", test_poor_coverage),
        ("Partial Coverage", test_partial_coverage),
        ("Extract from Profile", test_extract_from_profile),
        ("Weighted Scoring", test_weighted_scoring),
    ]

    results = []
    passed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                results.append((test_name, True))
                passed += 1
            else:
                results.append((test_name, False))
        except Exception as e:
            print(f"\n❌ {test_name} FAILED:")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "#"*80)
    print("# TEST SUMMARY")
    print("#"*80 + "\n")

    print(f"Tests Passed: {passed}/{len(tests)}")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "#"*80 + "\n")

    return passed == len(tests)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
