"""
Adidas 3SSB DataSource Integration Tests

Tests 3SSB datasource with real API calls.
"""

import pytest

from src.datasources.us.three_ssb import ThreeSSBDataSource
from src.models import Player, PlayerSeasonStats


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestThreeSSBDataSource:
    """Test suite for Adidas 3SSB datasource with real API calls."""

    @pytest.fixture
    async def datasource(self):
        """Create 3SSB datasource instance."""
        ds = ThreeSSBDataSource()
        yield ds
        await ds.close()

    @pytest.mark.asyncio
    async def test_health_check(self, datasource):
        """Test 3SSB health check."""
        is_healthy = await datasource.health_check()
        assert is_healthy is True, "3SSB datasource should be healthy"

    @pytest.mark.asyncio
    async def test_search_players_by_name(self, datasource):
        """Test searching players by name."""
        # Search for a common name
        players = await datasource.search_players(name="Smith", limit=5)

        assert isinstance(players, list), "Should return a list"
        # Note: Results depend on current 3SSB roster
        if len(players) > 0:
            assert len(players) <= 5, "Should respect limit parameter"

            # Validate player structure
            for player in players:
                assert isinstance(player, Player), "Should return Player objects"
                assert player.name, "Player should have a name"
                assert player.player_id, "Player should have an ID"
                assert player.player_id.startswith("3ssb_"), "3SSB players should have 3ssb_ prefix"

                # Check data source metadata
                assert player.data_source is not None, "Should have data source metadata"
                assert player.data_source.source_type.value == "three_ssb"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, datasource):
        """Test searching players by team."""
        # Search for players from a team
        players = await datasource.search_players(team="Elite", limit=10)

        # Team might not exist in current season
        for player in players:
            assert isinstance(player, Player)
            # If team filter works, team_name should contain the search term
            if player.team_name:
                assert "elite" in player.team_name.lower()

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
            assert entry["rank"] > 0

    @pytest.mark.asyncio
    async def test_get_leaderboard_rebounds(self, datasource):
        """Test getting rebounds leaderboard."""
        leaderboard = await datasource.get_leaderboard(
            stat_category="rebounds",
            limit=5
        )

        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 5

    @pytest.mark.asyncio
    async def test_get_team(self, datasource):
        """Test getting team information."""
        # First find a player to get team name
        players = await datasource.search_players(limit=1)

        if len(players) > 0 and players[0].team_name:
            team_name = players[0].team_name

            # Get team info
            team = await datasource.get_team(team_name)

            if team is not None:
                assert team.name
                assert team.team_id.startswith("3ssb_")

    @pytest.mark.asyncio
    async def test_get_games(self, datasource):
        """Test getting games/schedule."""
        games = await datasource.get_games(limit=10)

        assert isinstance(games, list)
        # Schedule might be empty depending on season timing
        for game in games:
            assert game.home_team
            assert game.away_team
            assert game.game_id.startswith("3ssb_")

    @pytest.mark.asyncio
    async def test_get_games_by_team(self, datasource):
        """Test getting games filtered by team."""
        # Get all games first
        all_games = await datasource.get_games(limit=5)

        if len(all_games) > 0:
            # Pick a team from first game
            team_name = all_games[0].home_team

            # Get games for that team
            team_games = await datasource.get_games(team_id=team_name, limit=10)

            for game in team_games:
                # Team should appear in either home or away
                assert (team_name.lower() in game.home_team.lower() or
                        team_name.lower() in game.away_team.lower())

    @pytest.mark.asyncio
    async def test_player_id_format(self, datasource):
        """Test that player IDs follow correct format."""
        players = await datasource.search_players(limit=3)

        for player in players:
            # Should be format: 3ssb_firstname_lastname or 3ssb_firstname_lastname_teamname
            assert player.player_id.startswith("3ssb_")
            parts = player.player_id.split("_")
            assert len(parts) >= 3  # At least: 3ssb, first, last

    @pytest.mark.asyncio
    async def test_rate_limiting(self, datasource):
        """Test that rate limiting is configured."""
        # Just verify that the datasource has rate limiting configured
        assert datasource.rate_limiter is not None
        assert datasource.requests_per_minute > 0

    @pytest.mark.asyncio
    async def test_source_metadata(self, datasource):
        """Test that source metadata is correctly set."""
        assert datasource.source_type.value == "three_ssb"
        assert datasource.source_name == "Adidas 3SSB"
        assert datasource.base_url == "https://adidas3ssb.com"
        assert datasource.stats_url == "https://adidas3ssb.com/stats"
        assert datasource.schedule_url == "https://adidas3ssb.com/schedule"
        assert datasource.standings_url == "https://adidas3ssb.com/standings"


@pytest.mark.unit
class TestThreeSSBPlayerIDBuilder:
    """Unit tests for 3SSB player ID generation."""

    def test_build_player_id_simple(self):
        """Test building player ID with name only."""
        ds = ThreeSSBDataSource()
        player_id = ds._build_player_id("John Doe")
        assert player_id == "3ssb_john_doe"

    def test_build_player_id_with_team(self):
        """Test building player ID with name and team."""
        ds = ThreeSSBDataSource()
        player_id = ds._build_player_id("John Doe", "Team Elite")
        assert player_id == "3ssb_john_doe_team_elite"

    def test_build_player_id_special_chars(self):
        """Test building player ID with special characters."""
        ds = ThreeSSBDataSource()
        player_id = ds._build_player_id("O'Brien Jr.", "Team #1")
        # Should normalize special characters
        assert player_id.startswith("3ssb_")
        assert " " not in player_id
