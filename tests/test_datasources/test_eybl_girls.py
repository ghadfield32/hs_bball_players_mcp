"""
Nike Girls EYBL DataSource Integration Tests

Tests Girls EYBL datasource with real API calls.
Extends boys EYBL adapter with girls-specific URLs.
"""

import pytest

from src.datasources.us.eybl_girls import EYBLGirlsDataSource
from src.models import Player, PlayerSeasonStats


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestEYBLGirlsDataSource:
    """Test suite for Girls EYBL datasource with real API calls."""

    @pytest.fixture
    async def datasource(self):
        """Create Girls EYBL datasource instance."""
        ds = EYBLGirlsDataSource()
        yield ds
        await ds.close()

    @pytest.mark.asyncio
    async def test_health_check(self, datasource):
        """Test Girls EYBL health check."""
        is_healthy = await datasource.health_check()
        assert is_healthy is True, "Girls EYBL datasource should be healthy"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, datasource):
        """Test searching players by name."""
        # Search for a common name
        players = await datasource.search_players(name="Johnson", limit=5)

        assert isinstance(players, list), "Should return a list"
        # Results depend on current season roster
        if len(players) > 0:
            assert len(players) <= 5, "Should respect limit parameter"

            # Validate player structure
            for player in players:
                assert isinstance(player, Player), "Should return Player objects"
                assert player.name, "Player should have a name"
                assert player.player_id, "Player should have an ID"
                assert player.player_id.startswith("eybl_girls_"), "Girls EYBL players should have eybl_girls_ prefix"

                # Check data source metadata
                assert player.data_source is not None, "Should have data source metadata"
                assert player.data_source.source_type.value == "eybl_girls"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, datasource):
        """Test searching players by team."""
        # Search for players from a team
        players = await datasource.search_players(team="All-Ohio", limit=10)

        # Team might not exist in current season
        for player in players:
            assert isinstance(player, Player)
            # If team filter works, team should match
            if player.team_name:
                assert "ohio" in player.team_name.lower() or "all-ohio" in player.team_name.lower()

    @pytest.mark.asyncio
    async def test_search_players_no_results(self, datasource):
        """Test search with no matching results."""
        # Search for impossible name
        players = await datasource.search_players(name="XyZqWvUiOpAsD", limit=5)

        assert isinstance(players, list)
        assert len(players) == 0, "Should return empty list for no matches"

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, datasource):
        """Test getting player season statistics."""
        # First find a player
        players = await datasource.search_players(limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Get season stats
            stats = await datasource.get_player_season_stats(player_id)

            if stats is not None:
                assert isinstance(stats, PlayerSeasonStats)
                assert stats.player_id == player_id
                assert stats.season is not None
                assert stats.games_played >= 0

    @pytest.mark.asyncio
    async def test_get_leaderboard_default(self, datasource):
        """Test getting default leaderboard (points)."""
        leaderboard = await datasource.get_leaderboard(limit=10)

        assert isinstance(leaderboard, list)
        # Leaderboard might be empty if season hasn't started
        for entry in leaderboard:
            assert isinstance(entry, dict)
            assert "player_name" in entry
            assert "rank" in entry

    @pytest.mark.asyncio
    async def test_source_metadata(self, datasource):
        """Test that source metadata is correctly set for Girls EYBL."""
        assert datasource.source_type.value == "eybl_girls"
        assert datasource.source_name == "Nike Girls EYBL"
        assert datasource.base_url == "https://nikeeyb.com/girls"
        assert datasource.stats_url == "https://nikeeyb.com/girls/cumulative-season-stats"
        assert datasource.schedule_url == "https://nikeeyb.com/girls/schedule"
        assert datasource.standings_url == "https://nikeeyb.com/girls/standings"

    @pytest.mark.asyncio
    async def test_inheritance_from_eybl(self, datasource):
        """Test that Girls EYBL properly inherits from EYBL base class."""
        # Should have all the same methods as EYBL
        assert hasattr(datasource, 'search_players')
        assert hasattr(datasource, 'get_player_season_stats')
        assert hasattr(datasource, 'get_leaderboard')
        assert hasattr(datasource, 'get_team')
        assert hasattr(datasource, 'get_games')

    @pytest.mark.asyncio
    async def test_rate_limiting(self, datasource):
        """Test that rate limiting is configured."""
        assert datasource.rate_limiter is not None
        assert datasource.requests_per_minute > 0


@pytest.mark.unit
class TestEYBLGirlsConfiguration:
    """Unit tests for Girls EYBL configuration."""

    def test_girls_eybl_urls(self):
        """Test that Girls EYBL uses correct URLs."""
        ds = EYBLGirlsDataSource()

        # Should use girls-specific URLs
        assert "/girls" in ds.base_url
        assert "/girls" in ds.stats_url
        assert "/girls" in ds.schedule_url
        assert "/girls" in ds.standings_url

    def test_source_type(self):
        """Test that source type is set correctly."""
        ds = EYBLGirlsDataSource()
        assert ds.source_type.value == "eybl_girls"
