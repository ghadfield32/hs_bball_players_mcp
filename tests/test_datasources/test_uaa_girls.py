"""
Tests for UAA Girls / UA Next DataSource Adapter

Basic tests to verify adapter structure and configuration.
"""

import pytest

from src.datasources.us.uaa_girls import UAAGirlsDataSource
from src.models import DataSourceRegion, DataSourceType


class TestUAAGirlsDataSource:
    """Test suite for UAA Girls / UA Next adapter."""

    @pytest.fixture
    def adapter(self):
        """Create UAA Girls adapter instance."""
        return UAAGirlsDataSource()

    def test_initialization(self, adapter):
        """Test adapter initializes correctly."""
        assert adapter is not None
        assert adapter.source_type == DataSourceType.UAA_GIRLS
        assert adapter.source_name == "UA Next (Girls UAA)"
        assert adapter.region == DataSourceRegion.US
        assert adapter.base_url == "https://uanext.com"

    def test_endpoints_configured(self, adapter):
        """Test endpoints are properly configured."""
        assert adapter.stats_url == "https://uanext.com/stats"
        assert adapter.schedule_url == "https://uanext.com/schedule"
        assert adapter.standings_url == "https://uanext.com/standings"
        assert adapter.teams_url == "https://uanext.com/teams"
        assert adapter.events_url == "https://uanext.com/events"

    def test_player_id_namespace(self, adapter):
        """Test player IDs use correct namespace to avoid collisions."""
        # Girls should use uaa_g: prefix
        player_id = adapter._build_player_id("Jane Doe", "Team Elite", "2024")
        assert player_id.startswith("uaa_g:")
        assert "jane_doe" in player_id.lower()
        assert "2024" in player_id

    def test_team_id_namespace(self, adapter):
        """Test team IDs use correct namespace."""
        team_id = adapter._build_team_id("Team Elite", "17U")
        assert team_id.startswith("uaa_g:team_")
        assert "17u" in team_id.lower()

    def test_inherits_from_base_uaa(self, adapter):
        """Test adapter correctly inherits from UAADataSource."""
        from src.datasources.us.uaa import UAADataSource

        assert isinstance(adapter, UAADataSource)

    @pytest.mark.asyncio
    async def test_has_required_methods(self, adapter):
        """Test adapter has all required data fetching methods."""
        assert hasattr(adapter, "search_players")
        assert hasattr(adapter, "get_player")
        assert hasattr(adapter, "get_player_season_stats")
        assert hasattr(adapter, "get_team")
        assert hasattr(adapter, "get_games")
        assert hasattr(adapter, "get_leaderboard")

    def test_girls_namespace_differs_from_boys(self):
        """Test that girls and boys UAA use different ID namespaces."""
        from src.datasources.us.uaa import UAADataSource

        boys_adapter = UAADataSource()
        girls_adapter = UAAGirlsDataSource()

        boys_id = boys_adapter._build_player_id("Same Player", "Same Team")
        girls_id = girls_adapter._build_player_id("Same Player", "Same Team")

        # Verify they have different prefixes
        assert boys_id.startswith("uaa:")
        assert girls_id.startswith("uaa_g:")
        assert boys_id != girls_id
