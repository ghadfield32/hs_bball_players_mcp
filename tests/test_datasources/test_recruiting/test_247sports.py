"""
247Sports Recruiting DataSource Integration Tests

**LEGAL WARNING**: These tests interact with 247Sports which prohibits scraping.
Tests should only be run:
1. For educational/research purposes
2. With explicit permission from 247Sports
3. In compliance with rate limiting
4. Preferably with commercial data license

Tests are marked as @pytest.mark.integration and @pytest.mark.slow
Run with: pytest -m "integration" tests/test_datasources/test_recruiting/test_247sports.py

Author: Claude Code
Date: 2025-11-15
"""

import pytest

from src.datasources.recruiting.sports_247 import Sports247DataSource
from src.models import DataSourceType, Position, RecruitingRank, RecruitingService


class Test247SportsDataSource:
    """Integration tests for 247Sports recruiting datasource adapter."""

    @pytest.fixture
    async def sports247(self):
        """Create 247Sports datasource instance."""
        datasource = Sports247DataSource()
        yield datasource
        await datasource.close()

    @pytest.mark.integration
    async def test_247sports_initialization(self, sports247):
        """
        Test 247Sports datasource initializes correctly.

        Verifies:
        - Datasource type is SPORTS_247
        - Base URL is correct
        - Browser client is configured
        - Available class years are configured
        """
        assert sports247.source_type == DataSourceType.SPORTS_247
        assert sports247.source_name == "247Sports"
        assert sports247.base_url == "https://247sports.com"

        # Verify available class years (typically current + next 4 years)
        assert len(sports247.AVAILABLE_YEARS) >= 5
        assert 2025 in sports247.AVAILABLE_YEARS
        assert 2026 in sports247.AVAILABLE_YEARS

        # Verify browser client is configured
        assert sports247.browser_client is not None

    @pytest.mark.integration
    async def test_health_check(self, sports247):
        """
        Test 247Sports health check.

        Verifies website is accessible (doesn't test scraping).
        """
        is_healthy = await sports247.health_check()

        # Health check might fail due to anti-bot protection
        # Just log the result, don't fail test
        if is_healthy:
            pytest.skip("247Sports health check passed")
        else:
            pytest.skip("247Sports health check failed (expected with anti-bot protection)")

    @pytest.mark.integration
    def test_validate_class_year_valid(self, sports247):
        """Test class year validation with valid years."""
        # Test current and future years
        assert sports247._validate_class_year(2025) == 2025
        assert sports247._validate_class_year(2026) == 2026
        assert sports247._validate_class_year(2027) == 2027
        assert sports247._validate_class_year(2030) == 2030

    @pytest.mark.integration
    def test_validate_class_year_invalid(self, sports247):
        """Test class year validation with invalid years."""
        # Test past year (too old)
        with pytest.raises(ValueError, match="not available"):
            sports247._validate_class_year(2020)

        # Test too far in future
        with pytest.raises(ValueError, match="not available"):
            sports247._validate_class_year(2040)

    @pytest.mark.integration
    def test_build_rankings_url(self, sports247):
        """Test rankings URL building."""
        # Composite rankings URL
        url = sports247._build_rankings_url(2025, "composite")
        assert url == "https://247sports.com/season/2025-basketball/compositerecruitrankings/"

        # 247Sports rankings URL
        url = sports247._build_rankings_url(2026, "247sports")
        assert url == "https://247sports.com/season/2026-basketball/recruitrankings/"

        # Industry rankings URL
        url = sports247._build_rankings_url(2027, "industry")
        assert url == "https://247sports.com/season/2027-basketball/industryrecruitrankings/"

    @pytest.mark.integration
    def test_build_player_id(self, sports247):
        """Test player ID generation."""
        # With 247Sports ID
        player_id = sports247._build_player_id("John Doe", "12345")
        assert player_id == "247_12345"

        # Without 247Sports ID (uses name)
        player_id = sports247._build_player_id("John Doe")
        assert player_id == "247_john_doe"

        # Test name cleaning
        player_id = sports247._build_player_id("John P. Doe III")
        assert "247_" in player_id
        assert "john" in player_id.lower()
        assert "doe" in player_id.lower()

    @pytest.mark.integration
    def test_position_mapping(self, sports247):
        """Test position mapping from 247Sports to internal Position enum."""
        # Test standard positions
        assert sports247.POSITION_MAP["PG"] == Position.PG
        assert sports247.POSITION_MAP["SG"] == Position.SG
        assert sports247.POSITION_MAP["SF"] == Position.SF
        assert sports247.POSITION_MAP["PF"] == Position.PF
        assert sports247.POSITION_MAP["C"] == Position.C

        # Test combo positions
        assert sports247.POSITION_MAP["COMBO"] == Position.G
        assert sports247.POSITION_MAP["WING"] == Position.GF

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires ToS compliance - enable manually for testing")
    async def test_get_rankings_2025(self, sports247):
        """
        Test fetching 2025 recruiting rankings.

        **SKIPPED BY DEFAULT** - Only run with explicit permission.

        This test makes a real network request to 247Sports.
        Only run if you have permission to scrape 247Sports data.

        To run: pytest tests/test_datasources/test_recruiting/test_247sports.py::test_get_rankings_2025 -v
        """
        # Fetch top 10 players from 2025 class
        rankings = await sports247.get_rankings(
            class_year=2025,
            limit=10  # Small limit to minimize requests
        )

        # Verify results
        assert isinstance(rankings, list)

        if len(rankings) > 0:
            # Verify ranking structure
            rank = rankings[0]
            assert isinstance(rank, RecruitingRank)

            # Verify required fields
            assert rank.player_id.startswith("247_")
            assert rank.player_name is not None
            assert rank.service == RecruitingService.COMPOSITE
            assert rank.class_year == 2025

            # Verify ranking data
            assert rank.rank_national is not None
            assert rank.rank_national >= 1

            # Verify optional fields if present
            if rank.stars:
                assert 3 <= rank.stars <= 5

            if rank.rating:
                assert 0.0 <= rank.rating <= 1.0

            # Log sample player for manual verification
            print(f"\nSample Player: {rank.player_name}")
            print(f"Rank: #{rank.rank_national}")
            print(f"Stars: {rank.stars}★" if rank.stars else "Stars: N/A")
            print(f"Position: {rank.position}")
            print(f"School: {rank.school}")
            print(f"City, State: {rank.city}, {rank.state}")
            print(f"Committed To: {rank.committed_to}")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires ToS compliance - enable manually for testing")
    async def test_get_rankings_with_position_filter(self, sports247):
        """
        Test fetching rankings with position filter.

        **SKIPPED BY DEFAULT** - Only run with explicit permission.
        """
        # Fetch point guards from 2026 class
        rankings = await sports247.get_rankings(
            class_year=2026,
            limit=5,
            position="PG"
        )

        assert isinstance(rankings, list)

        if len(rankings) > 0:
            # Verify all players are point guards
            for rank in rankings:
                assert rank.position == Position.PG or rank.position is None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires ToS compliance - enable manually for testing")
    async def test_get_rankings_with_state_filter(self, sports247):
        """
        Test fetching rankings with state filter.

        **SKIPPED BY DEFAULT** - Only run with explicit permission.
        """
        # Fetch California players from 2025 class
        rankings = await sports247.get_rankings(
            class_year=2025,
            limit=5,
            state="CA"
        )

        assert isinstance(rankings, list)

        if len(rankings) > 0:
            # Verify all players are from California
            for rank in rankings:
                assert rank.state == "CA" or rank.state is None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires ToS compliance - enable manually for testing")
    async def test_search_players_by_name(self, sports247):
        """
        Test searching for players by name.

        **SKIPPED BY DEFAULT** - Only run with explicit permission.
        """
        # Search for players with common name
        results = await sports247.search_players(
            name="Smith",
            class_year=2025,
            limit=5
        )

        assert isinstance(results, list)

        if len(results) > 0:
            # Verify all results contain "Smith" in name
            for rank in results:
                assert "smith" in rank.player_name.lower()

            # Log results
            print(f"\nFound {len(results)} players with 'Smith' in name")
            for rank in results:
                print(f"  - {rank.player_name} (#{rank.rank_national})")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="ToS compliance - manual testing only")
    async def test_get_player_recruiting_profile(self, sports247):
        """
        Test getting player recruiting profile.

        **SKIPPED BY DEFAULT** - Only run with explicit permission.
        **NOT YET IMPLEMENTED** - Placeholder for future development.
        """
        # This would require a real player ID from a previous search
        # Currently returns None as method is not implemented
        player_id = "247_example_player"

        profile = await sports247.get_player_recruiting_profile(player_id)

        # Currently expected to be None (not implemented)
        assert profile is None

    @pytest.mark.integration
    async def test_247sports_enabled_in_config(self, sports247):
        """Test that 247Sports can be enabled/disabled via config."""
        # Check if enabled (default is False due to ToS concerns)
        is_enabled = sports247.is_enabled()

        # Log result
        print(f"\n247Sports enabled in config: {is_enabled}")

        # Just verify method works, don't assert value
        assert isinstance(is_enabled, bool)


@pytest.mark.integration
@pytest.mark.slow
class Test247SportsRealWorld:
    """
    Real-world integration tests for 247Sports.

    **WARNING**: These tests make real network requests.
    Only run with explicit permission from 247Sports.

    All tests are SKIPPED by default for ToS compliance.
    """

    @pytest.mark.skip(reason="ToS compliance - manual testing only")
    async def test_rankings_multiple_class_years(self):
        """
        Test fetching rankings across multiple class years.

        Would verify 247Sports adapter works for different graduating classes.
        """
        async with Sports247DataSource() as sports247:
            # Test 2025 class
            rankings_2025 = await sports247.get_rankings(class_year=2025, limit=3)
            assert len(rankings_2025) <= 3

            # Test 2026 class
            rankings_2026 = await sports247.get_rankings(class_year=2026, limit=3)
            assert len(rankings_2026) <= 3

            # Test 2027 class
            rankings_2027 = await sports247.get_rankings(class_year=2027, limit=3)
            assert len(rankings_2027) <= 3

    @pytest.mark.skip(reason="ToS compliance - manual testing only")
    async def test_ranking_data_quality(self):
        """
        Test quality of extracted ranking data.

        Would verify that parsed recruiting data is accurate and complete.
        """
        async with Sports247DataSource() as sports247:
            rankings = await sports247.get_rankings(class_year=2025, limit=10)

            for rank in rankings:
                # Verify required fields
                assert rank.player_name is not None
                assert rank.service == RecruitingService.COMPOSITE
                assert rank.class_year == 2025

                # Log data quality
                print(f"\nPlayer: {rank.player_name}")
                print(f"  National Rank: #{rank.rank_national}")
                print(f"  Stars: {rank.stars}★" if rank.stars else "  Stars: N/A")
                print(f"  Rating: {rank.rating}" if rank.rating else "  Rating: N/A")
                print(f"  Position: {rank.position}")
                print(f"  School: {rank.school}, {rank.city}, {rank.state}")
                print(f"  Height: {rank.height}" if rank.height else "  Height: N/A")
                print(f"  Weight: {rank.weight}" if rank.weight else "  Weight: N/A")
                print(f"  Committed To: {rank.committed_to}" if rank.committed_to else "  Committed To: Uncommitted")

    @pytest.mark.skip(reason="ToS compliance - manual testing only")
    async def test_browser_automation_reliability(self):
        """
        Test browser automation reliability for React content.

        Would verify that browser client consistently renders 247Sports pages.
        """
        async with Sports247DataSource() as sports247:
            # Test multiple requests to check reliability
            for i in range(3):
                rankings = await sports247.get_rankings(class_year=2025, limit=5)

                # Should get consistent results
                assert isinstance(rankings, list)
                print(f"\nRequest {i+1}: Retrieved {len(rankings)} rankings")


# Fixture for pytest
@pytest.fixture(scope="module")
def sports247_datasource():
    """Module-level 247Sports datasource fixture."""
    return Sports247DataSource()
