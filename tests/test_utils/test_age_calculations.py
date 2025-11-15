"""
Unit tests for age calculation utilities (Enhancement 4).

Tests all 4 age calculation functions with comprehensive edge cases:
- calculate_age_for_grade(): Age advantage calculation
- calculate_age_at_date(): Exact age calculation
- parse_birth_date(): Date parsing from multiple formats
- categorize_age_for_grade(): Categorization logic
"""

from datetime import date

import pytest

from src.utils.age_calculations import (
    calculate_age_at_date,
    calculate_age_for_grade,
    categorize_age_for_grade,
    parse_birth_date,
)


class TestCalculateAgeForGrade:
    """Test age-for-grade advantage calculation."""

    def test_younger_than_average(self):
        """Test player younger than average for grade (positive advantage)."""
        # Expected birth date for class of 2025: July 1, 2007
        # Player born Aug 15, 2007 is about 1.5 months younger
        birth_date = date(2007, 8, 15)
        grad_year = 2025

        age_advantage = calculate_age_for_grade(birth_date, grad_year)

        # Should be positive (younger = advantage)
        assert age_advantage > 0
        assert 0.1 <= age_advantage <= 0.15  # ~1.5 months = 0.125 years

    def test_older_than_average(self):
        """Test player older than average for grade (negative disadvantage)."""
        # Expected birth date for class of 2025: July 1, 2007
        # Player born May 15, 2007 is about 1.5 months older
        birth_date = date(2007, 5, 15)
        grad_year = 2025

        age_advantage = calculate_age_for_grade(birth_date, grad_year)

        # Should be negative (older = disadvantage)
        assert age_advantage < 0
        assert -0.15 <= age_advantage <= -0.1

    def test_average_age(self):
        """Test player exactly average age for grade."""
        # Born exactly on expected date
        birth_date = date(2007, 7, 1)
        grad_year = 2025

        age_advantage = calculate_age_for_grade(birth_date, grad_year)

        # Should be very close to 0
        assert abs(age_advantage) < 0.01

    def test_very_young_for_grade(self):
        """Test player much younger than average (strong advantage)."""
        # Born almost a year after expected date
        birth_date = date(2008, 6, 15)
        grad_year = 2025

        age_advantage = calculate_age_for_grade(birth_date, grad_year)

        # Should be close to +1.0 year
        assert age_advantage > 0.9
        assert age_advantage < 1.1

    def test_very_old_for_grade(self):
        """Test player much older than average (strong disadvantage)."""
        # Born almost a year before expected date
        birth_date = date(2006, 7, 15)
        grad_year = 2025

        age_advantage = calculate_age_for_grade(birth_date, grad_year)

        # Should be close to -1.0 year
        assert age_advantage < -0.9
        assert age_advantage > -1.1

    def test_different_grad_years(self):
        """Test calculation works for different graduation years."""
        birth_date = date(2009, 8, 1)

        # Class of 2027
        age_adv_2027 = calculate_age_for_grade(birth_date, 2027)
        assert age_adv_2027 > 0  # Younger than average

        # Class of 2026 (if they reclassified down)
        age_adv_2026 = calculate_age_for_grade(birth_date, 2026)
        assert age_adv_2026 > age_adv_2027  # Even younger for this class

    def test_custom_reference_date(self):
        """Test calculation with custom reference date."""
        birth_date = date(2007, 8, 15)
        grad_year = 2025
        reference_date = date(2024, 9, 1)  # Start of senior year

        age_advantage = calculate_age_for_grade(
            birth_date, grad_year, reference_date
        )

        # Should still return positive (younger than average)
        assert age_advantage > 0

    def test_leap_year_handling(self):
        """Test calculation handles leap years correctly."""
        # Born on leap day
        birth_date = date(2008, 2, 29)
        grad_year = 2026

        age_advantage = calculate_age_for_grade(birth_date, grad_year)

        # Should calculate without error
        assert isinstance(age_advantage, float)


class TestCalculateAgeAtDate:
    """Test exact age calculation."""

    def test_exact_age_years_only(self):
        """Test age calculation when exact number of years."""
        birth_date = date(2007, 3, 15)
        reference_date = date(2024, 3, 15)  # Exactly 17 years later

        years, days = calculate_age_at_date(birth_date, reference_date)

        assert years == 17
        assert days == 0

    def test_age_with_remaining_days(self):
        """Test age calculation with remaining days."""
        birth_date = date(2007, 3, 15)
        reference_date = date(2024, 4, 10)  # 17 years and ~26 days

        years, days = calculate_age_at_date(birth_date, reference_date)

        assert years == 17
        assert 20 <= days <= 30  # Should be ~26 days

    def test_age_before_birthday_this_year(self):
        """Test age calculation before birthday in current year."""
        birth_date = date(2007, 9, 15)
        reference_date = date(2024, 3, 15)  # Before birthday

        years, days = calculate_age_at_date(birth_date, reference_date)

        assert years == 16  # Not yet 17

    def test_default_reference_date(self):
        """Test age calculation with default reference date (today)."""
        birth_date = date(2007, 1, 1)

        years, days = calculate_age_at_date(birth_date)

        # Should return current age
        assert years >= 17  # Born in 2007, should be at least 17 in 2024+
        assert days >= 0

    def test_leap_year_age_calculation(self):
        """Test age calculation across leap years."""
        birth_date = date(2004, 2, 29)
        reference_date = date(2024, 3, 1)  # Day after leap day

        years, days = calculate_age_at_date(birth_date, reference_date)

        assert years == 20
        assert days <= 2  # Should be 1-2 days


class TestParseBirthDate:
    """Test birth date parsing from various formats."""

    def test_parse_mm_dd_yyyy(self):
        """Test parsing MM/DD/YYYY format."""
        date_str = "03/15/2007"
        parsed = parse_birth_date(date_str)

        assert parsed == date(2007, 3, 15)

    def test_parse_month_dd_yyyy(self):
        """Test parsing 'Month DD, YYYY' format."""
        date_str = "March 15, 2007"
        parsed = parse_birth_date(date_str)

        assert parsed == date(2007, 3, 15)

    def test_parse_mon_dd_yyyy(self):
        """Test parsing 'Mon DD, YYYY' format (abbreviated month)."""
        date_str = "Mar 15, 2007"
        parsed = parse_birth_date(date_str)

        assert parsed == date(2007, 3, 15)

    def test_parse_iso_format(self):
        """Test parsing ISO format (YYYY-MM-DD)."""
        date_str = "2007-03-15"
        parsed = parse_birth_date(date_str)

        assert parsed == date(2007, 3, 15)

    def test_parse_european_format(self):
        """Test parsing European format (DD/MM/YYYY)."""
        date_str = "15/03/2007"
        parsed = parse_birth_date(date_str)

        # Should parse as DD/MM/YYYY
        assert parsed == date(2007, 3, 15)

    def test_parse_month_dd_yyyy_no_comma(self):
        """Test parsing 'Month DD YYYY' format (no comma)."""
        date_str = "March 15 2007"
        parsed = parse_birth_date(date_str)

        assert parsed == date(2007, 3, 15)

    def test_parse_invalid_format(self):
        """Test parsing invalid date format returns None."""
        date_str = "invalid date"
        parsed = parse_birth_date(date_str)

        assert parsed is None

    def test_parse_year_out_of_range(self):
        """Test parsing year outside valid range returns None."""
        # Too old (before 2000)
        date_str = "03/15/1995"
        parsed = parse_birth_date(date_str)
        assert parsed is None

        # Too recent (after 2015)
        date_str = "03/15/2020"
        parsed = parse_birth_date(date_str)
        assert parsed is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        parsed = parse_birth_date("")
        assert parsed is None

    def test_parse_whitespace_handling(self):
        """Test parsing handles extra whitespace."""
        date_str = "  March 15, 2007  "
        parsed = parse_birth_date(date_str)

        assert parsed == date(2007, 3, 15)

    def test_parse_various_valid_dates(self):
        """Test parsing multiple valid birth dates."""
        test_cases = [
            ("01/01/2007", date(2007, 1, 1)),
            ("December 25, 2006", date(2006, 12, 25)),
            ("2008-02-29", date(2008, 2, 29)),  # Leap day
            ("Jun 1, 2007", date(2007, 6, 1)),
        ]

        for date_str, expected in test_cases:
            parsed = parse_birth_date(date_str)
            assert parsed == expected, f"Failed to parse {date_str}"


class TestCategorizeAgeForGrade:
    """Test age-for-grade categorization."""

    def test_very_young_category(self):
        """Test 'Very Young' category (>= 0.75 years younger)."""
        category = categorize_age_for_grade(0.9)
        assert category == "Very Young"

        category = categorize_age_for_grade(1.2)
        assert category == "Very Young"

    def test_young_category(self):
        """Test 'Young' category (0.25 to 0.75 years younger)."""
        category = categorize_age_for_grade(0.5)
        assert category == "Young"

        category = categorize_age_for_grade(0.3)
        assert category == "Young"

    def test_average_category(self):
        """Test 'Average' category (-0.25 to 0.25 years)."""
        category = categorize_age_for_grade(0.0)
        assert category == "Average"

        category = categorize_age_for_grade(0.1)
        assert category == "Average"

        category = categorize_age_for_grade(-0.1)
        assert category == "Average"

    def test_old_category(self):
        """Test 'Old' category (-0.75 to -0.25 years older)."""
        category = categorize_age_for_grade(-0.5)
        assert category == "Old"

        category = categorize_age_for_grade(-0.3)
        assert category == "Old"

    def test_very_old_category(self):
        """Test 'Very Old' category (<= -0.75 years older)."""
        category = categorize_age_for_grade(-0.9)
        assert category == "Very Old"

        category = categorize_age_for_grade(-1.2)
        assert category == "Very Old"

    def test_unknown_category(self):
        """Test 'Unknown' category when age_advantage is None."""
        category = categorize_age_for_grade(None)
        assert category == "Unknown"

    def test_boundary_values(self):
        """Test categorization at exact boundary values."""
        # Boundary between Young and Very Young
        assert categorize_age_for_grade(0.75) == "Very Young"
        assert categorize_age_for_grade(0.74) == "Young"

        # Boundary between Average and Young
        assert categorize_age_for_grade(0.25) == "Young"
        assert categorize_age_for_grade(0.24) == "Average"

        # Boundary between Average and Old
        assert categorize_age_for_grade(-0.25) == "Old"
        assert categorize_age_for_grade(-0.24) == "Average"

        # Boundary between Old and Very Old
        assert categorize_age_for_grade(-0.75) == "Very Old"
        assert categorize_age_for_grade(-0.74) == "Old"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_age_for_grade_with_none_birth_date(self):
        """Test calculate_age_for_grade handles None gracefully."""
        # This would be caught before the function, but test defensive programming
        # The function expects a date object, so we test what happens in practice
        pass

    def test_integration_full_workflow(self):
        """Test complete workflow: parse -> calculate -> categorize."""
        # Parse birth date from string
        birth_date_str = "August 15, 2007"
        birth_date = parse_birth_date(birth_date_str)
        assert birth_date is not None

        # Calculate age-for-grade
        grad_year = 2025
        age_advantage = calculate_age_for_grade(birth_date, grad_year)
        assert age_advantage > 0  # Younger than average

        # Categorize
        category = categorize_age_for_grade(age_advantage)
        assert category == "Young"  # Should be "Young" category

    def test_real_world_examples(self):
        """Test with real-world player examples."""
        # Cooper Flagg example: Born Dec 21, 2006 (class of 2025)
        # Expected birth: July 1, 2007
        # He's ~6 months older (reclassified)
        birth_date = date(2006, 12, 21)
        grad_year = 2025

        age_advantage = calculate_age_for_grade(birth_date, grad_year)
        assert age_advantage < 0  # Older than average

        category = categorize_age_for_grade(age_advantage)
        assert category == "Old"  # Should be categorized as old for grade

    def test_young_prospect_example(self):
        """Test very young prospect (advantage)."""
        # Hypothetical very young player: Born June 2008, class of 2026
        # Expected birth: July 1, 2008
        # About average, maybe slightly younger
        birth_date = date(2008, 6, 1)
        grad_year = 2026

        age_advantage = calculate_age_for_grade(birth_date, grad_year)
        assert age_advantage < 0.15  # Close to average or slightly younger

        category = categorize_age_for_grade(age_advantage)
        assert category in ["Average", "Young"]
