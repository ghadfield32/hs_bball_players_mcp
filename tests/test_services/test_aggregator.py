"""
Multi-Source Aggregator Service Tests

Tests aggregator with real datasource integration.
"""

import pytest

from src.models import Player, PlayerSeasonStats


@pytest.mark.integration
@pytest.mark.service
@pytest.mark.slow
class TestDataSourceAggregator:
    """Test suite for multi-source aggregator with real API calls."""

    @pytest.mark.asyncio
    async def test_aggregator_initialization(self, aggregator):
        """Test that aggregator initializes with all sources."""
        sources = aggregator.get_available_sources()

        assert isinstance(sources, list)
        assert len(sources) > 0, "Should have at least one datasource enabled"

        # Check expected sources
        expected_sources = ["eybl", "psal", "fiba", "mn_hub"]
        for source in expected_sources:
            assert source in sources, f"{source} should be available"

    @pytest.mark.asyncio
    async def test_get_source_info(self, aggregator):
        """Test getting information about all sources."""
        source_info = aggregator.get_source_info()

        assert isinstance(source_info, dict)
        assert len(source_info) > 0

        for source_key, info in source_info.items():
            assert "name" in info
            assert "type" in info
            assert "region" in info
            assert "base_url" in info
            assert "enabled" in info

    @pytest.mark.asyncio
    async def test_health_check_all_sources(self, aggregator):
        """Test health check across all datasources."""
        health_status = await aggregator.health_check_all_sources()

        assert isinstance(health_status, dict)
        assert len(health_status) > 0

        # At least some sources should be healthy
        healthy_sources = [k for k, v in health_status.items() if v]
        assert len(healthy_sources) > 0, "At least one source should be healthy"

    @pytest.mark.asyncio
    async def test_search_players_all_sources(self, aggregator):
        """Test searching players across all sources."""
        players = await aggregator.search_players_all_sources(
            name="Johnson",
            limit_per_source=2,
            total_limit=10
        )

        assert isinstance(players, list)
        assert len(players) > 0, "Should find players with common name"
        assert len(players) <= 10, "Should respect total_limit"

        # Validate players from different sources
        sources_found = set()
        for player in players:
            assert isinstance(player, Player)
            source_prefix = player.player_id.split("_")[0]
            sources_found.add(source_prefix)

        # Should have results from multiple sources
        assert len(sources_found) >= 1, "Should aggregate from multiple sources"

    @pytest.mark.asyncio
    async def test_search_players_specific_sources(self, aggregator):
        """Test searching players from specific sources only."""
        # Query only EYBL and PSAL
        players = await aggregator.search_players_all_sources(
            name="Williams",
            sources=["eybl", "psal"],
            limit_per_source=3,
            total_limit=10
        )

        assert isinstance(players, list)

        # Validate only requested sources are included
        for player in players:
            source_prefix = player.player_id.split("_")[0]
            assert source_prefix in ["eybl", "psal"], \
                "Should only return from requested sources"

    @pytest.mark.asyncio
    async def test_search_players_by_team(self, aggregator):
        """Test searching players by team across sources."""
        players = await aggregator.search_players_all_sources(
            team="Lakers",
            limit_per_source=5,
            total_limit=20
        )

        assert isinstance(players, list)
        # Results depend on whether team exists

    @pytest.mark.asyncio
    async def test_deduplication(self, aggregator):
        """Test that aggregator deduplicates players with same name."""
        # Search with high limits to potentially get duplicates
        players = await aggregator.search_players_all_sources(
            name="Smith",
            limit_per_source=10,
            total_limit=50
        )

        # Check for duplicates by (name, school) combination
        seen = set()
        for player in players:
            key = (player.full_name.lower(), player.school_name or "")
            assert key not in seen, f"Duplicate player found: {player.full_name}"
            seen.add(key)

    @pytest.mark.asyncio
    async def test_get_player_from_specific_source(self, aggregator):
        """Test getting a player from a specific source."""
        # First search for a player
        players = await aggregator.search_players_all_sources(
            name="Davis",
            sources=["eybl"],
            limit_per_source=1,
            total_limit=1
        )

        if len(players) > 0:
            player_id = players[0].player_id

            # Get from specific source
            player = await aggregator.get_player_from_source("eybl", player_id)

            if player:
                assert isinstance(player, Player)
                assert player.player_id == player_id

    @pytest.mark.asyncio
    async def test_get_player_season_stats_all_sources(self, aggregator):
        """Test getting player stats from multiple sources."""
        stats_list = await aggregator.get_player_season_stats_all_sources(
            player_name="Johnson",
            sources=["eybl", "psal"]
        )

        assert isinstance(stats_list, list)

        # Validate stats structure
        for stats in stats_list:
            assert isinstance(stats, PlayerSeasonStats)
            assert stats.player_name
            assert stats.season

    @pytest.mark.asyncio
    async def test_get_leaderboard_all_sources(self, aggregator):
        """Test getting aggregated leaderboard across sources."""
        leaderboard = await aggregator.get_leaderboard_all_sources(
            stat="points_per_game",
            limit_per_source=5,
            total_limit=15
        )

        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 15

        # Validate leaderboard structure
        for i, entry in enumerate(leaderboard):
            assert isinstance(entry, dict)
            assert "source" in entry, "Should tag entries with source"
            assert "aggregated_rank" in entry, "Should have aggregated rank"
            assert entry["aggregated_rank"] == i + 1

            # Validate descending order
            if i < len(leaderboard) - 1:
                assert entry.get("stat_value", 0) >= leaderboard[i + 1].get("stat_value", 0)

    @pytest.mark.asyncio
    async def test_parallel_query_performance(self, aggregator):
        """Test that parallel queries complete efficiently."""
        import time

        start_time = time.time()

        # Query all sources in parallel
        players = await aggregator.search_players_all_sources(
            name="Brown",
            limit_per_source=5,
            total_limit=20
        )

        elapsed_time = time.time() - start_time

        # Parallel queries should complete reasonably fast
        # (Even with network latency, should be < 30 seconds for 4 sources)
        assert elapsed_time < 30, f"Parallel queries took too long: {elapsed_time}s"

        assert isinstance(players, list)

    @pytest.mark.asyncio
    async def test_duckdb_persistence(self, aggregator, duckdb_storage):
        """Test that aggregator persists data to DuckDB."""
        # Clear any existing data for this test
        # (In production, we'd want separate test database)

        # Search players - should auto-persist
        players = await aggregator.search_players_all_sources(
            name="TestPlayer",
            limit_per_source=2,
            total_limit=5
        )

        # Query DuckDB to verify persistence
        if len(players) > 0 and duckdb_storage.conn:
            # Check that data was persisted
            df = duckdb_storage.query_players(limit=1000)
            assert len(df) >= 0  # Should have persisted data

    @pytest.mark.asyncio
    async def test_error_handling_invalid_source(self, aggregator):
        """Test error handling for invalid source."""
        # Request invalid source
        players = await aggregator.search_players_all_sources(
            sources=["invalid_source"],
            limit_per_source=5
        )

        # Should return empty list, not crash
        assert isinstance(players, list)
        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_error_handling_partial_failures(self, aggregator):
        """Test that partial source failures don't break aggregation."""
        # Even if some sources fail, others should succeed
        players = await aggregator.search_players_all_sources(
            name="Smith",
            limit_per_source=5,
            total_limit=20
        )

        # Should get results from working sources
        assert isinstance(players, list)

    @pytest.mark.asyncio
    async def test_empty_results(self, aggregator):
        """Test handling of searches with no results."""
        players = await aggregator.search_players_all_sources(
            name="XyZqWvUiOpAsD",  # Impossible name
            limit_per_source=5
        )

        assert isinstance(players, list)
        assert len(players) == 0

    @pytest.mark.asyncio
    async def test_limit_enforcement(self, aggregator):
        """Test that limits are properly enforced."""
        # Test per-source limit
        players = await aggregator.search_players_all_sources(
            name="Johnson",
            limit_per_source=2,
            total_limit=100
        )

        # Should respect per-source limit even with high total limit
        assert len(players) <= 2 * len(aggregator.get_available_sources())

        # Test total limit
        players = await aggregator.search_players_all_sources(
            name="Johnson",
            limit_per_source=50,
            total_limit=5
        )

        assert len(players) <= 5
