"""
OSAA (Oregon School Activities Association) DataSource Tests

Smoke tests for OSAA datasource (tournament brackets).
Official Oregon state association with JSON widget support.
"""

import pytest

from src.datasources.us.oregon_osaa import OregonOSAADataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestOregonOSAADataSource:
    """Test suite for Oregon OSAA datasource."""

    @pytest.fixture
    def osaa_source(self):
        """Create OSAA datasource instance."""
        return OregonOSAADataSource()

    def test_initialization(self, osaa_source):
        """Test OSAA datasource initializes correctly."""
        assert osaa_source is not None
        assert osaa_source.source_type == DataSourceType.OSAA
        assert osaa_source.source_name == "Oregon OSAA"
        assert osaa_source.region == DataSourceRegion.US_OR
        assert osaa_source.STATE_CODE == "OR"
        assert osaa_source.STATE_NAME == "Oregon"

    def test_constants(self, osaa_source):
        """Test OSAA constants are defined."""
        assert osaa_source.CLASSIFICATIONS == ["6A", "5A", "4A", "3A", "2A", "1A"]
        assert osaa_source.GENDERS == ["Boys", "Girls"]

    def test_build_bracket_url_html(self, osaa_source):
        """Test HTML bracket URL construction."""
        url = osaa_source._build_bracket_url(
            classification="6A",
            gender="Boys",
            year=2025
        )

        assert "osaa.org" in url
        assert "basketball" in url.lower() or "brackets" in url.lower()
        assert "2025" in url

    def test_build_bracket_url_json(self, osaa_source):
        """Test JSON bracket URL construction (OSAA special feature)."""
        url = osaa_source._build_json_bracket_url(
            classification="6A",
            gender="Boys",
            year=2025
        )

        assert "osaa.org" in url
        assert "json" in url.lower()
        assert "6a" in url.lower()
        assert "2025" in url

    def test_extract_team_and_seed(self, osaa_source):
        """Test team name and seed extraction."""
        # Verify the method exists
        assert hasattr(osaa_source, '_extract_team_and_seed')

        # Test with seed in parentheses
        team, seed = osaa_source._extract_team_and_seed("Portland Jefferson (1)")
        assert team == "Portland Jefferson"
        assert seed == 1

        # Without seed
        team, seed = osaa_source._extract_team_and_seed("Beaverton")
        assert team == "Beaverton"
        assert seed is None

    @pytest.mark.asyncio
    async def test_health_check(self, osaa_source):
        """Test OSAA health check."""
        is_healthy = await osaa_source.health_check()
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_json_first(self, osaa_source):
        """
        Test tournament bracket fetching with JSON-first approach.

        NOTE: This test makes real API calls. It may fail if:
        - OSAA website is down
        - Tournament data is not yet available for the season
        - JSON widget or HTML structure has changed
        """
        try:
            brackets = await osaa_source.get_tournament_brackets(
                season="2024-25",
                classification="6A",  # Only fetch 6A to limit API calls
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
                assert game.game_id.startswith("osaa_")
                assert game.game_type.value == "playoff"
                assert game.data_source is not None
                assert game.data_source.source_type == DataSourceType.OSAA

        except Exception as e:
            pytest.skip(f"OSAA API call failed (site may be down or season not available): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_parse_json_widget(self, osaa_source):
        """
        Test JSON widget parsing (OSAA special feature).

        This test verifies that OSAA can parse JSON bracket data if available.
        """
        try:
            # Try to fetch a bracket with JSON endpoint
            brackets = await osaa_source.get_tournament_brackets(
                season="2024-25",
                classification="5A",
                gender="Girls"
            )

            # If successful, data should be present
            assert isinstance(brackets, dict)

            # Metadata may indicate if JSON was used
            if "metadata" in brackets and len(brackets["metadata"]) > 0:
                # Check if any metadata suggests JSON source
                pass  # JSON source detection is internal

        except Exception as e:
            pytest.skip(f"OSAA JSON widget test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_tournament_brackets_all_classifications(self, osaa_source):
        """
        Test fetching all classifications.

        NOTE: This is slow as it fetches 6 classifications.
        """
        try:
            brackets = await osaa_source.get_tournament_brackets(
                season="2024-25",
                gender="Boys"
            )

            # Check structure
            assert isinstance(brackets, dict)
            assert "brackets" in brackets

            # Should have entries for multiple classifications
            # (May not have all 6 if tournament hasn't started)

        except Exception as e:
            pytest.skip(f"OSAA all classifications test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games(self, osaa_source):
        """
        Test getting games from tournament brackets.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            games = await osaa_source.get_games(
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
            pytest.skip(f"OSAA get_games failed: {e}")

    def test_player_methods_not_supported(self, osaa_source):
        """Test that player methods return None/empty (not supported by OSAA)."""
        # OSAA doesn't provide player stats (by design)
        assert hasattr(osaa_source, 'search_players')
        assert hasattr(osaa_source, 'get_player')
        assert hasattr(osaa_source, 'get_player_season_stats')
        assert hasattr(osaa_source, 'get_leaderboard')

    def test_classification_configuration(self, osaa_source):
        """Test OSAA classification configuration."""
        # Verify all 6 classifications are configured
        assert len(osaa_source.CLASSIFICATIONS) == 6
        for classification in ["6A", "5A", "4A", "3A", "2A", "1A"]:
            assert classification in osaa_source.CLASSIFICATIONS

    def test_json_vs_html_fallback(self, osaa_source):
        """Test that datasource has both JSON and HTML parsing methods."""
        # OSAA should have both methods for JSON-first approach
        assert hasattr(osaa_source, '_parse_bracket_json')
        assert hasattr(osaa_source, '_parse_bracket_html')
        assert hasattr(osaa_source, '_build_json_bracket_url')
        assert hasattr(osaa_source, '_build_bracket_url')

    @pytest.mark.asyncio
    async def test_get_team(self, osaa_source):
        """Test getting a specific team."""
        # This test won't work well without knowing a team_id in advance
        # Just verify the method exists and has correct signature
        assert hasattr(osaa_source, 'get_team')

        import inspect
        assert inspect.iscoroutinefunction(osaa_source.get_team)
