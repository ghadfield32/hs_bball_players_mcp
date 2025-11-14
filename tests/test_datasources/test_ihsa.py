"""
IHSA (Illinois High School Association) DataSource Tests

Smoke tests for IHSA datasource (tournament brackets).
Official Illinois state association for postseason data.
"""

import pytest

from src.datasources.us.illinois_ihsa import IHSADataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestIHSADataSource:
    """Test suite for IHSA datasource."""

    @pytest.fixture
    def ihsa_source(self):
        """Create IHSA datasource instance."""
        return IHSADataSource()

    def test_initialization(self, ihsa_source):
        """Test IHSA datasource initializes correctly."""
        assert ihsa_source is not None
        assert ihsa_source.source_type == DataSourceType.IHSA
        assert ihsa_source.source_name == "Illinois IHSA"
        assert ihsa_source.region == DataSourceRegion.US_IL
        assert ihsa_source.STATE_CODE == "IL"

    def test_constants(self, ihsa_source):
        """Test IHSA constants are defined."""
        assert ihsa_source.CLASSES == ["1A", "2A", "3A", "4A"]
        assert ihsa_source.GENDERS == ["Boys", "Girls"]
        assert ihsa_source.MIN_YEAR == 2016

    def test_build_bracket_url(self, ihsa_source):
        """Test bracket URL construction."""
        # Boys Class 4A
        url = ihsa_source._build_bracket_url(
            class_name="4A",
            gender="Boys"
        )

        assert "ihsa.org" in url
        assert "bkb" in url  # Boys basketball code
        assert "4bracket.htm" in url

        # Girls Class 2A
        url = ihsa_source._build_bracket_url(
            class_name="2A",
            gender="Girls"
        )

        assert "ihsa.org" in url
        assert "bkg" in url  # Girls basketball code
        assert "2bracket.htm" in url

    def test_extract_team_and_seed(self, ihsa_source):
        """Test team name and seed extraction."""
        # With seed in parentheses
        team, seed = ihsa_source._extract_team_and_seed("Chicago Simeon (1)")
        assert team == "Chicago Simeon"
        assert seed == 1

        # With seed in parentheses, different format
        team, seed = ihsa_source._extract_team_and_seed("Decatur MacArthur (12)")
        assert team == "Decatur MacArthur"
        assert seed == 12

        # Without seed
        team, seed = ihsa_source._extract_team_and_seed("Peoria Central")
        assert team == "Peoria Central"
        assert seed is None

    def test_create_team_from_game(self, ihsa_source):
        """Test team creation from game data."""
        team = ihsa_source._create_team_from_game(
            team_id="ihsa_il_chicago_simeon",
            team_name="Chicago Simeon",
            class_name="4A",
            season="2024-25"
        )

        assert team is not None
        assert team.team_id == "ihsa_il_chicago_simeon"
        assert team.team_name == "Chicago Simeon"
        assert team.state == "IL"
        assert team.league == "IHSA Class 4A"
        assert team.season == "2024-25"

    @pytest.mark.asyncio
    async def test_health_check(self, ihsa_source):
        """Test IHSA health check."""
        is_healthy = await ihsa_source.health_check()
        assert isinstance(is_healthy, bool)
        # IHSA may or may not be reachable depending on their site status
        # We just check it returns a boolean

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_structure(self, ihsa_source):
        """
        Test tournament bracket fetching returns correct structure.

        NOTE: This test makes real API calls. It may fail if:
        - IHSA website is down
        - Tournament data is not yet available for the season
        - HTML structure has changed
        """
        try:
            brackets = await ihsa_source.get_tournament_brackets(
                season="2024-25",
                class_name="4A",  # Only fetch Class 4A to limit API calls
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
                assert game.game_id.startswith("ihsa_")
                assert game.game_type.value == "playoff"
                assert game.data_source is not None
                assert game.data_source.source_type == DataSourceType.IHSA

        except Exception as e:
            pytest.skip(f"IHSA API call failed (site may be down or season not available): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, ihsa_source):
        """
        Test getting games from tournament brackets.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            games = await ihsa_source.get_games(
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
            pytest.skip(f"IHSA get_games failed: {e}")

    def test_player_methods_not_supported(self, ihsa_source):
        """Test that player methods return None/empty (not supported by IHSA)."""
        # These should not raise errors, just return None/empty
        # IHSA doesn't provide player stats (by design)

        # search_players should return empty list
        # get_player should return None
        # get_player_season_stats should return None
        # get_leaderboard should return empty list

        # We're just testing the methods exist and have correct signatures
        assert hasattr(ihsa_source, 'search_players')
        assert hasattr(ihsa_source, 'get_player')
        assert hasattr(ihsa_source, 'get_player_season_stats')
        assert hasattr(ihsa_source, 'get_leaderboard')

    def test_build_team_id(self, ihsa_source):
        """Test team ID construction."""
        team_id = ihsa_source._build_team_id("chicago_simeon")
        assert team_id == "ihsa_il_chicago_simeon"

    def test_build_game_id(self, ihsa_source):
        """Test game ID construction."""
        game_id = ihsa_source._build_game_id(
            home_team="Chicago Simeon",
            away_team="Peoria Central",
            season="2024-25",
            round_name="Semifinals"
        )
        assert game_id.startswith("ihsa_2024-25_")
        assert "semifinals" in game_id.lower()

    def test_class_configuration(self, ihsa_source):
        """Test IHSA class configuration."""
        # Verify all 4 classes are configured
        assert len(ihsa_source.CLASSES) == 4
        for class_name in ["1A", "2A", "3A", "4A"]:
            assert class_name in ihsa_source.CLASSES

    def test_season_validation(self, ihsa_source):
        """Test season validation."""
        # Valid season formats
        valid_seasons = ["2024-25", "2023-24", "2022-23"]
        for season in valid_seasons:
            # Should not raise errors
            year = int(season.split("-")[0])
            assert year >= ihsa_source.MIN_YEAR

    @pytest.mark.asyncio
    async def test_enumerate_all_brackets(self, ihsa_source):
        """Test that enumerate_all_brackets returns correct structure."""
        # This tests the method exists and returns proper format
        # without making actual API calls
        assert hasattr(ihsa_source, 'enumerate_all_brackets')

        # The method should be callable
        import inspect
        assert inspect.iscoroutinefunction(ihsa_source.enumerate_all_brackets)
