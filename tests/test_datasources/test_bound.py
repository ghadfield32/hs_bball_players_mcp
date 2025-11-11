"""
Bound (formerly Varsity Bound) DataSource Integration Tests

Tests Bound datasource covering 4 Midwest states:
IA (flagship), SD, IL, MN

High-quality stats with excellent player profile pages.
"""

import pytest

from src.models import Player, PlayerSeasonStats, Team


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestBoundDataSource:
    """Test suite for Bound datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, bound_source):
        """Test Bound health check."""
        is_healthy = await bound_source.health_check()
        assert is_healthy is True, "Bound datasource should be healthy"

    @pytest.mark.asyncio
    async def test_supported_states(self, bound_source):
        """Test that Bound supports the correct Midwest states."""
        expected_states = ["IA", "SD", "IL", "MN"]
        assert bound_source.SUPPORTED_STATES == expected_states
        assert len(bound_source.state_base_urls) == 4

    @pytest.mark.asyncio
    async def test_state_subdomain_urls(self, bound_source):
        """Test that Bound uses subdomain pattern for states."""
        # Bound uses www.{state}.bound.com pattern
        assert bound_source.state_base_urls["IA"] == "https://www.ia.bound.com"
        assert bound_source.state_base_urls["IL"] == "https://www.il.bound.com"

    @pytest.mark.asyncio
    async def test_search_players_iowa_flagship(self, bound_source):
        """Test searching players in Iowa (flagship state with best coverage)."""
        players = await bound_source.search_players(state="IA", limit=10)

        assert isinstance(players, list)

        if len(players) > 0:
            assert len(players) <= 10, "Should respect limit"

            for player in players:
                assert isinstance(player, Player)
                assert player.full_name
                assert player.player_id.startswith("bound_ia_")
                assert player.school_state == "IA"
                assert player.school_country == "USA"

                # Data source validation
                assert player.data_source is not None
                assert player.data_source.source_type.value == "bound"

    @pytest.mark.asyncio
    async def test_search_players_illinois(self, bound_source):
        """Test searching players in Illinois."""
        players = await bound_source.search_players(state="IL", limit=5)

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            assert player.player_id.startswith("bound_il_")
            assert player.school_state == "IL"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, bound_source):
        """Test searching players by name in a state."""
        players = await bound_source.search_players(
            state="IA", name="Anderson", limit=5
        )

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            assert "anderson" in player.full_name.lower()
            assert player.school_state == "IA"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, bound_source):
        """Test searching players by team/school."""
        players = await bound_source.search_players(
            state="IA", team="Roosevelt", limit=5
        )

        assert isinstance(players, list)

        for player in players:
            assert isinstance(player, Player)
            if player.school_name:
                assert "roosevelt" in player.school_name.lower()

    @pytest.mark.asyncio
    async def test_state_validation(self, bound_source):
        """Test that invalid states are rejected."""
        with pytest.raises(ValueError):
            await bound_source.search_players(state="TX", limit=5)

        with pytest.raises(ValueError):
            await bound_source.search_players(state="INVALID", limit=5)

        with pytest.raises(ValueError):
            await bound_source.search_players(state=None, limit=5)

    @pytest.mark.asyncio
    async def test_player_id_with_state_prefix(self, bound_source):
        """Test that player IDs include state prefix."""
        players = await bound_source.search_players(state="SD", limit=5)

        if len(players) > 0:
            for player in players:
                # Format: bound_{state}_{name}
                assert player.player_id.startswith("bound_sd_")
                parts = player.player_id.split("_")
                assert len(parts) >= 3
                assert parts[0] == "bound"
                assert parts[1] == "sd"

    @pytest.mark.asyncio
    async def test_get_player_season_stats(self, bound_source):
        """Test getting player season stats."""
        # First find a player
        players = await bound_source.search_players(state="IA", limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Try to get their stats
            stats = await bound_source.get_player_season_stats(player_id)

            if stats:
                assert isinstance(stats, PlayerSeasonStats)
                assert stats.player_id == player_id
                assert "Bound" in stats.league
                assert stats.season is not None

    @pytest.mark.asyncio
    async def test_get_leaderboard_by_state(self, bound_source):
        """Test getting state-specific leaderboard."""
        leaderboard = await bound_source.get_leaderboard(
            stat="points", state="IA", limit=10
        )

        assert isinstance(leaderboard, list)

        if len(leaderboard) > 0:
            for entry in leaderboard:
                assert isinstance(entry, dict)
                assert "player_name" in entry
                assert "stat_value" in entry
                assert "state" in entry
                assert entry["state"] == "IA"
                assert "Bound Iowa" in entry["league"]

    @pytest.mark.asyncio
    async def test_get_leaderboards_all_states(self, bound_source):
        """Test getting leaderboards for all Midwest states at once."""
        all_leaderboards = await bound_source.get_leaderboards_all_states(
            stat="points", limit=5
        )

        assert isinstance(all_leaderboards, dict)
        assert len(all_leaderboards) == 4  # Should have all 4 states

        for state in ["IA", "SD", "IL", "MN"]:
            assert state in all_leaderboards
            assert isinstance(all_leaderboards[state], list)

    @pytest.mark.asyncio
    async def test_get_team(self, bound_source):
        """Test getting team information."""
        # Try to get a team
        team = await bound_source.get_team("bound_ia_team_roosevelt", state="IA")

        if team:
            assert isinstance(team, Team)
            assert team.team_id.startswith("bound_ia_")
            assert "Bound Iowa" in team.league
            assert team.state == "IA"
            assert team.country == "USA"

    @pytest.mark.asyncio
    async def test_player_profile_pages(self, bound_source):
        """Test that Bound can fetch player profile pages."""
        # Bound has excellent player profile pages
        # Test the profile parsing logic
        players = await bound_source.search_players(state="IA", limit=1)

        if len(players) > 0:
            player_id = players[0].player_id

            # Try to get full player profile
            player = await bound_source.get_player(player_id)

            if player:
                assert isinstance(player, Player)
                assert player.player_id == player_id
                assert player.school_state == "IA"

    @pytest.mark.asyncio
    async def test_state_extraction_from_player_id(self, bound_source):
        """Test extracting state from player ID."""
        state = bound_source._extract_state_from_player_id("bound_ia_john_doe")
        assert state == "IA"

        state = bound_source._extract_state_from_player_id("bound_il_jane_smith")
        assert state == "IL"

        # Invalid format
        state = bound_source._extract_state_from_player_id("invalid_id")
        assert state is None

    @pytest.mark.asyncio
    async def test_multi_state_location_data(self, bound_source):
        """Test that players from different states have correct location data."""
        ia_players = await bound_source.search_players(state="IA", limit=2)
        mn_players = await bound_source.search_players(state="MN", limit=2)

        if ia_players:
            for player in ia_players:
                assert player.school_state == "IA"
                assert player.school_country == "USA"

        if mn_players:
            for player in mn_players:
                assert player.school_state == "MN"
                assert player.school_country == "USA"

    @pytest.mark.asyncio
    async def test_state_url_construction(self, bound_source):
        """Test that state URLs use subdomain pattern."""
        # Bound uses subdomain pattern: www.{state}.bound.com
        ia_stats_url = bound_source._get_state_url("IA", "stats")
        assert ia_stats_url == "https://www.ia.bound.com/basketball/stats"

        il_standings_url = bound_source._get_state_url("IL", "standings")
        assert il_standings_url == "https://www.il.bound.com/basketball/standings"

    @pytest.mark.asyncio
    async def test_error_handling(self, bound_source):
        """Test error handling for edge cases."""
        # Invalid player ID
        player = await bound_source.get_player("bound_ia_nonexistent_player")
        assert player is None or isinstance(player, Player)

        # Invalid team ID
        team = await bound_source.get_team("bound_ia_team_nonexistent", state="IA")
        assert team is None or isinstance(team, Team)

    @pytest.mark.asyncio
    async def test_state_names_mapping(self, bound_source):
        """Test that state names are correctly mapped."""
        assert bound_source.STATE_NAMES["IA"] == "Iowa"
        assert bound_source.STATE_NAMES["SD"] == "South Dakota"
        assert bound_source.STATE_NAMES["IL"] == "Illinois"
        assert bound_source.STATE_NAMES["MN"] == "Minnesota"
