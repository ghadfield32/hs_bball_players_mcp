"""
RankOne Sport DataSource Integration Tests

Tests RankOne datasource with real API calls.
Multi-state platform: TX, KY, IN, OH, TN
"""

import pytest

from src.models import Game, GameType


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestRankOneDataSource:
    """Test suite for RankOne datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, rankone_source):
        """Test RankOne health check."""
        is_healthy = await rankone_source.health_check()
        assert is_healthy is True, "RankOne datasource should be healthy"

    @pytest.mark.asyncio
    async def test_state_validation(self, rankone_source):
        """Test state validation logic."""
        # Valid states
        assert rankone_source._validate_state("TX") is True
        assert rankone_source._validate_state("tx") is True
        assert rankone_source._validate_state("Kentucky") is True
        assert rankone_source._validate_state("OHIO") is True

        # Invalid states
        assert rankone_source._validate_state("CA") is False
        assert rankone_source._validate_state("NY") is False
        assert rankone_source._validate_state("Invalid") is False

    def test_build_player_id(self, rankone_source):
        """Test player ID construction."""
        # Basic player ID
        player_id = rankone_source._build_player_id("TX", "John Smith")
        assert player_id == "rankone_tx_john_smith"

        # With team name for uniqueness
        player_id = rankone_source._build_player_id("KY", "John Smith", "Wildcats")
        assert player_id == "rankone_ky_john_smith_wildcats"

        # Different state
        player_id = rankone_source._build_player_id("OH", "Mike Davis")
        assert player_id == "rankone_oh_mike_davis"

    def test_build_team_id(self, rankone_source):
        """Test team ID construction."""
        # Basic team ID
        team_id = rankone_source._build_team_id("TX", "Austin Lakers")
        assert team_id == "rankone_tx_austin_lakers"

        # Different state
        team_id = rankone_source._build_team_id("TN", "Memphis Tigers")
        assert team_id == "rankone_tn_memphis_tigers"

    @pytest.mark.asyncio
    async def test_get_games_texas(self, rankone_source, sample_season):
        """Test getting games from Texas."""
        games = await rankone_source.get_games(
            state="TX",
            season=sample_season,
            limit=10
        )

        assert isinstance(games, list), "Should return a list"

        if len(games) > 0:
            assert len(games) <= 10, "Should respect limit parameter"

            # Validate game structure
            for game in games:
                assert isinstance(game, Game), "Should return Game objects"
                assert game.game_id, "Game should have an ID"
                assert game.game_id.startswith("rankone_tx_"), "Texas games should have rankone_tx_ prefix"
                assert game.home_team or game.away_team, "Game should have teams"

                # Check data source metadata
                assert game.data_source is not None, "Should have data source metadata"
                assert game.data_source.source_type.value == "rankone"

    @pytest.mark.asyncio
    async def test_get_games_kentucky(self, rankone_source):
        """Test getting games from Kentucky."""
        games = await rankone_source.get_games(
            state="KY",
            limit=5
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                assert game.game_id.startswith("rankone_ky_")

    @pytest.mark.asyncio
    async def test_get_games_ohio(self, rankone_source):
        """Test getting games from Ohio."""
        games = await rankone_source.get_games(
            state="OH",
            limit=5
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                assert game.game_id.startswith("rankone_oh_")

    @pytest.mark.asyncio
    async def test_get_games_indiana(self, rankone_source):
        """Test getting games from Indiana."""
        games = await rankone_source.get_games(
            state="IN",
            limit=5
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                assert game.game_id.startswith("rankone_in_")

    @pytest.mark.asyncio
    async def test_get_games_tennessee(self, rankone_source):
        """Test getting games from Tennessee."""
        games = await rankone_source.get_games(
            state="TN",
            limit=5
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                assert game.game_id.startswith("rankone_tn_")

    @pytest.mark.asyncio
    async def test_get_games_invalid_state(self, rankone_source):
        """Test getting games with invalid state."""
        games = await rankone_source.get_games(
            state="CA",  # Not a supported state
            limit=5
        )

        # Should return empty list for unsupported states
        assert isinstance(games, list)
        assert len(games) == 0

    @pytest.mark.asyncio
    async def test_get_games_with_team_filter(self, rankone_source):
        """Test getting games with team filter."""
        games = await rankone_source.get_games(
            state="TX",
            team_id="Westlake",
            limit=10
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                # At least one team should match filter (case-insensitive)
                assert ("westlake" in game.home_team.lower() or
                       "westlake" in game.away_team.lower())

    @pytest.mark.asyncio
    async def test_search_players_not_supported(self, rankone_source):
        """Test that player search returns empty (RankOne is fixtures-only)."""
        players = await rankone_source.search_players(name="Smith", limit=5)

        # RankOne focuses on schedules/fixtures, not player stats
        assert isinstance(players, list)
        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_get_player_not_supported(self, rankone_source):
        """Test that get_player returns None (RankOne is fixtures-only)."""
        player = await rankone_source.get_player("rankone_tx_john_smith")

        # RankOne doesn't have individual player pages
        assert player is None

    @pytest.mark.asyncio
    async def test_get_player_season_stats_not_supported(self, rankone_source):
        """Test that get_player_season_stats returns None (RankOne is fixtures-only)."""
        stats = await rankone_source.get_player_season_stats("rankone_tx_john_smith")

        # RankOne doesn't provide player statistics
        assert stats is None

    @pytest.mark.asyncio
    async def test_error_handling_network_issues(self, rankone_source):
        """Test error handling for network issues."""
        # Try to fetch from invalid URL
        games = await rankone_source.get_games(
            state="TX",
            season="1900-01",  # Very old season unlikely to exist
            limit=5
        )

        # Should return empty list, not raise exception
        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_data_source_metadata(self, rankone_source):
        """Test that data source metadata is correctly set."""
        games = await rankone_source.get_games(state="TX", limit=1)

        if len(games) > 0:
            game = games[0]
            assert game.data_source is not None
            assert game.data_source.source_type.value == "rankone"
            assert game.data_source.source_url
            assert game.data_source.quality_flag is not None

    @pytest.mark.asyncio
    async def test_multi_state_parallel_queries(self, rankone_source):
        """Test querying multiple states in parallel."""
        import asyncio

        # Query all supported states in parallel
        tasks = [
            rankone_source.get_games(state="TX", limit=2),
            rankone_source.get_games(state="KY", limit=2),
            rankone_source.get_games(state="OH", limit=2),
            rankone_source.get_games(state="IN", limit=2),
            rankone_source.get_games(state="TN", limit=2),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All queries should succeed (return lists, not exceptions)
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_game_type_classification(self, rankone_source):
        """Test that games have appropriate game type."""
        games = await rankone_source.get_games(state="TX", limit=5)

        if len(games) > 0:
            for game in games:
                # RankOne provides schedules - could be regular season or tournament
                assert game.game_type in [GameType.REGULAR, GameType.TOURNAMENT, GameType.PLAYOFF]

    @pytest.mark.asyncio
    async def test_rate_limiting(self, rankone_source):
        """Test that rate limiting is enforced."""
        # Make multiple rapid requests
        results = []
        for i in range(3):
            games = await rankone_source.get_games(state="TX", limit=1)
            results.append(len(games))

        # All requests should succeed (rate limiter should handle it)
        assert all(isinstance(r, int) for r in results)
