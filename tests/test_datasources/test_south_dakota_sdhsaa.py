"""
South Dakota SDHSAA (South Dakota High School Activities Association) DataSource Tests

Smoke tests for South Dakota SDHSAA datasource (tournament brackets via MaxPreps).
Official South Dakota state association for postseason data.
"""

import pytest

from src.datasources.us.south_dakota_sdhsaa import SouthDakotaSdhsaaDataSource
from src.models import DataSourceType, DataSourceRegion


@pytest.mark.datasource
class TestSouthDakotaSdhsaaDataSource:
    """Test suite for South Dakota SDHSAA datasource."""

    @pytest.fixture
    def sdhsaa_source(self):
        """Create South Dakota SDHSAA datasource instance."""
        return SouthDakotaSdhsaaDataSource()

    def test_initialization(self, sdhsaa_source):
        """Test South Dakota SDHSAA datasource initializes correctly."""
        assert sdhsaa_source is not None
        assert sdhsaa_source.source_type == DataSourceType.SDHSAA
        assert sdhsaa_source.source_name == "South Dakota SDHSAA"
        assert sdhsaa_source.region == DataSourceRegion.US_SD
        assert sdhsaa_source.STATE_CODE == "SD"
        assert sdhsaa_source.STATE_NAME == "South Dakota"

    def test_constants(self, sdhsaa_source):
        """Test South Dakota SDHSAA constants are defined."""
        assert sdhsaa_source.CLASSES == ["AA", "A", "B"]
        assert sdhsaa_source.GENDERS == ["Boys", "Girls"]
        assert sdhsaa_source.MIN_YEAR == 2015  # Estimated, needs validation
        assert sdhsaa_source.REGIONS == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_season_url(self, sdhsaa_source):
        """Test season URL construction."""
        url = sdhsaa_source._get_season_url("2024-25")
        assert "maxpreps.com" in url
        assert "search" in url
        assert "sdhsaa" in url.lower()
        assert "south" in url.lower() or "dakota" in url.lower()

    def test_tournament_url_pattern(self, sdhsaa_source):
        """Test tournament URL pattern construction."""
        # Test Class AA Boys
        url = sdhsaa_source._build_tournament_url(
            year=2025, class_name="AA", gender="Boys", bracket_type="state"
        )

        assert "maxpreps.com" in url
        assert "tournament" in url
        assert "class-aa" in url.lower()
        assert "state-tournament" in url

        # Test Class B Girls
        url = sdhsaa_source._build_tournament_url(
            year=2024, class_name="B", gender="Girls", bracket_type="regional"
        )

        assert "maxpreps.com" in url
        assert "girls" in url.lower()
        assert "class-b" in url.lower()
        assert "regional-tournament" in url

    def test_slugify(self, sdhsaa_source):
        """Test text slugification for URLs."""
        # Test with spaces
        slug = sdhsaa_source._slugify("Rapid City Stevens")
        assert slug == "rapid_city_stevens"

        # Test with punctuation
        slug = sdhsaa_source._slugify("Sioux Falls O'Gorman")
        assert slug == "sioux_falls_ogorman"

        # Test with mixed case
        slug = sdhsaa_source._slugify("Aberdeen Central")
        assert slug == "aberdeen_central"

    def test_create_team(self, sdhsaa_source):
        """Test team creation from tournament data."""
        team = sdhsaa_source._create_team(
            team_id="sdhsaa_sd:2025:aa:rapid_city_stevens",
            team_name="Rapid City Stevens",
            class_name="AA",
            season="2024-25",
        )

        assert team is not None
        assert team.team_id == "sdhsaa_sd:2025:aa:rapid_city_stevens"
        assert team.team_name == "Rapid City Stevens"
        assert team.state == "SD"
        assert team.league == "SDHSAA Class AA"
        assert team.season == "2024-25"
        assert team.data_source.source_name == "South Dakota SDHSAA"

    def test_tournament_venues(self, sdhsaa_source):
        """Test tournament venue metadata."""
        assert sdhsaa_source.TOURNAMENT_VENUES["AA"] == "Rapid City, SD (Barnett Arena)"
        assert sdhsaa_source.TOURNAMENT_VENUES["A"] == "Sioux Falls, SD (Sanford Pentagon)"
        assert sdhsaa_source.TOURNAMENT_VENUES["B"] == "Aberdeen, SD (Civic Arena)"

    @pytest.mark.asyncio
    async def test_player_search_not_supported(self, sdhsaa_source):
        """Test that player search raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            await sdhsaa_source.search_players(name="Test Player")

        assert "does not support player search" in str(exc_info.value).lower()
        assert "bound" in str(exc_info.value).lower()  # Should suggest Bound adapter

    @pytest.mark.asyncio
    async def test_leaderboard_not_supported(self, sdhsaa_source):
        """Test that leaderboards raise NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            await sdhsaa_source.get_leaderboard(stat="pts", season="2024-25")

        assert "does not provide stat leaderboards" in str(exc_info.value).lower()
        assert "bound" in str(exc_info.value).lower()  # Should suggest Bound adapter

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Off-season - no current data available")
    async def test_get_tournament_brackets(self, sdhsaa_source):
        """Test tournament bracket retrieval (skipped during off-season)."""
        # This test will pass during tournament season (March)
        # Skipped for now as we're in off-season (November)
        result = await sdhsaa_source.get_tournament_brackets(
            season="2024-25", class_name="AA"
        )

        assert "games" in result
        assert "teams" in result
        assert "brackets" in result
        assert "metadata" in result
        assert result["metadata"]["year"] == 2025
        assert result["metadata"]["state"] == "SD"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Off-season - no current data available")
    async def test_get_games(self, sdhsaa_source):
        """Test game retrieval (skipped during off-season)."""
        games = await sdhsaa_source.get_games(season="2024-25")

        # During tournament season, this should return games
        assert isinstance(games, list)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Historical data validation needed")
    async def test_historical_data_range(self, sdhsaa_source):
        """Test historical data availability (validation needed)."""
        # Test 2024 season (most recent complete season)
        result = await sdhsaa_source.get_tournament_brackets(season="2023-24")

        # If data is available, we should get games
        # This test validates MIN_YEAR = 2015 assumption
        if result["games"]:
            assert len(result["games"]) > 0
            assert result["metadata"]["year"] == 2024

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Needs actual MaxPreps data for validation")
    async def test_all_classes(self, sdhsaa_source):
        """Test all classes can be fetched (needs actual data)."""
        for class_name in ["AA", "A", "B"]:
            result = await sdhsaa_source.get_tournament_brackets(
                season="2023-24", class_name=class_name
            )

            assert result["metadata"]["classes"] == [class_name]
            assert class_name in result["brackets"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Needs actual MaxPreps data for validation")
    async def test_girls_basketball(self, sdhsaa_source):
        """Test girls basketball support (needs actual data)."""
        result = await sdhsaa_source.get_tournament_brackets(
            season="2023-24", class_name="AA", gender="Girls"
        )

        assert result["metadata"]["gender"] == "Girls"
        assert "games" in result

    def test_base_url(self, sdhsaa_source):
        """Test base URLs are correctly configured."""
        assert sdhsaa_source.base_url == "https://www.maxpreps.com"
        assert "maxpreps" in sdhsaa_source.base_url

    def test_inherited_capabilities(self, sdhsaa_source):
        """Test inherited AssociationAdapterBase capabilities."""
        # Should have base class attributes
        assert hasattr(sdhsaa_source, "http_client")
        assert hasattr(sdhsaa_source, "logger")
        assert hasattr(sdhsaa_source, "HAS_BRACKETS")
        assert sdhsaa_source.HAS_BRACKETS is True

    @pytest.mark.asyncio
    async def test_all_classifications(self, sdhsaa_source):
        """Test that all classifications are configured."""
        for class_name in ["AA", "A", "B"]:
            # Test URL building for each class
            url = sdhsaa_source._build_tournament_url(2024, class_name, "Boys", "state")
            assert f"class-{class_name.lower()}" in url.lower()
            assert "2024" in url or "23-24" in url

    def test_class_validation(self, sdhsaa_source):
        """Test class validation in tournament bracket method."""
        # This is a synchronous wrapper to test validation
        with pytest.raises(ValueError) as exc_info:
            # Create a coroutine but don't await it (just checking validation)
            import asyncio

            asyncio.run(
                sdhsaa_source.get_tournament_brackets(
                    season="2024-25", class_name="INVALID"
                )
            )

        assert "invalid class" in str(exc_info.value).lower()

    def test_gender_validation(self, sdhsaa_source):
        """Test gender validation in tournament bracket method."""
        with pytest.raises(ValueError) as exc_info:
            import asyncio

            asyncio.run(
                sdhsaa_source.get_tournament_brackets(
                    season="2024-25", gender="INVALID"
                )
            )

        assert "invalid gender" in str(exc_info.value).lower()

    def test_regional_structure(self, sdhsaa_source):
        """Test regional structure constants."""
        assert len(sdhsaa_source.REGIONS) == 8
        assert sdhsaa_source.REGIONS == [1, 2, 3, 4, 5, 6, 7, 8]
        assert all(isinstance(r, int) for r in sdhsaa_source.REGIONS)
