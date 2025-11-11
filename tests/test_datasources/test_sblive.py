"""
SBLive Sports DataSource Integration Tests

Tests SBLive Sports datasource covering 6 West Coast states:
WA, OR, CA, AZ, ID, NV
"""

import pytest

from src.models import Player, PlayerSeasonStats, Team


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestSBLiveDataSource:
    """Test suite for SBLive datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, sblive_source):
        """Test SBLive health check."""
        is_healthy = await sblive_source.health_check()
        assert is_healthy is True, "SBLive datasource should be healthy"

    @pytest.mark.asyncio
    async def test_supported_states(self, sblive_source):
        """Test that SBLive supports the correct states."""
        expected_states = ["WA", "OR", "CA", "AZ", "ID", "NV"]
        assert sblive_source.SUPPORTED_STATES == expected_states
        assert len(sblive_source.state_urls) == 6

    @pytest.mark.asyncio
    async def test_search_players_washington(self, sblive_source):
        """Test searching players in Washington state."""
        players = await sblive_source.search_players(state="WA", limit=10)

        assert isinstance(players, list)

        if len(players) > 0:
            assert len(players) <= 10, "Should respect limit"

            for player in players:
                assert isinstance(player, Player)
                assert player.full_name
                assert player.player_id.startswith("sblive_wa_")
                assert player.school_state == "WA"
                assert player.school_country == "USA"

                # Data source validation
                assert player.data_source is not None
                assert player.data_source.source_type.value == "sblive"

    @pytest.mark.asyncio
    async def test_search_players_california(self, sblive_source):
        """Test searching players in California state."""
        players = await sblive_source.search_players(state="CA", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            assert player.player_id.startswith("sblive_ca_")
            assert player.school_state == "CA"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, sblive_source):
        """Test searching players by name in a state."""
        players = await sblive_source.search_players(
            state="WA", name="Johnson", limit=5
        )

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            assert "johnson" in player.full_name.lower()
            assert player.school_state == "WA"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, sblive_source):
        """Test searching players by team/school."""
        players = await sblive_source.search_players(
            state="WA", team="Roosevelt", limit=5
        )

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            if player.school_name:
                assert "roosevelt" in player.school_name.lower()

    @pytest.mark.asyncio
    async def test_state_validation(self, sblive_source):
        """Test that invalid states are rejected."""
        with pytest.raises(ValueError):
            await sblive_source.search_players(state="TX", limit=5)

        with pytest.raises(ValueError):
            await sblive_source.search_players(state="INVALID", limit=5)

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, sblive_source):
        """Test getting player season stats."""
        # First find a player
        players = await sblive_source.search_players(state="WA", limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Try to get their stats
            stats = await sblive_source.get_player_season_stats(player_id)

            if stats:
                assert isinstance(stats, PlayerSeasonStats)
                assert stats.player_id == player_id
                assert "SBLive" in stats.league
                assert stats.season is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard_by_state(self, sblive_source):
        """Test getting state-specific leaderboard."""
        leaderboard = await sblive_source.get_leaderboard(
            stat="points", state="WA", limit=10
        )

        assert isinstance(leaderboard, list)

        if len(leaderboard) > 0:
            for entry in leaderboard:
                assert isinstance(entry, dict)
                assert "player_name" in entry
                assert "stat_value" in entry
                assert "state" in entry
                assert entry["state"] == "WA"
                assert "SBLive Washington" in entry["league"]

    @pytest.mark.asyncio
    async def test_get_leaderboards_all_states(self, sblive_source):
        """Test getting leaderboards for all states at once."""
        all_leaderboards = await sblive_source.get_leaderboards_all_states(
            stat="points", limit=5
        )

        assert isinstance(all_leaderboards, dict)
        assert len(all_leaderboards) == 6  # Should have all 6 states

        for state in ["WA", "OR", "CA", "AZ", "ID", "NV"]:
            assert state in all_leaderboards
            assert isinstance(all_leaderboards[state], list)

    @pytest.mark.asyncio
    async def test_get_team(self, sblive_source):
        """Test getting team information."""
        # Try to get a team
        team = await sblive_source.get_team("sblive_wa_team_garfield", state="WA")

        if team:
            assert isinstance(team, Team)
            assert team.team_id.startswith("sblive_wa_")
            assert "SBLive Washington" in team.league
            assert team.state == "WA"
            assert team.country == "USA"

    @pytest.mark.asyncio
    async def test_player_id_format(self, sblive_source):
        """Test that player IDs follow the correct format."""
        players = await sblive_source.search_players(state="OR", limit=5)

        if len(players) > 0:
            for player in players:
                # Format: sblive_{state}_{name}
                assert player.player_id.startswith("sblive_or_")
                parts = player.player_id.split("_")
                assert len(parts) >= 3
                assert parts[0] == "sblive"
                assert parts[1] == "or"

    @pytest.mark.asyncio
    async def test_multi_state_location_data(self, sblive_source):
        """Test that players from different states have correct location data."""
        wa_players = await sblive_source.search_players(state="WA", limit=2)
        ca_players = await sblive_source.search_players(state="CA", limit=2)

        if wa_players:
            for player in wa_players:
                assert player.school_state == "WA"
                assert player.school_country == "USA"

        if ca_players:
            for player in ca_players:
                assert player.school_state == "CA"
                assert player.school_country == "USA"

    @pytest.mark.asyncio
    async def test_error_handling(self, sblive_source):
        """Test error handling for edge cases."""
        # Invalid player ID
        player = await sblive_source.get_player("sblive_wa_nonexistent_player")
        assert player is None or isinstance(player, Player)

        # Invalid team ID
        team = await sblive_source.get_team("sblive_wa_team_nonexistent", state="WA")
        assert team is None or isinstance(team, Team)

    @pytest.mark.asyncio
    async def test_state_url_construction(self, sblive_source):
        """Test that state URLs are correctly constructed."""
        # Test URL building
        wa_stats_url = sblive_source._get_state_url("WA", "stats")
        assert wa_stats_url == "https://www.sblive.com/wa/basketball/stats"

        ca_standings_url = sblive_source._get_state_url("CA", "standings")
        assert ca_standings_url == "https://www.sblive.com/ca/basketball/standings"

    @pytest.mark.asyncio
    async def test_state_extraction_from_player_id(self, sblive_source):
        """Test extracting state from player ID."""
        state = sblive_source._extract_state_from_player_id("sblive_wa_john_doe")
        assert state == "WA"

        state = sblive_source._extract_state_from_player_id("sblive_ca_jane_smith")
        assert state == "CA"

        # Invalid format
        state = sblive_source._extract_state_from_player_id("invalid_id")
        assert state is None
