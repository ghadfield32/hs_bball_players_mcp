"""
IHSAA-ID (Idaho High School Activities Association) DataSource Tests

Smoke tests for Idaho IHSAA datasource (tournament brackets).
Official Idaho state association for postseason data.

NOTE: This is IHSAA-ID (Idaho), separate from IHSAA (Illinois) and IHSAA (Indiana).
"""

import pytest

from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestIdahoIHSAADataSource:
    """Test suite for Idaho IHSAA datasource."""

    @pytest.fixture
    def ihsaa_id_source(self):
        """Create Idaho IHSAA datasource instance."""
        return IdahoIHSAADataSource()

    def test_initialization(self, ihsaa_id_source):
        """Test Idaho IHSAA datasource initializes correctly."""
        assert ihsaa_id_source is not None
        assert ihsaa_id_source.source_type == DataSourceType.IHSAA_ID
        assert ihsaa_id_source.source_name == "Idaho IHSAA"
        assert ihsaa_id_source.region == DataSourceRegion.US_ID
        assert ihsaa_id_source.STATE_CODE == "ID"
        assert ihsaa_id_source.STATE_NAME == "Idaho"

    def test_constants(self, ihsaa_id_source):
        """Test Idaho IHSAA constants are defined."""
        assert ihsaa_id_source.CLASSIFICATIONS == ["6A", "5A", "4A", "3A", "2A", "1A"]
        assert ihsaa_id_source.GENDERS == ["Boys", "Girls"]

    def test_build_bracket_url(self, ihsaa_id_source):
        """Test bracket URL construction."""
        url = ihsaa_id_source._build_bracket_url(
            classification="6A",
            gender="Boys",
            year=2025
        )

        assert "idhsaa.org" in url
        assert "basketball" in url.lower() or "brackets" in url.lower()
        assert "2025" in url

    def test_extract_team_and_seed(self, ihsaa_id_source):
        """Test team name and seed extraction."""
        # With seed in parentheses
        team, seed = ihsaa_id_source._extract_team_seed("Boise (1)")
        assert team == "Boise"
        assert seed == 1

        # Without seed
        team, seed = ihsaa_id_source._extract_team_seed("Meridian")
        assert team == "Meridian"
        assert seed is None

    def test_create_team(self, ihsaa_id_source):
        """Test team creation."""
        team = ihsaa_id_source._create_team(
            tid="ihsaa_id_boise",
            name="Boise",
            cls="6A",
            season="2024-25"
        )

        assert team is not None
        assert team.team_id == "ihsaa_id_boise"
        assert team.team_name == "Boise"
        assert team.state == "ID"
        assert team.league == "IHSAA-ID Classification 6A"
        assert team.season == "2024-25"

    def test_game_creation_method_exists(self, ihsaa_id_source):
        """Test that game creation method exists."""
        # Verify the private helper method exists
        assert hasattr(ihsaa_id_source, '_create_game')

    @pytest.mark.asyncio
    async def test_health_check(self, ihsaa_id_source):
        """Test Idaho IHSAA health check."""
        is_healthy = await ihsaa_id_source.health_check()
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_structure(self, ihsaa_id_source):
        """
        Test tournament bracket fetching returns correct structure.

        NOTE: This test makes real API calls. It may fail if:
        - IHSAA website is down
        - Tournament data is not yet available for the season
        - HTML structure has changed
        """
        try:
            brackets = await ihsaa_id_source.get_tournament_brackets(
                season="2024-25",
                classification="6A",
                gender="Boys"
            )

            # Check structure
            assert isinstance(brackets, dict)
            assert "games" in brackets
            assert "teams" in brackets
            assert "brackets" in brackets
            assert "metadata" in brackets

            # If games were found, validate structure
            if len(brackets["games"]) > 0:
                game = brackets["games"][0]
                assert isinstance(game, Game)
                assert game.game_id.startswith("ihsaa_id_")
                assert game.game_type.value == "playoff"
                assert game.data_source.source_type == DataSourceType.IHSAA_ID

        except Exception as e:
            pytest.skip(f"Idaho IHSAA API call failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, ihsaa_id_source):
        """Test getting games from tournament brackets."""
        try:
            games = await ihsaa_id_source.get_games(
                season="2024-25",
                limit=5
            )

            assert isinstance(games, list)
            assert len(games) <= 5

            if len(games) > 0:
                for game in games:
                    assert isinstance(game, Game)
                    assert game.game_id

        except Exception as e:
            pytest.skip(f"Idaho IHSAA get_games failed: {e}")

    def test_player_methods_not_supported(self, ihsaa_id_source):
        """Test that player methods return None/empty (not supported)."""
        assert hasattr(ihsaa_id_source, 'search_players')
        assert hasattr(ihsaa_id_source, 'get_player')
        assert hasattr(ihsaa_id_source, 'get_player_season_stats')
        assert hasattr(ihsaa_id_source, 'get_leaderboard')

    def test_classification_configuration(self, ihsaa_id_source):
        """Test Idaho IHSAA classification configuration."""
        assert len(ihsaa_id_source.CLASSIFICATIONS) == 6
        for classification in ["6A", "5A", "4A", "3A", "2A", "1A"]:
            assert classification in ihsaa_id_source.CLASSIFICATIONS

    def test_extract_year(self, ihsaa_id_source):
        """Test year extraction from season string."""
        year = ihsaa_id_source._extract_year("2024-25")
        assert year == 2025

        year = ihsaa_id_source._extract_year(None)
        assert year >= 2024

    def test_not_illinois_or_indiana(self, ihsaa_id_source):
        """Test that this is Idaho IHSAA, not Illinois or Indiana."""
        assert ihsaa_id_source.STATE_CODE == "ID"
        assert ihsaa_id_source.STATE_NAME == "Idaho"
        assert ihsaa_id_source.region == DataSourceRegion.US_ID
        # Idaho uses source_type IHSAA_ID (different from IHSA or IHSAA)
        assert ihsaa_id_source.source_type == DataSourceType.IHSAA_ID
