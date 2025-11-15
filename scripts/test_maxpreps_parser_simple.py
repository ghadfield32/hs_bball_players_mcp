"""
Simple Validation of MaxPreps Enhanced Parser

Tests parsing logic without pytest or network requests.

Usage:
    python scripts/test_maxpreps_parser_simple.py

Author: Claude Code
Date: 2025-11-15
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.maxpreps import MaxPrepsDataSource
from src.models import DataQualityFlag


def test_parse_full_stats():
    """Test parsing row with complete player info and stats."""
    print("\n" + "="*80)
    print("TEST 1: Parse Player with Full Stats")
    print("="*80)

    maxpreps = MaxPrepsDataSource()
    data_source = maxpreps.create_data_source_metadata(
        url="https://www.maxpreps.com/ca/basketball/stat-leaders",
        quality_flag=DataQualityFlag.COMPLETE,
        notes="Test data"
    )

    row = {
        "Rank": "1",
        "Player": "John Doe",
        "School": "Lincoln High School",
        "Class": "2025",
        "Pos": "SG",
        "Ht": "6-5",
        "Wt": "185",
        "GP": "25",
        "PPG": "28.5",
        "RPG": "6.2",
        "APG": "4.8",
        "SPG": "2.1",
        "BPG": "0.8",
        "FG%": "52.5",
        "3P%": "38.2",
        "FT%": "85.0",
    }

    player, stats = maxpreps._parse_player_and_stats_from_row(
        row, state="CA", data_source=data_source
    )

    # Validate player
    assert player is not None, "Player should not be None"
    assert player.full_name == "John Doe", f"Expected 'John Doe', got '{player.full_name}'"
    assert player.school_name == "Lincoln High School"
    assert player.grad_year == 2025
    assert player.height_inches == 77  # 6*12 + 5

    # Validate stats
    assert stats is not None, "Stats should not be None"
    assert stats.games_played == 25
    assert abs(stats.points_per_game - 28.5) < 0.1
    assert abs(stats.rebounds_per_game - 6.2) < 0.1
    assert abs(stats.field_goal_percentage - 52.5) < 0.1

    # Validate totals calculated
    assert stats.points == int(28.5 * 25)

    print("✅ All validations passed!")
    print(f"   Player: {player.full_name} ({player.school_name})")
    print(f"   Stats: {stats.points_per_game} PPG, {stats.rebounds_per_game} RPG")
    return True


def test_parse_without_stats():
    """Test parsing row with only player info (no stats)."""
    print("\n" + "="*80)
    print("TEST 2: Parse Player Without Stats")
    print("="*80)

    maxpreps = MaxPrepsDataSource()
    data_source = maxpreps.create_data_source_metadata(
        url="test", quality_flag=DataQualityFlag.COMPLETE, notes="test"
    )

    row = {
        "Player": "Mike Williams",
        "School": "Central High",
        "Class": "2026",
        "Pos": "PF",
        "Ht": "6-9",
        "Wt": "220",
    }

    player, stats = maxpreps._parse_player_and_stats_from_row(
        row, state="FL", data_source=data_source
    )

    assert player is not None, "Player should not be None"
    assert player.full_name == "Mike Williams"
    assert player.height_inches == 81  # 6*12 + 9
    assert player.weight_lbs == 220

    # No stats should return None
    assert stats is None, "Stats should be None when no stats in row"

    print("✅ All validations passed!")
    print(f"   Player: {player.full_name}")
    print(f"   Stats: None (expected)")
    return True


def test_backward_compatibility():
    """Test that tuple unpacking works (backward compatibility)."""
    print("\n" + "="*80)
    print("TEST 3: Backward Compatibility (Tuple Unpacking)")
    print("="*80)

    maxpreps = MaxPrepsDataSource()
    data_source = maxpreps.create_data_source_metadata(
        url="test", quality_flag=DataQualityFlag.COMPLETE, notes="test"
    )

    row = {
        "Player": "Test Player",
        "PPG": "10.0",
    }

    # This should work: player, _ = ...
    player, _ = maxpreps._parse_player_and_stats_from_row(
        row, state="CA", data_source=data_source
    )

    assert player is not None
    assert player.full_name == "Test Player"

    print("✅ Tuple unpacking works!")
    print(f"   Player: {player.full_name}")
    print(f"   Stats: Ignored via _ (backward compatible)")
    return True


def test_various_height_formats():
    """Test parsing different height formats."""
    print("\n" + "="*80)
    print("TEST 4: Various Height Formats")
    print("="*80)

    maxpreps = MaxPrepsDataSource()
    data_source = maxpreps.create_data_source_metadata(
        url="test", quality_flag=DataQualityFlag.COMPLETE, notes="test"
    )

    test_cases = [
        ("6-5", 77),   # Dash format
        ("6'5\"", 77), # Feet-inches format
        ("77", 77),    # Direct inches
    ]

    for height_str, expected_inches in test_cases:
        row = {
            "Player": "Test Player",
            "Ht": height_str,
            "PPG": "10.0",
        }

        player, _ = maxpreps._parse_player_and_stats_from_row(
            row, state="CA", data_source=data_source
        )

        assert player.height_inches == expected_inches, \
            f"Failed for height format: {height_str}, expected {expected_inches}, got {player.height_inches}"

        print(f"   ✅ {height_str} → {player.height_inches} inches")

    print("✅ All height formats parsed correctly!")
    return True


def test_method_exists():
    """Test that search_players_with_stats method exists."""
    print("\n" + "="*80)
    print("TEST 5: New Method Exists")
    print("="*80)

    maxpreps = MaxPrepsDataSource()

    assert hasattr(maxpreps, 'search_players_with_stats'), \
        "search_players_with_stats method should exist"
    assert callable(maxpreps.search_players_with_stats), \
        "search_players_with_stats should be callable"

    print("✅ search_players_with_stats() method exists and is callable!")
    return True


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "#"*80)
    print("# MaxPreps Enhancement 5 - Parser Validation")
    print("#"*80)

    tests = [
        ("Parse Full Stats", test_parse_full_stats),
        ("Parse Without Stats", test_parse_without_stats),
        ("Backward Compatibility", test_backward_compatibility),
        ("Height Format Parsing", test_various_height_formats),
        ("New Method Exists", test_method_exists),
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
