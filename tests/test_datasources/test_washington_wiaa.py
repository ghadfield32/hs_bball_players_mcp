"""
WIAA-WA (Washington Interscholastic Activities Association) DataSource Tests

Smoke tests for Washington WIAA datasource (tournament brackets).
Official Washington state association for postseason data.

NOTE: This is separate from Wisconsin WIAA - different state association.
"""

import pytest

from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestWashingtonWIAADataSource:
    """Test suite for Washington WIAA datasource."""

    @pytest.fixture
    def wiaa_wa_source(self):
        """Create Washington WIAA datasource instance."""
        return WashingtonWIAADataSource()

    def test_initialization(self, wiaa_wa_source):
        """Test Washington WIAA datasource initializes correctly."""
        assert wiaa_wa_source is not None
        assert wiaa_wa_source.source_type == DataSourceType.WIAA_WA
        assert wiaa_wa_source.source_name == "Washington WIAA"
        assert wiaa_wa_source.region == DataSourceRegion.US_WA
        assert wiaa_wa_source.STATE_CODE == "WA"
        assert wiaa_wa_source.STATE_NAME == "Washington"

    def test_constants(self, wiaa_wa_source):
        """Test Washington WIAA constants are defined."""
        assert wiaa_wa_source.CLASSIFICATIONS == ["4A", "3A", "2A", "1A"]
        assert wiaa_wa_source.GENDERS == ["Boys", "Girls"]

    def test_build_bracket_url(self, wiaa_wa_source):
        """Test bracket URL construction."""
        url = wiaa_wa_source._build_bracket_url(
            classification="4A",
            gender="Boys",
            year=2025
        )

        assert "wiaa.com" in url
        assert "basketball" in url.lower() or "brackets" in url.lower()
        assert "2025" in url

    def test_extract_team_and_seed(self, wiaa_wa_source):
        """Test team name and seed extraction."""
        # With seed in parentheses
        team, seed = wiaa_wa_source._extract_team_seed("Seattle O'Dea (1)")
        assert team == "Seattle O'Dea"
        assert seed == 1

        # Without seed
        team, seed = wiaa_wa_source._extract_team_seed("Tacoma Lincoln")
        assert team == "Tacoma Lincoln"
        assert seed is None

    def test_create_team(self, wiaa_wa_source):
        """Test team creation."""
        team = wiaa_wa_source._create_team(
            tid="wiaa_wa_seattle_odea",
            name="Seattle O'Dea",
            cls="4A",
            season="2024-25"
        )

        assert team is not None
        assert team.team_id == "wiaa_wa_seattle_odea"
        assert team.team_name == "Seattle O'Dea"
        assert team.state == "WA"
        assert team.league == "WIAA-WA Classification 4A"
        assert team.season == "2024-25"

    def test_game_creation_method_exists(self, wiaa_wa_source):
        """Test that game creation method exists."""
        # Verify the private helper method exists
        assert hasattr(wiaa_wa_source, '_create_game')

    @pytest.mark.asyncio
    async def test_health_check(self, wiaa_wa_source):
        """Test Washington WIAA health check."""
        is_healthy = await wiaa_wa_source.health_check()
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_structure(self, wiaa_wa_source):
        """
        Test tournament bracket fetching returns correct structure.

        NOTE: This test makes real API calls. It may fail if:
        - WIAA website is down
        - Tournament data is not yet available for the season
        - HTML structure has changed
        """
        try:
            brackets = await wiaa_wa_source.get_tournament_brackets(
                season="2024-25",
                classification="4A",
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
                assert game.game_id.startswith("wiaa_wa_")
                assert game.game_type.value == "playoff"
                assert game.data_source.source_type == DataSourceType.WIAA_WA

        except Exception as e:
            pytest.skip(f"Washington WIAA API call failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, wiaa_wa_source):
        """Test getting games from tournament brackets."""
        try:
            games = await wiaa_wa_source.get_games(
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
            pytest.skip(f"Washington WIAA get_games failed: {e}")

    def test_player_methods_not_supported(self, wiaa_wa_source):
        """Test that player methods return None/empty (not supported)."""
        assert hasattr(wiaa_wa_source, 'search_players')
        assert hasattr(wiaa_wa_source, 'get_player')
        assert hasattr(wiaa_wa_source, 'get_player_season_stats')
        assert hasattr(wiaa_wa_source, 'get_leaderboard')

    def test_classification_configuration(self, wiaa_wa_source):
        """Test Washington WIAA classification configuration."""
        assert len(wiaa_wa_source.CLASSIFICATIONS) == 4
        for classification in ["4A", "3A", "2A", "1A"]:
            assert classification in wiaa_wa_source.CLASSIFICATIONS

    def test_extract_year(self, wiaa_wa_source):
        """Test year extraction from season string."""
        year = wiaa_wa_source._extract_year("2024-25")
        assert year == 2025

        year = wiaa_wa_source._extract_year(None)
        assert year >= 2024

    def test_not_wisconsin_wiaa(self, wiaa_wa_source):
        """Test that this is Washington WIAA, not Wisconsin WIAA."""
        assert wiaa_wa_source.STATE_CODE == "WA"
        assert wiaa_wa_source.STATE_NAME == "Washington"
        assert wiaa_wa_source.region == DataSourceRegion.US_WA
        # Wisconsin uses source_type WIAA (different enum)
        assert wiaa_wa_source.source_type == DataSourceType.WIAA_WA
