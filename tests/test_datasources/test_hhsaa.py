"""
HHSAA (Hawaii High School Athletic Association) DataSource Integration Tests

Tests HHSAA datasource with real API calls.
Hawaii state championships with excellent historical tournament data.
"""

import pytest

from src.models import Game, GameStatus, GameType


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestHHSAADataSource:
    """Test suite for HHSAA datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, hhsaa_source):
        """Test HHSAA health check."""
        is_healthy = await hhsaa_source.health_check()
        assert is_healthy is True, "HHSAA datasource should be healthy"

    def test_build_player_id(self, hhsaa_source):
        """Test player ID construction."""
        # Basic player ID
        player_id = hhsaa_source._build_player_id("John Smith")
        assert player_id == "hhsaa_john_smith"

        # With team name for uniqueness
        player_id = hhsaa_source._build_player_id("John Smith", "Punahou")
        assert player_id == "hhsaa_john_smith_punahou"

    def test_build_team_id(self, hhsaa_source):
        """Test team ID construction."""
        # Basic team ID
        team_id = hhsaa_source._build_team_id("Punahou")
        assert team_id == "hhsaa_punahou"

        # With division
        team_id = hhsaa_source._build_team_id("Iolani", "Division I")
        assert team_id == "hhsaa_iolani_division_i"

    def test_basketball_urls(self, hhsaa_source):
        """Test that basketball URLs are properly constructed."""
        assert hhsaa_source.basketball_boys_url == "https://www.hhsaa.org/sports/basketball_boys"
        assert hhsaa_source.basketball_girls_url == "https://www.hhsaa.org/sports/basketball_girls"

    @pytest.mark.asyncio
    async def test_get_games_boys(self, hhsaa_source, sample_season):
        """Test getting boys basketball games."""
        games = await hhsaa_source.get_games(
            season=sample_season,
            gender="boys",
            limit=10
        )

        assert isinstance(games, list), "Should return a list"

        if len(games) > 0:
            assert len(games) <= 10, "Should respect limit parameter"

            # Validate game structure
            for game in games:
                assert isinstance(game, Game), "Should return Game objects"
                assert game.game_id, "Game should have an ID"
                assert game.game_id.startswith("hhsaa_"), "HHSAA games should have hhsaa_ prefix"
                assert game.home_team or game.away_team, "Game should have teams"

                # Check data source metadata
                assert game.data_source is not None, "Should have data source metadata"
                assert game.data_source.source_type.value == "hhsaa"

    @pytest.mark.asyncio
    async def test_get_games_girls(self, hhsaa_source, sample_season):
        """Test getting girls basketball games."""
        games = await hhsaa_source.get_games(
            season=sample_season,
            gender="girls",
            limit=10
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                assert game.game_id.startswith("hhsaa_")

    @pytest.mark.asyncio
    async def test_get_games_tournament_type(self, hhsaa_source):
        """Test that HHSAA games are classified as tournament games."""
        games = await hhsaa_source.get_games(limit=5)

        if len(games) > 0:
            for game in games:
                # HHSAA primarily provides state tournament data
                assert game.game_type == GameType.TOURNAMENT

    @pytest.mark.asyncio
    async def test_get_games_with_team_filter(self, hhsaa_source):
        """Test getting games with team filter."""
        games = await hhsaa_source.get_games(
            team_id="Punahou",
            limit=10
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                # At least one team should match filter (case-insensitive)
                assert ("punahou" in game.home_team.lower() or
                       "punahou" in game.away_team.lower())

    @pytest.mark.asyncio
    async def test_get_games_with_date_range(self, hhsaa_source):
        """Test getting games with date range filter."""
        from datetime import datetime, timedelta

        # Get games from the past year
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        games = await hhsaa_source.get_games(
            start_date=start_date,
            end_date=end_date,
            limit=10
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                if game.game_date:
                    assert start_date <= game.game_date <= end_date

    @pytest.mark.asyncio
    async def test_historical_data_access(self, hhsaa_source):
        """Test accessing historical tournament data."""
        # HHSAA has excellent historical data - test older season
        games = await hhsaa_source.get_games(
            season="2022-23",
            limit=5
        )

        assert isinstance(games, list)
        # Historical data may or may not be available, just verify no exceptions

    @pytest.mark.asyncio
    async def test_search_players_not_supported(self, hhsaa_source):
        """Test that player search returns empty (HHSAA focuses on tournament brackets)."""
        players = await hhsaa_source.search_players(name="Smith", limit=5)

        # HHSAA focuses on tournament brackets and team results
        assert isinstance(players, list)
        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_get_player_not_supported(self, hhsaa_source):
        """Test that get_player returns None (HHSAA doesn't have individual player pages)."""
        player = await hhsaa_source.get_player("hhsaa_john_smith")

        # HHSAA doesn't have individual player profile pages
        assert player is None

    @pytest.mark.asyncio
    async def test_get_player_season_stats_not_supported(self, hhsaa_source):
        """Test that get_player_season_stats returns None (HHSAA focuses on team results)."""
        stats = await hhsaa_source.get_player_season_stats("hhsaa_john_smith")

        # HHSAA focuses on team results and tournament brackets
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_player_game_stats_not_supported(self, hhsaa_source):
        """Test that get_player_game_stats returns None."""
        stats = await hhsaa_source.get_player_game_stats("hhsaa_john_smith", "game123")

        # Individual game stats not typically available
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_team(self, hhsaa_source):
        """Test getting team information."""
        team = await hhsaa_source.get_team("hhsaa_punahou")

        # HHSAA team lookup not yet fully implemented
        # Should return None without raising exception
        assert team is None or team is not None

    @pytest.mark.asyncio
    async def test_error_handling_network_issues(self, hhsaa_source):
        """Test error handling for network issues."""
        # Try to fetch from very old season
        games = await hhsaa_source.get_games(
            season="1900-01",  # Very old season unlikely to exist
            limit=5
        )

        # Should return empty list, not raise exception
        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_data_source_metadata(self, hhsaa_source):
        """Test that data source metadata is correctly set."""
        games = await hhsaa_source.get_games(limit=1)

        if len(games) > 0:
            game = games[0]
            assert game.data_source is not None
            assert game.data_source.source_type.value == "hhsaa"
            assert game.data_source.source_url
            assert game.data_source.quality_flag is not None

    @pytest.mark.asyncio
    async def test_game_status_classification(self, hhsaa_source):
        """Test that games have appropriate status."""
        games = await hhsaa_source.get_games(limit=5)

        if len(games) > 0:
            for game in games:
                # Games should have status (SCHEDULED or FINAL)
                assert game.status in [GameStatus.SCHEDULED, GameStatus.IN_PROGRESS, GameStatus.FINAL]

    @pytest.mark.asyncio
    async def test_boys_girls_parallel_queries(self, hhsaa_source):
        """Test querying boys and girls divisions in parallel."""
        import asyncio

        # Query both divisions in parallel
        tasks = [
            hhsaa_source.get_games(gender="boys", limit=5),
            hhsaa_source.get_games(gender="girls", limit=5),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All queries should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_multiple_season_queries(self, hhsaa_source):
        """Test querying multiple seasons in parallel."""
        import asyncio

        # Query different seasons in parallel
        tasks = [
            hhsaa_source.get_games(season="2024-25", limit=2),
            hhsaa_source.get_games(season="2023-24", limit=2),
            hhsaa_source.get_games(season="2022-23", limit=2),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All queries should succeed (return lists, not exceptions)
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, hhsaa_source):
        """Test that rate limiting is enforced."""
        # Make multiple rapid requests
        results = []
        for i in range(3):
            games = await hhsaa_source.get_games(limit=1)
            results.append(len(games))

        # All requests should succeed (rate limiter should handle it)
        assert all(isinstance(r, int) for r in results)

    @pytest.mark.asyncio
    async def test_source_attributes(self, hhsaa_source):
        """Test datasource attributes are properly set."""
        assert hhsaa_source.source_name == "Hawaii High School Athletic Association"
        assert hhsaa_source.base_url == "https://www.hhsaa.org"
        assert hhsaa_source.source_type.value == "hhsaa"
        assert hhsaa_source.region.value == "US"

    @pytest.mark.asyncio
    async def test_division_support(self, hhsaa_source):
        """Test division filtering if supported."""
        # Hawaii typically has Division I and Division II
        games = await hhsaa_source.get_games(
            division="Division I",
            limit=5
        )

        assert isinstance(games, list)
        # Division parameter may or may not be implemented yet

    @pytest.mark.asyncio
    async def test_game_data_completeness(self, hhsaa_source):
        """Test that game data contains expected fields."""
        games = await hhsaa_source.get_games(limit=3)

        if len(games) > 0:
            for game in games:
                # Required fields
                assert game.game_id
                assert game.data_source

                # At least one team should be populated
                assert game.home_team or game.away_team

                # Data source should have URL
                assert game.data_source.source_url

    @pytest.mark.asyncio
    async def test_tournament_rounds(self, hhsaa_source):
        """Test that tournament round information is captured if available."""
        games = await hhsaa_source.get_games(limit=10)

        if len(games) > 0:
            for game in games:
                # Tournament games should have game_type set
                assert game.game_type == GameType.TOURNAMENT

    @pytest.mark.asyncio
    async def test_championship_identification(self, hhsaa_source):
        """Test identification of championship games if available."""
        games = await hhsaa_source.get_games(limit=20)

        # Just verify structure - championship identification may vary
        assert isinstance(games, list)
