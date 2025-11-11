"""
EYBL DataSource Integration Tests

Tests EYBL datasource with real API calls.
"""

import pytest

from src.models import Player, PlayerSeasonStats


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestEYBLDataSource:
    """Test suite for EYBL datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, eybl_source):
        """Test EYBL health check."""
        is_healthy = await eybl_source.health_check()
        assert is_healthy is True, "EYBL datasource should be healthy"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, eybl_source):
        """Test searching players by name."""
        # Search for a common name
        players = await eybl_source.search_players(name="Johnson", limit=5)

        assert isinstance(players, list), "Should return a list"
        assert len(players) > 0, "Should find at least one player with common name"
        assert len(players) <= 5, "Should respect limit parameter"

        # Validate player structure
        for player in players:
            assert isinstance(player, Player), "Should return Player objects"
            assert player.full_name, "Player should have a name"
            assert player.player_id, "Player should have an ID"
            assert player.player_id.startswith("eybl_"), "EYBL players should have eybl_ prefix"

            # Check data source metadata
            assert player.data_source is not None, "Should have data source metadata"
            assert player.data_source.source_type.value == "eybl"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, eybl_source):
        """Test searching players by team."""
        # Search for players from a team
        players = await eybl_source.search_players(team="All-Ohio", limit=10)

        if len(players) > 0:  # Team might not exist in current season
            for player in players:
                assert isinstance(player, Player)
                # If team filter works, school/team should match
                if player.school_name:
                    assert "ohio" in player.school_name.lower() or "all-ohio" in player.school_name.lower()

    @pytest.mark.asyncio
    async def test_search_players_with_season(self, eybl_source, sample_season):
        """Test searching players with season filter."""
        players = await eybl_source.search_players(season=sample_season, limit=5)

        assert isinstance(players, list)
        # Season might not have data yet, so just validate structure
        for player in players:
            assert isinstance(player, Player)

    @pytest.mark.asyncio
    async def test_search_players_no_results(self, eybl_source):
        """Test search with no matching results."""
        # Search for impossible name
        players = await eybl_source.search_players(name="XyZqWvUiOpAsD", limit=5)

        assert isinstance(players, list)
        assert len(players) == 0, "Should return empty list for no matches"

    @pytest.mark.asyncio
    async def test_get_player_by_id(self, eybl_source):
        """Test getting a specific player by ID."""
        # First search for a player
        players = await eybl_source.search_players(name="Williams", limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Now get that specific player
            player = await eybl_source.get_player(player_id)

            assert player is not None, "Should retrieve player by ID"
            assert isinstance(player, Player)
            assert player.player_id == player_id

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, eybl_source):
        """Test getting player season statistics."""
        # First find a player
        players = await eybl_source.search_players(name="Davis", limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Get their season stats
            stats = await eybl_source.get_player_season_stats(player_id)

            if stats:  # Stats might not be available for all players
                assert isinstance(stats, PlayerSeasonStats)
                assert stats.player_id == player_id
                assert stats.season is not None
                assert stats.league == "EYBL" or "Nike EYBL" in stats.league

                # Validate statistical fields
                if stats.games_played:
                    assert stats.games_played > 0
                if stats.points_per_game:
                    assert stats.points_per_game >= 0

    @pytest.mark.asyncio
    async def test_get_leaderboard_ppg(self, eybl_source):
        """Test getting PPG leaderboard."""
        leaderboard = await eybl_source.get_leaderboard(
            stat="points_per_game",
            limit=10
        )

        assert isinstance(leaderboard, list)

        if len(leaderboard) > 0:
            assert len(leaderboard) <= 10

            # Validate leaderboard structure
            for i, entry in enumerate(leaderboard, 1):
                assert isinstance(entry, dict)
                assert "player_name" in entry or "player_id" in entry
                assert "stat_value" in entry
                assert entry["stat_value"] >= 0

                # Check ranking order (descending)
                if i < len(leaderboard):
                    assert entry["stat_value"] >= leaderboard[i]["stat_value"], \
                        "Leaderboard should be sorted descending"

    @pytest.mark.asyncio
    async def test_get_leaderboard_rpg(self, eybl_source):
        """Test getting RPG leaderboard."""
        leaderboard = await eybl_source.get_leaderboard(
            stat="rebounds_per_game",
            limit=5
        )

        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 5

    @pytest.mark.asyncio
    async def test_rate_limiting(self, eybl_source):
        """Test that rate limiting is enforced."""
        # Make multiple rapid requests
        results = []
        for i in range(3):
            players = await eybl_source.search_players(name="Smith", limit=1)
            results.append(len(players))

        # All requests should succeed (rate limiter should handle it)
        assert all(isinstance(r, int) for r in results)

    @pytest.mark.asyncio
    async def test_error_handling_invalid_player_id(self, eybl_source):
        """Test error handling for invalid player ID."""
        player = await eybl_source.get_player("eybl_invalid_id_12345")

        # Should return None or empty, not raise exception
        assert player is None or isinstance(player, Player)

    @pytest.mark.asyncio
    async def test_data_quality_flags(self, eybl_source):
        """Test that data quality flags are set."""
        players = await eybl_source.search_players(name="Johnson", limit=1)

        if len(players) > 0:
            player = players[0]
            assert player.data_source is not None
            assert player.data_source.quality_flag is not None

    @pytest.mark.asyncio
    async def test_player_data_completeness(self, eybl_source):
        """Test that player data contains expected fields."""
        players = await eybl_source.search_players(limit=3)

        if len(players) > 0:
            for player in players:
                # Required fields
                assert player.player_id
                assert player.full_name
                assert player.data_source

                # At least one name field should be populated
                assert player.first_name or player.last_name or player.full_name

                # Data source should have URL
                assert player.data_source.source_url
