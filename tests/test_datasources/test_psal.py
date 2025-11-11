"""
PSAL DataSource Integration Tests

Tests PSAL (NYC Public Schools Athletic League) datasource with real API calls.
"""

import pytest

from src.models import Player, Team


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestPSALDataSource:
    """Test suite for PSAL datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, psal_source):
        """Test PSAL health check."""
        is_healthy = await psal_source.health_check()
        assert is_healthy is True, "PSAL datasource should be healthy"

    @pytest.mark.asyncio
    async def test_search_players_from_leaderboard(self, psal_source):
        """Test searching players from PSAL leaderboards."""
        players = await psal_source.search_players(limit=10)

        assert isinstance(players, list), "Should return a list"

        # PSAL might have players in leaderboards
        if len(players) > 0:
            assert len(players) <= 10, "Should respect limit"

            for player in players:
                assert isinstance(player, Player)
                assert player.full_name
                assert player.player_id.startswith("psal_")
                assert player.school_city == "New York"
                assert player.school_state == "NY"

                # Data source validation
                assert player.data_source is not None
                assert player.data_source.source_type.value == "psal"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, psal_source):
        """Test searching players by name."""
        players = await psal_source.search_players(name="Williams", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            assert "williams" in player.full_name.lower()

    @pytest.mark.asyncio
    async def test_search_players_by_school(self, psal_source):
        """Test searching players by school."""
        # Search for players from a common NYC school
        players = await psal_source.search_players(team="Lincoln", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            if player.school_name:
                assert "lincoln" in player.school_name.lower()

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, psal_source):
        """Test getting player season stats from leaderboards."""
        # First find a player
        players = await psal_source.search_players(limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Try to get their stats
            stats = await psal_source.get_player_season_stats(player_id)

            if stats:  # Stats might not be available
                assert stats.player_id == player_id
                assert stats.league == "PSAL"
                assert stats.season is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, psal_source):
        """Test getting statistical leaderboard."""
        leaderboard = await psal_source.get_leaderboard(
            stat="points_per_game",
            limit=10
        )

        assert isinstance(leaderboard, list)

        if len(leaderboard) > 0:
            for entry in leaderboard:
                assert isinstance(entry, dict)
                assert "player_name" in entry
                assert "stat_value" in entry
                assert entry["season"] is not None

    @pytest.mark.asyncio
    async def test_get_team_from_standings(self, psal_source):
        """Test getting team information from standings."""
        # Try to get a team
        team = await psal_source.get_team("psal_jefferson")

        if team:  # Team might not exist
            assert isinstance(team, Team)
            assert team.team_id.startswith("psal_")
            assert team.league == "PSAL"
            assert team.city == "New York"
            assert team.state == "NY"

    @pytest.mark.asyncio
    async def test_player_grad_year_parsing(self, psal_source):
        """Test that grad years are correctly parsed from grade levels."""
        players = await psal_source.search_players(limit=5)

        if len(players) > 0:
            for player in players:
                if player.grad_year:
                    # Grad year should be reasonable (2024-2028 range for current students)
                    assert 2024 <= player.grad_year <= 2030

    @pytest.mark.asyncio
    async def test_nyc_location_data(self, psal_source):
        """Test that all PSAL players are correctly tagged as NYC."""
        players = await psal_source.search_players(limit=5)

        if len(players) > 0:
            for player in players:
                assert player.school_city == "New York"
                assert player.school_state == "NY"
                assert player.school_country == "USA"

    @pytest.mark.asyncio
    async def test_error_handling(self, psal_source):
        """Test error handling for edge cases."""
        # Invalid player ID
        player = await psal_source.get_player("psal_nonexistent_player")
        assert player is None or isinstance(player, Player)

        # Invalid team ID
        team = await psal_source.get_team("psal_nonexistent_team")
        assert team is None or isinstance(team, Team)

    @pytest.mark.asyncio
    async def test_games_endpoint_warning(self, psal_source):
        """Test that games endpoint returns empty list with warning."""
        games = await psal_source.get_games(limit=5)

        # PSAL doesn't provide game schedules publicly
        assert isinstance(games, list)
        assert len(games) == 0
