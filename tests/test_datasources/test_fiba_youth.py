"""
FIBA Youth DataSource Integration Tests

Tests FIBA Youth datasource with real API calls.
"""

import pytest

from src.models import Player


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestFIBAYouthDataSource:
    """Test suite for FIBA Youth datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, fiba_source):
        """Test FIBA health check."""
        is_healthy = await fiba_source.health_check()
        assert is_healthy is True, "FIBA datasource should be healthy"

    @pytest.mark.asyncio
    async def test_search_players(self, fiba_source):
        """Test searching players from FIBA Youth."""
        players = await fiba_source.search_players(limit=5)

        assert isinstance(players, list)

        if len(players) > 0:
            assert len(players) <= 5

            for player in players:
                assert isinstance(player, Player)
                assert player.player_id.startswith("fiba_")
                assert player.full_name

                # FIBA is European, so should have European locations
                assert player.data_source is not None
                assert player.data_source.source_type.value == "fiba"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, fiba_source):
        """Test searching FIBA players by name."""
        players = await fiba_source.search_players(name="Silva", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            if player.full_name:
                assert "silva" in player.full_name.lower()

    @pytest.mark.asyncio
    async def test_european_data(self, fiba_source):
        """Test that FIBA data reflects European players."""
        players = await fiba_source.search_players(limit=3)

        if len(players) > 0:
            for player in players:
                # Should have country data for European players
                assert player.school_country is not None or player.nationality is not None

    @pytest.mark.asyncio
    async def test_get_player_by_id(self, fiba_source):
        """Test getting a specific FIBA player."""
        players = await fiba_source.search_players(limit=1)

        if len(players) > 0:
            player_id = players[0].player_id
            player = await fiba_source.get_player(player_id)

            if player:
                assert isinstance(player, Player)
                assert player.player_id == player_id

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, fiba_source):
        """Test getting FIBA player season stats."""
        players = await fiba_source.search_players(limit=1)

        if len(players) > 0:
            stats = await fiba_source.get_player_season_stats(players[0].player_id)

            if stats:
                assert stats.player_id == players[0].player_id
                # FIBA leagues vary
                assert stats.league is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, fiba_source):
        """Test getting FIBA leaderboard."""
        leaderboard = await fiba_source.get_leaderboard(
            stat="points_per_game",
            limit=10
        )

        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 10

        for entry in leaderboard:
            assert isinstance(entry, dict)

    @pytest.mark.asyncio
    async def test_error_handling(self, fiba_source):
        """Test FIBA error handling."""
        # Invalid player ID
        player = await fiba_source.get_player("fiba_invalid_12345")
        assert player is None or isinstance(player, Player)

        # No results search
        players = await fiba_source.search_players(name="XyZqWvUiOpAsD", limit=5)
        assert isinstance(players, list)
        assert len(players) == 0
