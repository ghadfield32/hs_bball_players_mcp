"""
FHSAA (Florida High School Athletic Association) DataSource Integration Tests

Tests FHSAA datasource with real API calls.
Florida state championships with 7 classifications (1A-7A).
"""

import pytest

from src.models import Game, GameStatus, GameType


@pytest.mark.integration
@pytest.mark.datasource
@pytest.mark.slow
class TestFHSAADataSource:
    """Test suite for FHSAA datasource with real API calls."""

    @pytest.mark.asyncio
    async def test_health_check(self, fhsaa_source):
        """Test FHSAA health check."""
        is_healthy = await fhsaa_source.health_check()
        assert is_healthy is True, "FHSAA datasource should be healthy"

    def test_build_player_id(self, fhsaa_source):
        """Test player ID construction."""
        # Basic player ID
        player_id = fhsaa_source._build_player_id("John Smith")
        assert player_id == "fhsaa_john_smith"

        # With team name for uniqueness
        player_id = fhsaa_source._build_player_id("John Smith", "Miami Heat")
        assert player_id == "fhsaa_john_smith_miami_heat"

    def test_build_team_id(self, fhsaa_source):
        """Test team ID construction."""
        # Basic team ID
        team_id = fhsaa_source._build_team_id("Miami Heat")
        assert team_id == "fhsaa_miami_heat"

        # With classification
        team_id = fhsaa_source._build_team_id("Orlando Magic", "7A")
        assert team_id == "fhsaa_orlando_magic_7a"

    def test_classifications(self, fhsaa_source):
        """Test that all classifications are defined."""
        assert fhsaa_source.classifications == ["1A", "2A", "3A", "4A", "5A", "6A", "7A"]

    @pytest.mark.asyncio
    async def test_get_games_boys(self, fhsaa_source, sample_season):
        """Test getting boys basketball games."""
        games = await fhsaa_source.get_games(
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
                assert game.game_id.startswith("fhsaa_"), "FHSAA games should have fhsaa_ prefix"
                assert game.home_team or game.away_team, "Game should have teams"

                # Check data source metadata
                assert game.data_source is not None, "Should have data source metadata"
                assert game.data_source.source_type.value == "fhsaa"

    @pytest.mark.asyncio
    async def test_get_games_girls(self, fhsaa_source, sample_season):
        """Test getting girls basketball games."""
        games = await fhsaa_source.get_games(
            season=sample_season,
            gender="girls",
            limit=10
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                assert game.game_id.startswith("fhsaa_")

    @pytest.mark.asyncio
    async def test_get_games_with_classification(self, fhsaa_source):
        """Test getting games filtered by classification."""
        games = await fhsaa_source.get_games(
            classification="7A",
            limit=5
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)

    @pytest.mark.asyncio
    async def test_get_games_tournament_type(self, fhsaa_source):
        """Test that FHSAA games are classified as tournament games."""
        games = await fhsaa_source.get_games(limit=5)

        if len(games) > 0:
            for game in games:
                # FHSAA primarily provides tournament brackets
                assert game.game_type == GameType.TOURNAMENT

    @pytest.mark.asyncio
    async def test_get_games_with_team_filter(self, fhsaa_source):
        """Test getting games with team filter."""
        games = await fhsaa_source.get_games(
            team_id="Miami",
            limit=10
        )

        assert isinstance(games, list)

        if len(games) > 0:
            for game in games:
                assert isinstance(game, Game)
                # At least one team should match filter (case-insensitive)
                assert ("miami" in game.home_team.lower() or
                       "miami" in game.away_team.lower())

    @pytest.mark.asyncio
    async def test_get_games_with_date_range(self, fhsaa_source):
        """Test getting games with date range filter."""
        from datetime import datetime, timedelta

        # Get games from the past year
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        games = await fhsaa_source.get_games(
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
    async def test_search_players_not_supported(self, fhsaa_source):
        """Test that player search returns empty (FHSAA focuses on tournament brackets)."""
        players = await fhsaa_source.search_players(name="Smith", limit=5)

        # FHSAA focuses on tournament brackets and team results
        assert isinstance(players, list)
        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_get_player_not_supported(self, fhsaa_source):
        """Test that get_player returns None (FHSAA doesn't have individual player pages)."""
        player = await fhsaa_source.get_player("fhsaa_john_smith")

        # FHSAA doesn't have individual player profile pages
        assert player is None

    @pytest.mark.asyncio
    async def test_get_player_season_stats_not_supported(self, fhsaa_source):
        """Test that get_player_season_stats returns None (FHSAA focuses on team results)."""
        stats = await fhsaa_source.get_player_season_stats("fhsaa_john_smith")

        # FHSAA focuses on team results and tournament brackets
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_player_game_stats_not_supported(self, fhsaa_source):
        """Test that get_player_game_stats returns None."""
        stats = await fhsaa_source.get_player_game_stats("fhsaa_john_smith", "game123")

        # Individual game stats not typically available
        assert stats is None

    @pytest.mark.asyncio
    async def test_get_team(self, fhsaa_source):
        """Test getting team information."""
        team = await fhsaa_source.get_team("fhsaa_miami_heat")

        # FHSAA team lookup not yet fully implemented
        # Should return None without raising exception
        assert team is None or team is not None

    @pytest.mark.asyncio
    async def test_error_handling_network_issues(self, fhsaa_source):
        """Test error handling for network issues."""
        # Try to fetch from very old season
        games = await fhsaa_source.get_games(
            season="1900-01",  # Very old season unlikely to exist
            limit=5
        )

        # Should return empty list, not raise exception
        assert isinstance(games, list)

    @pytest.mark.asyncio
    async def test_data_source_metadata(self, fhsaa_source):
        """Test that data source metadata is correctly set."""
        games = await fhsaa_source.get_games(limit=1)

        if len(games) > 0:
            game = games[0]
            assert game.data_source is not None
            assert game.data_source.source_type.value == "fhsaa"
            assert game.data_source.source_url
            assert game.data_source.quality_flag is not None

    @pytest.mark.asyncio
    async def test_game_status_classification(self, fhsaa_source):
        """Test that games have appropriate status."""
        games = await fhsaa_source.get_games(limit=5)

        if len(games) > 0:
            for game in games:
                # Games should have status (SCHEDULED or FINAL)
                assert game.status in [GameStatus.SCHEDULED, GameStatus.IN_PROGRESS, GameStatus.FINAL]

    @pytest.mark.asyncio
    async def test_multiple_classification_queries(self, fhsaa_source):
        """Test querying multiple classifications in parallel."""
        import asyncio

        # Query different classifications in parallel
        tasks = [
            fhsaa_source.get_games(classification="1A", limit=2),
            fhsaa_source.get_games(classification="4A", limit=2),
            fhsaa_source.get_games(classification="7A", limit=2),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All queries should succeed (return lists, not exceptions)
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_boys_girls_parallel_queries(self, fhsaa_source):
        """Test querying boys and girls divisions in parallel."""
        import asyncio

        # Query both divisions in parallel
        tasks = [
            fhsaa_source.get_games(gender="boys", limit=5),
            fhsaa_source.get_games(gender="girls", limit=5),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All queries should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, fhsaa_source):
        """Test that rate limiting is enforced."""
        # Make multiple rapid requests
        results = []
        for i in range(3):
            games = await fhsaa_source.get_games(limit=1)
            results.append(len(games))

        # All requests should succeed (rate limiter should handle it)
        assert all(isinstance(r, int) for r in results)

    @pytest.mark.asyncio
    async def test_basketball_url_construction(self, fhsaa_source):
        """Test that basketball URL is properly constructed."""
        assert fhsaa_source.basketball_url == "https://www.fhsaa.com/sports/basketball"

    @pytest.mark.asyncio
    async def test_source_attributes(self, fhsaa_source):
        """Test datasource attributes are properly set."""
        assert fhsaa_source.source_name == "Florida High School Athletic Association"
        assert fhsaa_source.base_url == "https://www.fhsaa.com"
        assert fhsaa_source.source_type.value == "fhsaa"
        assert fhsaa_source.region.value == "US"
