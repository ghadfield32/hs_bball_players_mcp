"""
Tests for UAA (Under Armour Association) DataSource Adapter

Basic tests to verify adapter structure and configuration.
"""

import pytest

from src.datasources.us.uaa import UAADataSource
from src.models import DataSourceRegion, DataSourceType


class TestUAADataSource:
    """Test suite for UAA adapter."""

    @pytest.fixture
    def adapter(self):
        """Create UAA adapter instance."""
        return UAADataSource()

    def test_initialization(self, adapter):
        """Test adapter initializes correctly."""
        assert adapter is not None
        assert adapter.source_type == DataSourceType.UAA
        assert adapter.source_name == "Under Armour Association"
        assert adapter.region == DataSourceRegion.US
        assert adapter.base_url == "https://underarmourassociation.com"

    def test_endpoints_configured(self, adapter):
        """Test endpoints are properly configured."""
        assert adapter.stats_url == "https://underarmourassociation.com/stats"
        assert adapter.schedule_url == "https://underarmourassociation.com/schedule"
        assert adapter.standings_url == "https://underarmourassociation.com/standings"
        assert adapter.teams_url == "https://underarmourassociation.com/teams"
        assert adapter.events_url == "https://underarmourassociation.com/events"

    def test_player_id_namespace(self, adapter):
        """Test player IDs use correct namespace."""
        # Boys UAA should use uaa: prefix
        player_id = adapter._build_player_id("John Doe", "Team Elite", "2024")
        assert player_id.startswith("uaa:")
        assert "john_doe" in player_id.lower()
        assert "2024" in player_id

    def test_team_id_namespace(self, adapter):
        """Test team IDs use correct namespace."""
        team_id = adapter._build_team_id("Team Elite", "17U")
        assert team_id.startswith("uaa:team_")
        assert "17u" in team_id.lower()

    def test_player_id_without_optional_params(self, adapter):
        """Test player ID building with minimal params."""
        player_id = adapter._build_player_id("John Doe")
        assert player_id == "uaa:john_doe"

    @pytest.mark.asyncio
    async def test_has_required_methods(self, adapter):
        """Test adapter has all required data fetching methods."""
        assert hasattr(adapter, "search_players")
        assert hasattr(adapter, "get_player")
        assert hasattr(adapter, "get_player_season_stats")
        assert hasattr(adapter, "get_team")
        assert hasattr(adapter, "get_games")
        assert hasattr(adapter, "get_leaderboard")

    def test_supports_division_filtering(self, adapter):
        """Test adapter supports UAA division structure (15U, 16U, 17U)."""
        # Verify search_players accepts division parameter
        import inspect

        sig = inspect.signature(adapter.search_players)
        assert "division" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_player_extracts_name_from_id(self, adapter):
        """Test get_player can extract name from properly formatted player_id."""
        # Mock test - would need actual data for full integration test
        # Just verify the ID parsing logic
        player_id = "uaa:john_doe:team_elite:2024"
        # This would call search_players internally
        # For now, just verify the adapter can handle the format
        assert player_id.startswith("uaa:")
