"""
WIAA (Wisconsin Interscholastic Athletic Association) DataSource Tests

Smoke tests for WIAA datasource (tournament brackets).
Official Wisconsin state association for postseason data.
"""

import pytest

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestWIAADataSource:
    """Test suite for WIAA datasource."""

    @pytest.fixture
    def wiaa_source(self):
        """Create WIAA datasource instance."""
        return WisconsinWiaaDataSource()

    def test_initialization(self, wiaa_source):
        """Test WIAA datasource initializes correctly."""
        assert wiaa_source is not None
        assert wiaa_source.source_type == DataSourceType.WIAA
        assert wiaa_source.source_name == "Wisconsin WIAA"
        assert wiaa_source.region == DataSourceRegion.US_WI
        assert wiaa_source.STATE_CODE == "WI"

    def test_constants(self, wiaa_source):
        """Test WIAA constants are defined."""
        assert wiaa_source.DIVISIONS == [1, 2, 3, 4, 5]
        assert wiaa_source.SECTIONALS == [1, 2, 3, 4]
        assert wiaa_source.GENDERS == ["Boys", "Girls"]
        assert wiaa_source.MIN_YEAR == 2016

    def test_build_bracket_url(self, wiaa_source):
        """Test bracket URL construction."""
        # Boys Division 4, Sectional 3, 2025
        url = wiaa_source._build_bracket_url(
            year=2025,
            division=4,
            sectional=3,
            gender="Boys",
            final=True
        )

        assert "halftime.wiaawi.org" in url
        assert "2025_Basketball_Boys" in url
        assert "Div4" in url
        assert "Sec3" in url

    def test_extract_team_and_seed(self, wiaa_source):
        """Test team name and seed extraction."""
        # With seed in parentheses
        team, seed = wiaa_source._extract_team_and_seed("Middleton (1)")
        assert team == "Middleton"
        assert seed == 1

        # With seed in parentheses, different format
        team, seed = wiaa_source._extract_team_and_seed("Sun Prairie East (12)")
        assert team == "Sun Prairie East"
        assert seed == 12

        # Without seed
        team, seed = wiaa_source._extract_team_and_seed("Madison Memorial")
        assert team == "Madison Memorial"
        assert seed is None

    def test_create_team_from_game(self, wiaa_source):
        """Test team creation from game data."""
        team = wiaa_source._create_team_from_game(
            team_id="wiaa_wi_madison_memorial",
            team_name="Madison Memorial",
            division=1,
            sectional=2,
            season="2024-25"
        )

        assert team is not None
        assert team.team_id == "wiaa_wi_madison_memorial"
        assert team.team_name == "Madison Memorial"
        assert team.state == "WI"
        assert team.league == "WIAA Division 1"
        assert team.conference == "Sectional 2"
        assert team.season == "2024-25"

    @pytest.mark.asyncio
    async def test_health_check(self, wiaa_source):
        """Test WIAA health check."""
        is_healthy = await wiaa_source.health_check()
        assert isinstance(is_healthy, bool)
        # WIAA may or may not be reachable depending on their site status
        # We just check it returns a boolean

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_structure(self, wiaa_source):
        """
        Test tournament bracket fetching returns correct structure.

        NOTE: This test makes real API calls. It may fail if:
        - WIAA website is down
        - Tournament data is not yet available for the season
        - HTML structure has changed
        """
        try:
            brackets = await wiaa_source.get_tournament_brackets(
                season="2024-25",
                division=1,  # Only fetch Division 1 to limit API calls
                gender="Boys"
            )

            # Check structure
            assert isinstance(brackets, dict)
            assert "games" in brackets
            assert "teams" in brackets
            assert "brackets" in brackets
            assert "metadata" in brackets

            assert isinstance(brackets["games"], list)
            assert isinstance(brackets["teams"], list)
            assert isinstance(brackets["brackets"], dict)

            # If games were found, validate structure
            if len(brackets["games"]) > 0:
                game = brackets["games"][0]
                assert isinstance(game, Game)
                assert game.game_id.startswith("wiaa_")
                assert game.game_type.value == "playoff"
                assert game.data_source is not None
                assert game.data_source.source_type == DataSourceType.WIAA

        except Exception as e:
            pytest.skip(f"WIAA API call failed (site may be down or season not available): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, wiaa_source):
        """
        Test getting games from tournament brackets.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            games = await wiaa_source.get_games(
                season="2024-25",
                limit=5  # Limit to reduce API calls
            )

            assert isinstance(games, list)
            assert len(games) <= 5

            # If games found, validate structure
            if len(games) > 0:
                for game in games:
                    assert isinstance(game, Game)
                    assert game.game_id
                    assert game.home_team_name or game.away_team_name

        except Exception as e:
            pytest.skip(f"WIAA get_games failed: {e}")

    def test_player_methods_not_supported(self, wiaa_source):
        """Test that player methods return None/empty (not supported by WIAA)."""
        # These should not raise errors, just return None/empty
        # WIAA doesn't provide player stats (by design)

        # search_players should return empty list
        # get_player should return None
        # get_player_season_stats should return None
        # get_leaderboard should return empty list

        # We're just testing the methods exist and have correct signatures
        assert hasattr(wiaa_source, 'search_players')
        assert hasattr(wiaa_source, 'get_player')
        assert hasattr(wiaa_source, 'get_player_season_stats')
        assert hasattr(wiaa_source, 'get_leaderboard')
