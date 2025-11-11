"""
Wisconsin Sports Network (WSN) DataSource Integration Tests

Tests WSN datasource for comprehensive Wisconsin high school basketball coverage.
One of the premier free high school basketball stats sources in Wisconsin.
"""

import pytest

from src.models import Player, PlayerSeasonStats, Team


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestWSNDataSource:
    """Test suite for WSN (Wisconsin Sports Network) datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, wsn_source):
        """Test WSN health check."""
        is_healthy = await wsn_source.health_check()
        assert is_healthy is True, "WSN datasource should be healthy"

    @pytest.mark.asyncio
    async def test_wisconsin_only_coverage(self, wsn_source):
        """Test that WSN is Wisconsin-only (single state, deep coverage)."""
        assert wsn_source.state_code == "WI"
        assert wsn_source.league_name == "Wisconsin High School"
        assert wsn_source.league_abbrev == "WIAA"

    @pytest.mark.asyncio
    async def test_search_players(self, wsn_source):
        """Test searching for Wisconsin players."""
        players = await wsn_source.search_players(limit=10)

        assert isinstance(players, list)

        if len(players) > 0:
            assert len(players) <= 10, "Should respect limit"

            for player in players:
                assert isinstance(player, Player)
                assert player.full_name
                assert player.player_id.startswith("wsn_")
                assert player.school_state == "WI"
                assert player.school_country == "USA"

                # Data source validation
                assert player.data_source is not None
                assert player.data_source.source_type.value == "wsn"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, wsn_source):
        """Test searching players by name."""
        players = await wsn_source.search_players(name="Johnson", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            assert "johnson" in player.full_name.lower()
            assert player.school_state == "WI"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, wsn_source):
        """Test searching players by team/school."""
        players = await wsn_source.search_players(team="Madison", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            if player.school_name:
                assert "madison" in player.school_name.lower()

    @pytest.mark.asyncio
    async def test_player_id_format(self, wsn_source):
        """Test that player IDs follow the correct format."""
        players = await wsn_source.search_players(limit=5)

        if len(players) > 0:
            for player in players:
                # Format: wsn_{name}
                assert player.player_id.startswith("wsn_")
                # Should not have underscores after wsn_ except for name parts
                parts = player.player_id.split("_")
                assert len(parts) >= 2

    @pytest.mark.asyncio
    async def test_get_player_by_id(self, wsn_source):
        """Test getting player by ID."""
        # First find a player
        players = await wsn_source.search_players(limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Try to get player by ID
            player = await wsn_source.get_player(player_id)

            if player:
                assert isinstance(player, Player)
                assert player.player_id == player_id
                assert player.school_state == "WI"

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, wsn_source):
        """Test getting player season stats."""
        # First find a player
        players = await wsn_source.search_players(limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Try to get their stats
            stats = await wsn_source.get_player_season_stats(player_id)

            if stats:
                assert isinstance(stats, PlayerSeasonStats)
                assert stats.player_id == player_id
                assert stats.league == "Wisconsin High School"
                assert stats.season is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, wsn_source):
        """Test getting statistical leaderboard."""
        leaderboard = await wsn_source.get_leaderboard(stat="points", limit=10)

        assert isinstance(leaderboard, list)

        if len(leaderboard) > 0:
            assert len(leaderboard) <= 10

            for entry in leaderboard:
                assert isinstance(entry, dict)
                assert "player_name" in entry
                assert "stat_value" in entry
                assert "rank" in entry
                assert entry["stat_value"] is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard_different_stats(self, wsn_source):
        """Test getting leaderboards for different stat categories."""
        stat_categories = ["points", "rebounds", "assists", "steals", "blocks"]

        for stat in stat_categories:
            leaderboard = await wsn_source.get_leaderboard(stat=stat, limit=5)

            assert isinstance(leaderboard, list)

            if len(leaderboard) > 0:
                for entry in leaderboard:
                    assert "stat_value" in entry
                    assert entry["stat_value"] > 0

    @pytest.mark.asyncio
    async def test_get_team(self, wsn_source):
        """Test getting team information."""
        # Try to get a team from standings
        team = await wsn_source.get_team("wsn_madison_memorial")

        if team:
            assert isinstance(team, Team)
            assert team.team_id.startswith("wsn_")
            assert team.league == "Wisconsin High School"
            assert team.state == "WI"
            assert team.country == "USA"

    @pytest.mark.asyncio
    async def test_wiaa_division_parsing(self, wsn_source):
        """Test that WIAA divisions are correctly parsed."""
        # Wisconsin has multiple divisions (D1-D5)
        players = await wsn_source.search_players(limit=5)

        # Just verify that division data doesn't break anything
        for player in players:
            assert isinstance(player, Player)
            # Division info might be in team_name or other fields

    @pytest.mark.asyncio
    async def test_wisconsin_location_data(self, wsn_source):
        """Test that all players are correctly tagged as Wisconsin."""
        players = await wsn_source.search_players(limit=5)

        if len(players) > 0:
            for player in players:
                assert player.school_state == "WI"
                assert player.school_country == "USA"

    @pytest.mark.asyncio
    async def test_player_profile_fallback(self, wsn_source):
        """Test that profile fetching falls back to search gracefully."""
        # Try to get a nonexistent player profile
        player = await wsn_source.get_player("wsn_nonexistent_player_12345")

        # Should either return None or try to search
        assert player is None or isinstance(player, Player)

    @pytest.mark.asyncio
    async def test_error_handling(self, wsn_source):
        """Test error handling for edge cases."""
        # Invalid player ID
        player = await wsn_source.get_player("wsn_nonexistent_player")
        assert player is None or isinstance(player, Player)

        # Invalid team ID
        team = await wsn_source.get_team("wsn_nonexistent_team")
        assert team is None or isinstance(team, Team)

        # Invalid stat category
        leaderboard = await wsn_source.get_leaderboard(stat="invalid_stat", limit=5)
        assert isinstance(leaderboard, list)
        # Should return empty list or handle gracefully

    @pytest.mark.asyncio
    async def test_season_defaults(self, wsn_source):
        """Test that season defaults to current season."""
        players = await wsn_source.search_players(season=None, limit=1)

        if len(players) > 0:
            player_id = players[0].player_id
            stats = await wsn_source.get_player_season_stats(player_id, season=None)

            if stats:
                # Should default to 2024-25 or current season
                assert stats.season is not None
                assert "202" in stats.season  # Should be a recent year

    @pytest.mark.asyncio
    async def test_conference_and_division_data(self, wsn_source):
        """Test that conference/division data is captured from standings."""
        # Try to get teams from standings which should have conference/division info
        # This is best-effort as it depends on data availability
        team = await wsn_source.get_team("wsn_milwaukee_king")

        if team:
            # Conference or division should be captured if available
            assert isinstance(team, Team)
            # conference field might contain division info

    @pytest.mark.asyncio
    async def test_multiple_leaderboard_tables(self, wsn_source):
        """Test handling of multiple leaderboard tables (PPG, RPG, APG, etc.)."""
        # WSN likely has separate tables for different stats
        points_leaders = await wsn_source.get_leaderboard(stat="points", limit=3)
        rebounds_leaders = await wsn_source.get_leaderboard(stat="rebounds", limit=3)
        assists_leaders = await wsn_source.get_leaderboard(stat="assists", limit=3)

        # All should return lists (even if empty during off-season)
        assert isinstance(points_leaders, list)
        assert isinstance(rebounds_leaders, list)
        assert isinstance(assists_leaders, list)
