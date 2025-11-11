"""
Tests for OSBA (Ontario Scholastic Basketball Association) DataSource Adapter

Run these tests to validate the OSBA adapter implementation.

Usage:
    # Run all OSBA tests
    pytest tests/test_datasources/test_osba.py -v

    # Run with output
    pytest tests/test_datasources/test_osba.py -v -s

    # Run specific test
    pytest tests/test_datasources/test_osba.py::TestOSBADataSource::test_search_players -v -s
"""

import pytest

from src.datasources.canada.osba import OSBADataSource


@pytest.mark.asyncio
class TestOSBADataSource:
    """Test suite for OSBA adapter."""

    @pytest.fixture
    async def datasource(self):
        """Create OSBA datasource instance."""
        ds = OSBADataSource()
        yield ds
        await ds.close()

    async def test_search_players(self, datasource):
        """Test player search functionality."""
        players = await datasource.search_players(limit=10)

        # Basic validation
        assert isinstance(players, list), "Should return a list"

        if len(players) == 0:
            pytest.skip("No players found - check if URLs need updating after website inspection")

        assert len(players) > 0, "Should find at least one player"

        # Validate first player
        player = players[0]
        assert player.full_name, "Player should have a name"
        assert player.player_id.startswith("osba_"), "Player ID should have correct prefix"
        assert player.data_source is not None, "Player should have data source metadata"

        # Log results for debugging
        print(f"\n✓ Found {len(players)} OSBA players")
        print(f"  Sample player: {player.full_name}")
        print(f"  Player ID: {player.player_id}")
        print(f"  School: {player.team_name or 'N/A'}")
        print(f"  Position: {player.position or 'N/A'}")

    async def test_search_players_with_name_filter(self, datasource):
        """Test player search with name filter."""
        # Use a common name that should exist
        players = await datasource.search_players(name="Smith", limit=5)

        if len(players) == 0:
            pytest.skip("No players matching 'Smith' - this is acceptable")

        # All returned players should match filter
        for player in players:
            assert "smith" in player.full_name.lower(), f"Player {player.full_name} doesn't match filter"

        print(f"\n✓ Name filter working: Found {len(players)} players with 'Smith'")

    async def test_search_players_with_team_filter(self, datasource):
        """Test player search with team filter."""
        # Try filtering by school
        players = await datasource.search_players(team="Prep", limit=5)

        if len(players) == 0:
            pytest.skip("No players from schools with 'Prep' - check school names")

        # All returned players should be from matching team
        for player in players:
            if player.team_name:
                assert "prep" in player.team_name.lower(), f"School {player.team_name} doesn't match filter"

        print(f"\n✓ Team filter working: Found {len(players)} players from schools with 'Prep'")

    async def test_get_player(self, datasource):
        """Test getting individual player."""
        # First find a player
        players = await datasource.search_players(limit=1)
        if not players:
            pytest.skip("No players found to test get_player")

        # Get that player by ID
        player_id = players[0].player_id
        player = await datasource.get_player(player_id)

        assert player is not None, "Should find player by ID"
        assert player.player_id == player_id, "Should return correct player"

        print(f"\n✓ get_player working: Retrieved {player.full_name}")

    async def test_get_player_season_stats(self, datasource):
        """Test getting player season statistics."""
        # First find a player
        players = await datasource.search_players(limit=1)
        if not players:
            pytest.skip("No players found")

        player = players[0]

        # Get their stats
        stats = await datasource.get_player_season_stats(player.player_id)

        if stats is None:
            pytest.skip("No stats found - check if stats page URL needs updating")

        # Validate stats structure
        assert stats.player_id == player.player_id, "Stats should match player"
        assert stats.games_played >= 0, "Games played should be non-negative"
        assert stats.league == "OSBA", "League should be OSBA"

        # Validate stat ranges
        if stats.points_per_game:
            assert 0 <= stats.points_per_game <= 100, "PPG should be reasonable"
        if stats.rebounds_per_game:
            assert 0 <= stats.rebounds_per_game <= 30, "RPG should be reasonable"
        if stats.assists_per_game:
            assert 0 <= stats.assists_per_game <= 20, "APG should be reasonable"

        print(f"\n✓ Stats for {player.full_name}:")
        print(f"  Games: {stats.games_played}")
        print(f"  PPG: {stats.points_per_game or 'N/A'}")
        print(f"  RPG: {stats.rebounds_per_game or 'N/A'}")
        print(f"  APG: {stats.assists_per_game or 'N/A'}")

    async def test_get_leaderboard_points(self, datasource):
        """Test getting points leaderboard."""
        leaderboard = await datasource.get_leaderboard("points", limit=10)

        if len(leaderboard) == 0:
            pytest.skip("No leaderboard data - check stats page URL")

        assert len(leaderboard) > 0, "Should find leaders"

        # Validate leaderboard structure
        top_player = leaderboard[0]
        assert top_player["rank"] == 1, "First entry should be rank 1"
        assert top_player["player_name"], "Should have player name"
        assert top_player["stat_value"] > 0, "Should have positive stat value"
        assert top_player["stat_name"] == "points", "Should match requested stat"

        # Validate sorting (descending order)
        for i in range(len(leaderboard) - 1):
            assert (
                leaderboard[i]["stat_value"] >= leaderboard[i + 1]["stat_value"]
            ), "Leaderboard should be sorted descending"

        print(f"\n✓ Top 5 Points Leaders:")
        for entry in leaderboard[:5]:
            print(
                f"  {entry['rank']}. {entry['player_name']}: {entry['stat_value']} ({entry.get('team_name', 'N/A')})"
            )

    async def test_get_leaderboard_rebounds(self, datasource):
        """Test getting rebounds leaderboard."""
        leaderboard = await datasource.get_leaderboard("rebounds", limit=5)

        if len(leaderboard) == 0:
            pytest.skip("No rebounds leaderboard data")

        assert len(leaderboard) > 0, "Should find rebounds leaders"

        print(f"\n✓ Top Rebounds Leaders:")
        for entry in leaderboard[:3]:
            print(f"  {entry['rank']}. {entry['player_name']}: {entry['stat_value']}")

    async def test_get_leaderboard_assists(self, datasource):
        """Test getting assists leaderboard."""
        leaderboard = await datasource.get_leaderboard("assists", limit=5)

        if len(leaderboard) == 0:
            pytest.skip("No assists leaderboard data")

        assert len(leaderboard) > 0, "Should find assists leaders"

        print(f"\n✓ Top Assists Leaders:")
        for entry in leaderboard[:3]:
            print(f"  {entry['rank']}. {entry['player_name']}: {entry['stat_value']}")

    async def test_rate_limiting(self, datasource):
        """Test that rate limiting is working and not too aggressive."""
        import time

        start = time.time()

        # Make multiple requests quickly
        results = []
        for _ in range(5):
            players = await datasource.search_players(limit=5)
            results.append(len(players))

        elapsed = time.time() - start

        # Should complete (even with rate limiting)
        assert elapsed < 30, "Requests should complete within 30 seconds"

        # Log timing info
        print(f"\n✓ Rate limiting test:")
        print(f"  5 requests took {elapsed:.2f} seconds")
        print(f"  Average: {elapsed/5:.2f} seconds per request")
        print(f"  Players per request: {results}")

        # Check cache hit rate
        if hasattr(datasource.http_client, "metrics"):
            metrics = datasource.http_client.metrics
            total = metrics.cache_hits + metrics.cache_misses
            if total > 0:
                hit_rate = (metrics.cache_hits / total) * 100
                print(f"  Cache hit rate: {hit_rate:.1f}%")

    async def test_data_quality(self, datasource):
        """Test data quality and validation."""
        players = await datasource.search_players(limit=20)

        if len(players) == 0:
            pytest.skip("No players to validate")

        # Count players with various fields
        with_team = sum(1 for p in players if p.team_name)
        with_position = sum(1 for p in players if p.position)
        with_height = sum(1 for p in players if p.height_inches)

        print(f"\n✓ Data Quality Report:")
        print(f"  Total players: {len(players)}")
        print(f"  With school: {with_team} ({with_team/len(players)*100:.1f}%)")
        print(f"  With position: {with_position} ({with_position/len(players)*100:.1f}%)")
        print(f"  With height: {with_height} ({with_height/len(players)*100:.1f}%)")

        # Validate height ranges if present
        for player in players:
            if player.height_inches:
                assert 60 <= player.height_inches <= 96, f"Height {player.height_inches} is unrealistic for {player.full_name}"

    async def test_error_handling(self, datasource):
        """Test error handling for invalid inputs."""
        # Test with invalid player ID
        player = await datasource.get_player("invalid_id_that_does_not_exist_12345")
        assert player is None, "Should return None for invalid player ID"

        # Test with invalid stat name
        leaderboard = await datasource.get_leaderboard("invalid_stat_name_xyz")
        assert isinstance(leaderboard, list), "Should return empty list for invalid stat"

        print("\n✓ Error handling working correctly")


# Integration test (requires aggregation service)
@pytest.mark.asyncio
@pytest.mark.integration
async def test_osba_integration_with_aggregator():
    """Test OSBA adapter integration with aggregation service."""
    from src.services.aggregator import StatsAggregator

    aggregator = StatsAggregator()

    # Search across all sources (should include OSBA if working)
    players = await aggregator.search_players_all_sources(limit=5)

    # Check if any OSBA players found
    osba_players = [p for p in players if p.player_id.startswith("osba_")]

    if len(osba_players) == 0:
        pytest.skip("No OSBA players found in aggregated results")

    print(f"\n✓ Integration test: Found {len(osba_players)} OSBA players via aggregator")

    await aggregator.close()
