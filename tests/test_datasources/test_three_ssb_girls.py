"""
Tests for Adidas 3SSB Girls DataSource Adapter

Basic tests to verify adapter structure and configuration.
"""

import pytest

from src.datasources.us.three_ssb_girls import ThreeSSBGirlsDataSource
from src.models import DataSourceRegion, DataSourceType


class TestThreeSSBGirlsDataSource:
    """Test suite for 3SSB Girls adapter."""

    @pytest.fixture
    def adapter(self):
        """Create 3SSB Girls adapter instance."""
        return ThreeSSBGirlsDataSource()

    def test_initialization(self, adapter):
        """Test adapter initializes correctly."""
        assert adapter is not None
        assert adapter.source_type == DataSourceType.THREE_SSB_GIRLS
        assert adapter.source_name == "Adidas 3SSB Girls"
        assert adapter.region == DataSourceRegion.US
        assert adapter.base_url == "https://adidas3ssb.com/girls"

    def test_endpoints_configured(self, adapter):
        """Test endpoints are properly configured."""
        assert adapter.stats_url == "https://adidas3ssb.com/girls/stats"
        assert adapter.schedule_url == "https://adidas3ssb.com/girls/schedule"
        assert adapter.standings_url == "https://adidas3ssb.com/girls/standings"
        assert adapter.teams_url == "https://adidas3ssb.com/girls/teams"

    def test_player_id_namespace(self, adapter):
        """Test player IDs use correct namespace to avoid collisions."""
        # Girls should use 3ssb_g: prefix
        player_id = adapter._build_player_id("Jane Doe", "Team Elite")
        assert player_id.startswith("3ssb_g:")
        assert "jane_doe" in player_id.lower()

    def test_inherits_from_base_3ssb(self, adapter):
        """Test adapter correctly inherits from ThreeSSBDataSource."""
        from src.datasources.us.three_ssb import ThreeSSBDataSource

        assert isinstance(adapter, ThreeSSBDataSource)

    @pytest.mark.asyncio
    async def test_has_required_methods(self, adapter):
        """Test adapter has all required data fetching methods."""
        assert hasattr(adapter, "search_players")
        assert hasattr(adapter, "get_player")
        assert hasattr(adapter, "get_player_season_stats")
        assert hasattr(adapter, "get_team")
        assert hasattr(adapter, "get_games")
        assert hasattr(adapter, "get_leaderboard")
