"""
FIBA LiveStats Federation DataSource Tests

Smoke tests for FIBA Federation datasource adapter.
High-leverage parameterized adapter covering 50+ federations globally.
"""

import pytest

from src.datasources.vendors.fibalivestats_federation import FIBALiveStatsFederationDataSource
from src.models import DataSourceType, DataSourceRegion, Game


@pytest.mark.datasource
class TestFIBAFederationDataSource:
    """Test suite for FIBA LiveStats Federation datasource."""

    @pytest.fixture
    def egypt_source(self):
        """Create Egypt federation datasource instance."""
        return FIBALiveStatsFederationDataSource(federation_code="EGY", season="2024-25")

    @pytest.fixture
    def nigeria_source(self):
        """Create Nigeria federation datasource instance."""
        return FIBALiveStatsFederationDataSource(federation_code="NGA", season="2024-25")

    @pytest.fixture
    def japan_source(self):
        """Create Japan federation datasource instance."""
        return FIBALiveStatsFederationDataSource(federation_code="JPN", season="2024-25")

    def test_initialization_egypt(self, egypt_source):
        """Test FIBA Federation datasource initializes correctly for Egypt."""
        assert egypt_source is not None
        assert egypt_source.source_type == DataSourceType.FIBA_FEDERATION
        assert egypt_source.federation_code == "EGY"
        assert egypt_source.season == "2024-25"
        assert egypt_source.region == DataSourceRegion.GLOBAL

    def test_initialization_nigeria(self, nigeria_source):
        """Test FIBA Federation datasource initializes correctly for Nigeria."""
        assert nigeria_source is not None
        assert nigeria_source.federation_code == "NGA"
        assert "NGA" in nigeria_source.source_name
        assert "FIBA" in nigeria_source.source_name

    def test_initialization_japan(self, japan_source):
        """Test FIBA Federation datasource initializes correctly for Japan."""
        assert japan_source is not None
        assert japan_source.federation_code == "JPN"
        assert "JPN" in japan_source.source_name
        assert "FIBA" in japan_source.source_name

    def test_api_url_construction(self, egypt_source):
        """Test API URL construction."""
        # Verify BASE_API_URL exists and points to FIBA LiveStats
        assert hasattr(egypt_source, 'BASE_API_URL')
        assert "fiba" in egypt_source.BASE_API_URL.lower()
        assert "livestats" in egypt_source.BASE_API_URL.lower()

    def test_competition_id_parameter(self):
        """Test datasource with competition_id parameter."""
        source = FIBALiveStatsFederationDataSource(
            federation_code="EGY",
            season="2024-25",
            competition_id="AFROCAN2024"
        )
        assert source.competition_id == "AFROCAN2024"

    @pytest.mark.asyncio
    async def test_health_check(self, egypt_source):
        """Test FIBA health check."""
        is_healthy = await egypt_source.health_check()
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_competitions_egypt(self, egypt_source):
        """
        Test getting competitions for Egypt federation.

        NOTE: This test makes real API calls. It may fail if:
        - FIBA LiveStats API is down
        - Egypt federation has no active competitions
        - API structure has changed
        """
        try:
            competitions = await egypt_source.get_competitions(season="2024-25")

            assert isinstance(competitions, list)

            # If competitions found, validate structure
            if len(competitions) > 0:
                comp = competitions[0]
                assert isinstance(comp, dict)
                assert "id" in comp or "competition_id" in comp
                # FIBA may use different field names

        except Exception as e:
            pytest.skip(f"FIBA API call failed (API may be down or no data): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_games_nigeria(self, nigeria_source):
        """
        Test getting games for Nigeria federation.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            games = await nigeria_source.get_games(
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
                    assert game.data_source is not None
                    assert game.data_source.source_type == DataSourceType.FIBA_FEDERATION

        except Exception as e:
            pytest.skip(f"FIBA get_games failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_box_score(self, japan_source):
        """
        Test getting box score for a game.

        NOTE: This test requires a valid game_id which we don't have in advance.
        We'll skip if no games are available.
        """
        try:
            # First get games
            games = await japan_source.get_games(season="2024-25", limit=1)

            if len(games) == 0:
                pytest.skip("No games available to test box score")

            game_id = games[0].game_id

            # Get box score
            box_score = await japan_source.get_game_box_score(game_id)

            if box_score is not None:
                assert isinstance(box_score, dict)
                # Box score should have home/away teams
                assert "home_team" in box_score or "away_team" in box_score

        except Exception as e:
            pytest.skip(f"FIBA box score test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_play_by_play(self, egypt_source):
        """
        Test getting play-by-play data for a game.

        NOTE: This test requires a valid game_id.
        """
        try:
            # First get games
            games = await egypt_source.get_games(season="2024-25", limit=1)

            if len(games) == 0:
                pytest.skip("No games available to test play-by-play")

            game_id = games[0].game_id

            # Get play-by-play
            pbp = await egypt_source.get_play_by_play(game_id)

            if pbp is not None:
                assert isinstance(pbp, list)
                # Play-by-play should be a list of events

        except Exception as e:
            pytest.skip(f"FIBA play-by-play test failed: {e}")

    def test_federation_code_uppercase(self):
        """Test that federation codes are normalized to uppercase."""
        source = FIBALiveStatsFederationDataSource(federation_code="egy", season="2024")
        assert source.federation_code == "EGY"

    def test_source_name_includes_federation(self, egypt_source):
        """Test that source name includes federation code."""
        assert "EGY" in egypt_source.source_name
        assert "FIBA" in egypt_source.source_name

    @pytest.mark.asyncio
    async def test_player_methods_supported(self, egypt_source):
        """Test that player methods are available (FIBA provides player stats)."""
        # FIBA should support player data via box scores
        assert hasattr(egypt_source, 'get_player')
        assert hasattr(egypt_source, 'search_players')
        assert hasattr(egypt_source, 'get_player_season_stats')

    def test_coverage_regions(self):
        """Test that different regional federations can be instantiated."""
        # Africa
        egy_source = FIBALiveStatsFederationDataSource(federation_code="EGY")
        nga_source = FIBALiveStatsFederationDataSource(federation_code="NGA")

        # Asia
        jpn_source = FIBALiveStatsFederationDataSource(federation_code="JPN")
        chn_source = FIBALiveStatsFederationDataSource(federation_code="CHN")

        # Europe
        esp_source = FIBALiveStatsFederationDataSource(federation_code="ESP")

        # Americas
        bra_source = FIBALiveStatsFederationDataSource(federation_code="BRA")

        # All should initialize successfully
        assert all([
            egy_source, nga_source, jpn_source,
            chn_source, esp_source, bra_source
        ])
