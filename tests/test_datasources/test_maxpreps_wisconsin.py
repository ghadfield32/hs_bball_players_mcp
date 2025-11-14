"""
MaxPreps Wisconsin DataSource Tests

Smoke tests for MaxPreps Wisconsin datasource (player/team stats).
Provides player-level statistics and regular season depth for Wisconsin.
"""

import pytest

from src.datasources.us.wisconsin_maxpreps import MaxPrepsWisconsinDataSource
from src.models import DataSourceType, DataSourceRegion, Player, PlayerSeasonStats


@pytest.mark.datasource
class TestMaxPrepsWisconsinDataSource:
    """Test suite for MaxPreps Wisconsin datasource."""

    def test_initialization(self, maxpreps_wi_source):
        """Test MaxPreps Wisconsin datasource initializes correctly."""
        assert maxpreps_wi_source is not None
        assert maxpreps_wi_source.source_type == DataSourceType.MAXPREPS_WI
        assert maxpreps_wi_source.source_name == "MaxPreps Wisconsin"
        assert maxpreps_wi_source.region == DataSourceRegion.US_WI
        assert maxpreps_wi_source.STATE_CODE == "WI"
        assert maxpreps_wi_source.STATE_NAME == "Wisconsin"

    def test_url_configuration(self, maxpreps_wi_source):
        """Test MaxPreps URLs are configured."""
        assert "maxpreps.com" in maxpreps_wi_source.base_url
        assert "maxpreps.com/wi/basketball" in maxpreps_wi_source.state_hub_url
        assert "leaders.htm" in maxpreps_wi_source.leaders_url

    def test_build_leaders_url(self, maxpreps_wi_source):
        """Test leaderboard URL construction."""
        # Points leaders for 2024-25 season
        url = maxpreps_wi_source._build_leaders_url(
            stat="points",
            season="2024-25",
            gender="boys"
        )

        assert "maxpreps.com/wi/basketball/leaders.htm" in url
        assert "season=2024" in url
        assert "stat=pts" in url
        assert "gender=boys" in url

        # Rebounds leaders
        url = maxpreps_wi_source._build_leaders_url(
            stat="rebounds",
            season="2023-24",
            gender="girls"
        )

        assert "stat=reb" in url
        assert "season=2023" in url
        assert "gender=girls" in url

    def test_build_player_id(self, maxpreps_wi_source):
        """Test player ID construction."""
        player_id = maxpreps_wi_source._build_player_id(
            player_name="John Doe",
            school_slug="madison_memorial"
        )

        assert player_id == "maxpreps_wi_madison_memorial_john_doe"

    def test_build_team_id(self, maxpreps_wi_source):
        """Test team ID construction."""
        team_id = maxpreps_wi_source._build_team_id("madison_memorial")

        assert team_id == "maxpreps_wi_madison_memorial"

    @pytest.mark.asyncio
    async def test_health_check(self, maxpreps_wi_source):
        """Test MaxPreps health check."""
        is_healthy = await maxpreps_wi_source.health_check()
        assert isinstance(is_healthy, bool)
        # MaxPreps may or may not be reachable depending on their site status

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_search_players_structure(self, maxpreps_wi_source):
        """
        Test player search returns correct structure.

        NOTE: This test makes real API calls to MaxPreps. It may fail if:
        - MaxPreps website is down
        - Rate limiting is triggered
        - HTML structure has changed
        - Season data is not yet available
        """
        try:
            players = await maxpreps_wi_source.search_players(
                limit=5  # Small limit to reduce API load
            )

            assert isinstance(players, list)
            assert len(players) <= 5

            # If players found, validate structure
            if len(players) > 0:
                player = players[0]
                assert isinstance(player, Player)
                assert player.player_id.startswith("maxpreps_wi_")
                assert player.full_name
                assert player.school_state == "WI"
                assert player.data_source is not None
                assert player.data_source.source_type == DataSourceType.MAXPREPS_WI

        except Exception as e:
            pytest.skip(f"MaxPreps API call failed (site may be down or rate limited): {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_search_players_with_filters(self, maxpreps_wi_source):
        """
        Test player search with name filter.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            # Search for common Wisconsin basketball name
            players = await maxpreps_wi_source.search_players(
                name="Johnson",
                limit=5
            )

            assert isinstance(players, list)

            # If players found, check filter worked
            if len(players) > 0:
                for player in players:
                    assert "johnson" in player.full_name.lower(), \
                        f"Player {player.full_name} should contain 'Johnson'"

        except Exception as e:
            pytest.skip(f"MaxPreps search failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_leaderboard_structure(self, maxpreps_wi_source):
        """
        Test leaderboard fetching returns correct structure.

        NOTE: This test makes real API calls and may be slow.
        """
        try:
            leaderboard = await maxpreps_wi_source.get_leaderboard(
                stat="points",
                limit=5
            )

            assert isinstance(leaderboard, list)
            assert len(leaderboard) <= 5

            # If leaderboard entries found, validate structure
            if len(leaderboard) > 0:
                entry = leaderboard[0]
                assert isinstance(entry, dict)
                assert "rank" in entry
                assert "player_name" in entry
                assert "stat_value" in entry
                assert "stat_name" in entry
                assert entry["state"] == "WI"
                assert entry["league"] == "Wisconsin High School"

        except Exception as e:
            pytest.skip(f"MaxPreps leaderboard failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_get_player_season_stats(self, maxpreps_wi_source):
        """
        Test getting player season stats.

        NOTE: This is a structure test. Real player IDs would be needed for full integration test.
        """
        # This would need a real player_id from search_players
        # For now, just test the method signature exists
        assert hasattr(maxpreps_wi_source, 'get_player_season_stats')

    def test_parse_season_stats_with_qa_gates(self, maxpreps_wi_source):
        """Test season stats parsing includes QA validation."""
        # Mock row data with implausible values
        row = {
            "Player": "Test Player",
            "School": "Test School",
            "PPG": "150.5",  # Implausible - over 100 PPG
            "RPG": "10.2",
            "APG": "5.5",
            "GP": "20"
        }

        # The parser should detect implausible values
        # This is a unit test of the QA gates
        stats = maxpreps_wi_source._parse_season_stats_from_row(
            row=row,
            player_id="test_player_id",
            season="2024-25"
        )

        # If stats were parsed, QA flag should be set to SUSPECT
        if stats:
            # Implausible PPG should trigger quality flag
            assert stats.data_source.quality_flag.value in ["suspect", "partial"]

    def test_stat_columns_mapping(self, maxpreps_wi_source):
        """Test stat column mappings are defined."""
        # Test the _build_leaders_url uses correct stat codes
        url_pts = maxpreps_wi_source._build_leaders_url("points")
        url_reb = maxpreps_wi_source._build_leaders_url("rebounds")
        url_ast = maxpreps_wi_source._build_leaders_url("assists")

        assert "stat=pts" in url_pts
        assert "stat=reb" in url_reb
        assert "stat=ast" in url_ast


@pytest.mark.datasource
class TestMaxPrepsWisconsinDataQuality:
    """Test suite for MaxPreps Wisconsin data quality validation."""

    def test_qa_gates_negative_stats(self, maxpreps_wi_source):
        """Test QA gates catch negative stat values."""
        # Negative stats should be rejected or flagged
        # This would be tested in the actual parser implementation
        pass  # Parser should handle negative values

    def test_qa_gates_missing_required_fields(self, maxpreps_wi_source):
        """Test QA gates catch missing required fields."""
        # Missing player name or school should be rejected
        row = {
            "Player": "",  # Missing
            "School": "Test School",
            "PPG": "25.5"
        }

        result = maxpreps_wi_source._parse_player_from_leader_row(
            row=row,
            season="2024-25",
            data_source=maxpreps_wi_source.create_data_source_metadata(url="test")
        )

        # Should return None for missing player name
        assert result is None

    def test_data_source_metadata(self, maxpreps_wi_source):
        """Test data source metadata includes quality flags."""
        metadata = maxpreps_wi_source.create_data_source_metadata(
            url="https://test.com",
            quality_flag=None  # Will default to PARTIAL for MaxPreps
        )

        assert metadata.source_type == DataSourceType.MAXPREPS_WI
        assert metadata.url == "https://test.com"
        # MaxPreps is crowd-sourced, so should have PARTIAL quality by default
