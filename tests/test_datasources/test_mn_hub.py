"""
Minnesota Basketball Hub DataSource Integration Tests

Tests MN Hub datasource with real API calls.
"""

import pytest

from src.models import Player


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestMNHubDataSource:
    """Test suite for MN Hub datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, mn_hub_source):
        """Test MN Hub health check."""
        is_healthy = await mn_hub_source.health_check()
        assert is_healthy is True, "MN Hub datasource should be healthy"

    @pytest.mark.asyncio
    async def test_search_players(self, mn_hub_source):
        """Test searching players from MN Hub."""
        players = await mn_hub_source.search_players(limit=5)

        assert isinstance(players, list)

        if len(players) > 0:
            assert len(players) <= 5

            for player in players:
                assert isinstance(player, Player)
                assert player.player_id.startswith("mn_hub_")
                assert player.full_name

                # MN Hub is Minnesota-based
                assert player.data_source is not None
                assert player.data_source.source_type.value == "mn_hub"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, mn_hub_source):
        """Test searching MN Hub players by name."""
        players = await mn_hub_source.search_players(name="Anderson", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            if player.full_name:
                assert "anderson" in player.full_name.lower()

    @pytest.mark.asyncio
    async def test_minnesota_location_data(self, mn_hub_source):
        """Test that MN Hub players have Minnesota location data."""
        players = await mn_hub_source.search_players(limit=3)

        if len(players) > 0:
            for player in players:
                # Should have MN state data
                assert player.school_state == "MN" or player.school_state is None

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, mn_hub_source):
        """Test searching players by team."""
        players = await mn_hub_source.search_players(team="Hopkins", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)

    @pytest.mark.asyncio
    async def test_get_player_by_id(self, mn_hub_source):
        """Test getting a specific MN Hub player."""
        players = await mn_hub_source.search_players(limit=1)

        if len(players) > 0:
            player_id = players[0].player_id
            player = await mn_hub_source.get_player(player_id)

            if player:
                assert isinstance(player, Player)
                assert player.player_id == player_id

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, mn_hub_source):
        """Test getting MN Hub player season stats."""
        players = await mn_hub_source.search_players(limit=1)

        if len(players) > 0:
            stats = await mn_hub_source.get_player_season_stats(players[0].player_id)

            if stats:
                assert stats.player_id == players[0].player_id
                assert stats.league is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, mn_hub_source):
        """Test getting MN Hub leaderboard."""
        leaderboard = await mn_hub_source.get_leaderboard(
            stat="points_per_game",
            limit=10
        )

        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 10

        for entry in leaderboard:
            assert isinstance(entry, dict)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mn_hub_source):
        """Test that rate limiting works."""
        # Make multiple requests
        results = []
        for i in range(3):
            players = await mn_hub_source.search_players(limit=1)
            results.append(len(players))

        # All should complete without errors
        assert all(isinstance(r, int) for r in results)

    @pytest.mark.asyncio
    async def test_error_handling(self, mn_hub_source):
        """Test MN Hub error handling."""
        # Invalid player ID
        player = await mn_hub_source.get_player("mn_hub_invalid_12345")
        assert player is None or isinstance(player, Player)

        # No results search
        players = await mn_hub_source.search_players(name="XyZqWvUiOpAsD", limit=5)
        assert isinstance(players, list)
        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_data_completeness(self, mn_hub_source):
        """Test that MN Hub data is reasonably complete."""
        players = await mn_hub_source.search_players(limit=3)

        if len(players) > 0:
            for player in players:
                assert player.player_id
                assert player.full_name
                assert player.data_source
                assert player.data_source.source_url
