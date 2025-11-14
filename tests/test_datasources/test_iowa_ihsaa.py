"""
Iowa IHSAA (Iowa High School Athletic Association) DataSource Tests

Smoke tests for Iowa IHSAA datasource (tournament brackets and box scores).
Official Iowa state association for postseason data.
"""

import pytest

from src.datasources.us.iowa_ihsaa import IowaIHSAADataSource
from src.models import DataSourceType, DataSourceRegion


@pytest.mark.datasource
class TestIowaIHSAADataSource:
    """Test suite for Iowa IHSAA datasource."""

    @pytest.fixture
    def ihsaa_source(self):
        """Create Iowa IHSAA datasource instance."""
        return IowaIHSAADataSource()

    def test_initialization(self, ihsaa_source):
        """Test Iowa IHSAA datasource initializes correctly."""
        assert ihsaa_source is not None
        assert ihsaa_source.source_type == DataSourceType.IHSAA_IA
        assert ihsaa_source.source_name == "Iowa IHSAA"
        assert ihsaa_source.region == DataSourceRegion.US_IA
        assert ihsaa_source.STATE_CODE == "IA"
        assert ihsaa_source.STATE_NAME == "Iowa"

    def test_constants(self, ihsaa_source):
        """Test Iowa IHSAA constants are defined."""
        assert ihsaa_source.CLASSES == ["1A", "2A", "3A", "4A"]
        assert ihsaa_source.GENDERS == ["Boys"]  # Girls TBD
        assert ihsaa_source.MIN_YEAR == 2015  # Estimated, needs validation

    def test_season_url(self, ihsaa_source):
        """Test season URL construction."""
        url = ihsaa_source._get_season_url("2024-25")
        assert "iahsaa.org" in url
        assert "basketball" in url
        assert "state-tournament-central" in url

    def test_box_score_url(self, ihsaa_source):
        """Test box score URL construction."""
        # Test Class 4A, Game 1, Year 2025
        url = ihsaa_source._build_box_score_url(
            year=2025,
            class_name="4A",
            game_number=1
        )

        assert "iahsaa.org" in url
        assert "/wp-content/uploads/2025/03/4A1.htm" in url

        # Test Class 1A, Game 5, Year 2024
        url = ihsaa_source._build_box_score_url(
            year=2024,
            class_name="1A",
            game_number=5
        )

        assert "iahsaa.org" in url
        assert "/wp-content/uploads/2024/03/1A5.htm" in url

    def test_slugify(self, ihsaa_source):
        """Test text slugification for URLs."""
        # Test with spaces
        slug = ihsaa_source._slugify("West Des Moines Valley")
        assert slug == "west_des_moines_valley"

        # Test with punctuation
        slug = ihsaa_source._slugify("North Scott (Eldridge)")
        assert slug == "north_scott_eldridge"

        # Test with mixed case
        slug = ihsaa_source._slugify("Cedar Rapids Kennedy")
        assert slug == "cedar_rapids_kennedy"

    def test_create_team(self, ihsaa_source):
        """Test team creation from tournament data."""
        team = ihsaa_source._create_team(
            team_id="ihsaa_ia:2025:waukee",
            team_name="Waukee",
            class_name="4A",
            season="2024-25"
        )

        assert team is not None
        assert team.team_id == "ihsaa_ia:2025:waukee"
        assert team.team_name == "Waukee"
        assert team.state == "IA"
        assert team.league == "IHSAA Class 4A"
        assert team.season == "2024-25"
        assert team.data_source.source_name == "Iowa IHSAA"

    @pytest.mark.asyncio
    async def test_player_search_not_supported(self, ihsaa_source):
        """Test that player search raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            await ihsaa_source.search_players(name="Test Player")

        assert "does not support player search" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_leaderboard_not_supported(self, ihsaa_source):
        """Test that leaderboards raise NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            await ihsaa_source.get_leaderboard(stat="pts", season="2024-25")

        assert "does not provide stat leaderboards" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Off-season - no current data available")
    async def test_get_tournament_brackets(self, ihsaa_source):
        """Test tournament bracket retrieval (skipped during off-season)."""
        # This test will pass during tournament season (March)
        # Skipped for now as we're in off-season (November)
        result = await ihsaa_source.get_tournament_brackets(
            season="2024-25",
            class_name="4A"
        )

        assert "games" in result
        assert "teams" in result
        assert "brackets" in result
        assert "metadata" in result
        assert result["year"] == 2025
        assert result["gender"] == "Boys"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Off-season - no current data available")
    async def test_get_games(self, ihsaa_source):
        """Test game retrieval (skipped during off-season)."""
        games = await ihsaa_source.get_games(season="2024-25")

        # During tournament season, this should return games
        assert isinstance(games, list)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Historical data validation needed")
    async def test_historical_data_range(self, ihsaa_source):
        """Test historical data availability (validation needed)."""
        # Test 2024 season (most recent complete season)
        result = await ihsaa_source.get_tournament_brackets(season="2023-24")

        # If data is available, we should get games
        # This test validates MIN_YEAR = 2015 assumption
        if result["games"]:
            assert len(result["games"]) > 0
            assert result["year"] == 2024

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Needs actual box score data for validation")
    async def test_game_stats_parsing(self, ihsaa_source):
        """Test box score parsing (needs actual data)."""
        # This test requires a valid game_id and box score availability
        # Will be validated during tournament season
        stats = await ihsaa_source.get_game_stats(
            game_id="ihsaa_ia:2024:4a:championship",
            year=2024,
            class_name="4A",
            game_number=1
        )

        assert "game_id" in stats
        assert "player_stats" in stats

    def test_base_url(self, ihsaa_source):
        """Test base URLs are correctly configured."""
        assert ihsaa_source.base_url == "https://www.iahsaa.org"
        assert ihsaa_source.stats_url == "https://stats.iahsaa.org/basketball"

    def test_inherited_capabilities(self, ihsaa_source):
        """Test inherited AssociationAdapterBase capabilities."""
        # Should have base class attributes
        assert hasattr(ihsaa_source, "http_client")
        assert hasattr(ihsaa_source, "logger")
        assert hasattr(ihsaa_source, "HAS_BRACKETS")
        assert ihsaa_source.HAS_BRACKETS is True

    @pytest.mark.asyncio
    async def test_all_classifications(self, ihsaa_source):
        """Test that all classifications are configured."""
        for class_name in ["1A", "2A", "3A", "4A"]:
            # Test URL building for each class
            url = ihsaa_source._build_box_score_url(2024, class_name, 1)
            assert class_name in url
            assert "2024" in url
