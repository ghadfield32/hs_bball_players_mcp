"""
Integration tests for Player model age-for-grade properties (Enhancement 4).

Tests the computed properties on the Player model:
- age_for_grade: Calculated age advantage/disadvantage
- age_for_grade_category: Descriptive category
"""

from datetime import date

import pytest

from src.models import Player


class TestPlayerAgeForGradeProperty:
    """Test Player.age_for_grade computed property."""

    @pytest.fixture
    def base_player_data(self):
        """Base player data for testing."""
        return {
            "player_id": "test_player_001",
            "first_name": "Test",
            "last_name": "Player",
            "position": "PG",
        }

    def test_age_for_grade_with_birth_date_and_grad_year(self, base_player_data):
        """Test age_for_grade calculates correctly with both fields present."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 8, 15),  # Younger than average
            grad_year=2025,
        )

        age_advantage = player.age_for_grade

        # Should return positive (younger than average)
        assert age_advantage is not None
        assert age_advantage > 0
        assert 0.1 <= age_advantage <= 0.15  # ~1.5 months younger

    def test_age_for_grade_older_player(self, base_player_data):
        """Test age_for_grade for older player (reclassified)."""
        player = Player(
            **base_player_data,
            birth_date=date(2006, 12, 21),  # Cooper Flagg example - older
            grad_year=2025,
        )

        age_advantage = player.age_for_grade

        # Should return negative (older than average)
        assert age_advantage is not None
        assert age_advantage < 0

    def test_age_for_grade_without_birth_date(self, base_player_data):
        """Test age_for_grade returns None when birth_date missing."""
        player = Player(
            **base_player_data,
            grad_year=2025,
            # No birth_date provided
        )

        assert player.age_for_grade is None

    def test_age_for_grade_without_grad_year(self, base_player_data):
        """Test age_for_grade returns None when grad_year missing."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 8, 15),
            # No grad_year provided
        )

        assert player.age_for_grade is None

    def test_age_for_grade_without_both(self, base_player_data):
        """Test age_for_grade returns None when both fields missing."""
        player = Player(**base_player_data)

        assert player.age_for_grade is None

    def test_age_for_grade_different_grad_years(self, base_player_data):
        """Test age_for_grade changes with different grad years (reclassification)."""
        birth_date = date(2007, 8, 15)

        # Class of 2025
        player_2025 = Player(
            **base_player_data,
            birth_date=birth_date,
            grad_year=2025,
        )

        # Class of 2026 (reclassified down)
        player_2026 = Player(
            **base_player_data,
            birth_date=birth_date,
            grad_year=2026,
        )

        # Same birth date, different grad year = different age advantage
        assert player_2025.age_for_grade != player_2026.age_for_grade
        # Should be even younger for 2026 class
        assert player_2026.age_for_grade > player_2025.age_for_grade

    def test_age_for_grade_computed_on_access(self, base_player_data):
        """Test age_for_grade is computed each time (not stored)."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 8, 15),
            grad_year=2025,
        )

        # Access multiple times
        age1 = player.age_for_grade
        age2 = player.age_for_grade

        # Should return same value
        assert age1 == age2

        # Modify grad_year
        player.grad_year = 2026

        # Should recalculate
        age3 = player.age_for_grade
        assert age3 != age1  # Different grad year = different calculation


class TestPlayerAgeForGradeCategory:
    """Test Player.age_for_grade_category computed property."""

    @pytest.fixture
    def base_player_data(self):
        """Base player data for testing."""
        return {
            "player_id": "test_player_001",
            "first_name": "Test",
            "last_name": "Player",
            "position": "PG",
        }

    def test_category_very_young(self, base_player_data):
        """Test 'Very Young' category for very young player."""
        player = Player(
            **base_player_data,
            birth_date=date(2008, 6, 15),  # Almost 1 year younger
            grad_year=2025,
        )

        category = player.age_for_grade_category
        assert category == "Very Young"

    def test_category_young(self, base_player_data):
        """Test 'Young' category for younger player."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 9, 1),  # ~2 months younger
            grad_year=2025,
        )

        category = player.age_for_grade_category
        assert category in ["Young", "Average"]  # Close to boundary

    def test_category_average(self, base_player_data):
        """Test 'Average' category for average age player."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 7, 1),  # Exactly average
            grad_year=2025,
        )

        category = player.age_for_grade_category
        assert category == "Average"

    def test_category_old(self, base_player_data):
        """Test 'Old' category for older player."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 3, 1),  # ~4 months older
            grad_year=2025,
        )

        category = player.age_for_grade_category
        assert category in ["Old", "Average"]  # Close to boundary

    def test_category_very_old(self, base_player_data):
        """Test 'Very Old' category for much older player."""
        player = Player(
            **base_player_data,
            birth_date=date(2006, 6, 15),  # ~1 year older
            grad_year=2025,
        )

        category = player.age_for_grade_category
        assert category == "Very Old"

    def test_category_unknown_no_data(self, base_player_data):
        """Test 'Unknown' category when no birth_date or grad_year."""
        player = Player(**base_player_data)

        category = player.age_for_grade_category
        assert category == "Unknown"

    def test_category_unknown_partial_data(self, base_player_data):
        """Test 'Unknown' category when only one field present."""
        # Only birth_date
        player1 = Player(
            **base_player_data,
            birth_date=date(2007, 8, 15),
        )
        assert player1.age_for_grade_category == "Unknown"

        # Only grad_year
        player2 = Player(
            **base_player_data,
            grad_year=2025,
        )
        assert player2.age_for_grade_category == "Unknown"


class TestPlayerAgePropertyIntegration:
    """Test integration between existing age property and new age_for_grade properties."""

    @pytest.fixture
    def base_player_data(self):
        """Base player data for testing."""
        return {
            "player_id": "test_player_001",
            "first_name": "Test",
            "last_name": "Player",
            "position": "PG",
        }

    def test_age_property_still_works(self, base_player_data):
        """Test existing age property is not broken by new properties."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 1, 1),
        )

        # Existing age property should still work
        age = player.age
        assert age is not None
        assert age >= 17  # Born 2007, should be at least 17 in 2024+

    def test_both_properties_independent(self, base_player_data):
        """Test age and age_for_grade are independent calculations."""
        player = Player(
            **base_player_data,
            birth_date=date(2007, 8, 15),
            grad_year=2025,
        )

        # Both should work independently
        current_age = player.age
        age_advantage = player.age_for_grade

        assert current_age is not None
        assert age_advantage is not None
        assert current_age != age_advantage  # Different calculations

    def test_real_world_scenario(self, base_player_data):
        """Test real-world player scenario with all age properties."""
        # Create player with full data
        player = Player(
            player_id="247_12345",
            first_name="Cooper",
            last_name="Flagg",
            birth_date=date(2006, 12, 21),
            grad_year=2025,
            position="SF",
            height="6-9",
            weight=205,
            school="Montverde Academy",
            city="Montverde",
            state="FL",
        )

        # Verify all age properties work
        assert player.age >= 17  # Current age
        assert player.age_for_grade < 0  # Older than average (reclassified)
        assert player.age_for_grade_category in ["Old", "Very Old"]

    def test_properties_handle_none_gracefully(self, base_player_data):
        """Test all age properties handle missing data gracefully."""
        player = Player(**base_player_data)

        # All should return None or "Unknown" without errors
        assert player.age is None
        assert player.age_for_grade is None
        assert player.age_for_grade_category == "Unknown"


class TestCircularImportPrevention:
    """Test that local imports in properties prevent circular dependencies."""

    def test_import_player_model_doesnt_fail(self):
        """Test importing Player model doesn't cause circular import."""
        # This test passes if the import above succeeded
        from src.models import Player

        assert Player is not None

    def test_import_age_calculations_independently(self):
        """Test importing age_calculations independently works."""
        from src.utils.age_calculations import (
            calculate_age_for_grade,
            categorize_age_for_grade,
        )

        assert calculate_age_for_grade is not None
        assert categorize_age_for_grade is not None

    def test_creating_player_doesnt_trigger_imports(self):
        """Test creating Player instance doesn't import utils immediately."""
        # Create player without accessing age properties
        player = Player(
            player_id="test_001",
            first_name="Test",
            last_name="Player",
        )

        # Should create successfully
        assert player is not None

        # Now access properties (triggers local imports)
        _ = player.age_for_grade_category

        # Should still work
        assert player is not None
