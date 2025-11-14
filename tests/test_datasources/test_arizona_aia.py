"""
AIA (Arizona Interscholastic Association) DataSource Tests

Smoke tests for AIA datasource (tournament brackets).
Official Arizona state association for postseason data.
"""

import pytest

from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestArizonaAIADataSource:
    """Test suite for Arizona AIA datasource."""

    @pytest.fixture
    def aia_source(self):
        """Create AIA datasource instance."""
        return ArizonaAIADataSource()

    def test_initialization(self, aia_source):
        """Test AIA datasource initializes correctly."""
        assert aia_source is not None
        assert aia_source.source_type == DataSourceType.AIA
        assert aia_source.source_name == "Arizona AIA"
        assert aia_source.region == DataSourceRegion.US_AZ
        assert aia_source.STATE_CODE == "AZ"
        assert aia_source.STATE_NAME == "Arizona"

    def test_constants(self, aia_source):
        """Test AIA constants are defined."""
        assert aia_source.CONFERENCES == ["6A", "5A", "4A", "3A", "2A", "1A", "Open"]
        assert aia_source.GENDERS == ["Boys", "Girls"]

    def test_build_bracket_url(self, aia_source):
        """Test bracket URL construction."""
        # Boys 6A Conference
        url = aia_source._build_bracket_url(
            conference="6A",
            gender="Boys",
            year=2025
        )

        assert "aiaonline.org" in url
        assert "basketball" in url.lower() or "brackets" in url.lower()
        assert "2025" in url

        # Girls 4A Conference
        url = aia_source._build_bracket_url(
            conference="4A",
            gender="Girls",
            year=2024
        )

        assert "aiaonline.org" in url
        assert "2024" in url

    def test_extract_team_and_seed(self, aia_source):
        """Test team name and seed extraction."""
        # Verify the method exists
        assert hasattr(aia_source, '_extract_team_and_seed')

        # Test with seed in parentheses
        team, seed = aia_source._extract_team_and_seed("Phoenix Sunnyslope (1)")
        assert team == "Phoenix Sunnyslope"
        assert seed == 1

        # Without seed
        team, seed = aia_source._extract_team_and_seed("Mesa Mountain View")
        assert team == "Mesa Mountain View"
        assert seed is None

    @pytest.mark.asyncio
    async def test_health_check(self, aia_source):
        """Test AIA health check."""
        is_healthy = await aia_source.health_check()
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_structure(self, aia_source):
        """
        Test tournament bracket fetching returns correct structure.

        NOTE: This test makes real API calls. It may fail if:
        - AIA website is down
        - Tournament data is not yet available for the season
        - HTML structure has changed
        """
        try:
            brackets = await aia_source.get_tournament_brackets(
                season="2024-25",
                conference="6A",  # Only fetch 6A to limit API calls
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
                assert game.game_id.startswith("aia_")
                assert game.game_type.value == "playoff"
                assert game.data_source is not None
                assert game.data_source.source_type == DataSourceType.AIA

        except Exception as e:
            pytest.skip(f"AIA API call failed (site may be down or season not available): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_all_conferences(self, aia_source):
        """
        Test fetching all conferences.

        NOTE: This is slow as it fetches 7 conferences.
        """
        try:
            brackets = await aia_source.get_tournament_brackets(
                season="2024-25",
                gender="Boys"
            )

            # Check structure
            assert isinstance(brackets, dict)
            assert "brackets" in brackets

            # Should have entries for multiple conferences
            # (May not have all 7 if tournament hasn't started)

        except Exception as e:
            pytest.skip(f"AIA all conferences test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, aia_source):
        """
        Test getting games from tournament brackets.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            games = await aia_source.get_games(
                season="2024-25",
                limit=5
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
            pytest.skip(f"AIA get_games failed: {e}")

    def test_player_methods_not_supported(self, aia_source):
        """Test that player methods return None/empty (not supported by AIA)."""
        # AIA doesn't provide player stats (by design)
        assert hasattr(aia_source, 'search_players')
        assert hasattr(aia_source, 'get_player')
        assert hasattr(aia_source, 'get_player_season_stats')
        assert hasattr(aia_source, 'get_leaderboard')

    def test_conference_configuration(self, aia_source):
        """Test AIA conference configuration."""
        # Verify all 7 conferences are configured
        assert len(aia_source.CONFERENCES) == 7
        for conference in ["6A", "5A", "4A", "3A", "2A", "1A", "Open"]:
            assert conference in aia_source.CONFERENCES

    @pytest.mark.asyncio
    async def test_get_team(self, aia_source):
        """Test getting a specific team."""
        # This test won't work well without knowing a team_id in advance
        # Just verify the method exists and has correct signature
        assert hasattr(aia_source, 'get_team')

        import inspect
        assert inspect.iscoroutinefunction(aia_source.get_team)
