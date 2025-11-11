"""
DuckDB Storage Service Tests

Tests DuckDB analytical database integration.
"""

import pytest
import pandas as pd

from src.models import Player, PlayerSeasonStats, Team, DataSourceMetadata, DataQualityFlag


@pytest.mark.integration
@pytest.mark.service
class TestDuckDBStorage:
    """Test suite for DuckDB storage service."""

    @pytest.mark.asyncio
    async def test_connection_initialization(self, duckdb_storage):
        """Test that DuckDB connection is initialized."""
        assert duckdb_storage.conn is not None, "DuckDB connection should be established"

    @pytest.mark.asyncio
    async def test_schema_initialization(self, duckdb_storage):
        """Test that database schema is properly initialized."""
        # Check that required tables exist
        tables_query = "SHOW TABLES"
        result = duckdb_storage.conn.execute(tables_query).fetchall()
        table_names = [row[0] for row in result]

        expected_tables = ["players", "teams", "player_season_stats", "games"]
        for table in expected_tables:
            assert table in table_names, f"Table {table} should exist"

    @pytest.mark.asyncio
    async def test_store_and_query_players(self, duckdb_storage):
        """Test storing and querying players."""
        # Create test players
        data_source = DataSourceMetadata(
            source_type="eybl",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_players = [
            Player(
                player_id="test_eybl_player1",
                first_name="John",
                last_name="Test",
                full_name="John Test",
                school_name="Test High School",
                school_state="CA",
                school_country="USA",
                grad_year=2025,
                data_source=data_source
            ),
            Player(
                player_id="test_eybl_player2",
                first_name="Jane",
                last_name="Test",
                full_name="Jane Test",
                school_name="Test Academy",
                school_state="NY",
                school_country="USA",
                grad_year=2026,
                data_source=data_source
            )
        ]

        # Store players
        count = await duckdb_storage.store_players(test_players)
        assert count == 2, "Should store 2 players"

        # Query all test players
        df = duckdb_storage.query_players(name="Test", limit=10)
        assert len(df) >= 2, "Should find at least 2 test players"

        # Validate data structure
        assert "player_id" in df.columns
        assert "full_name" in df.columns
        assert "school_name" in df.columns

    @pytest.mark.asyncio
    async def test_query_players_with_filters(self, duckdb_storage):
        """Test querying players with various filters."""
        # Query by name
        df = duckdb_storage.query_players(name="Test", limit=100)
        assert isinstance(df, pd.DataFrame)

        # Query by school
        df = duckdb_storage.query_players(school="Test High", limit=100)
        assert isinstance(df, pd.DataFrame)

        # Query by source
        df = duckdb_storage.query_players(source="eybl", limit=100)
        assert isinstance(df, pd.DataFrame)

        # Combined filters
        df = duckdb_storage.query_players(name="Test", school="High", limit=50)
        assert isinstance(df, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_store_and_query_player_stats(self, duckdb_storage):
        """Test storing and querying player statistics."""
        # Create test stats
        test_stats = [
            PlayerSeasonStats(
                player_id="test_eybl_player1",
                player_name="John Test",
                team_id="test_team_1",
                season="2024-25",
                league="EYBL",
                games_played=10,
                points=250,
                points_per_game=25.0,
                total_rebounds=80,
                rebounds_per_game=8.0,
                assists=50,
                assists_per_game=5.0
            ),
            PlayerSeasonStats(
                player_id="test_eybl_player2",
                player_name="Jane Test",
                team_id="test_team_2",
                season="2024-25",
                league="EYBL",
                games_played=12,
                points=288,
                points_per_game=24.0,
                total_rebounds=120,
                rebounds_per_game=10.0,
                assists=72,
                assists_per_game=6.0
            )
        ]

        # Store stats
        count = await duckdb_storage.store_player_stats(test_stats)
        assert count == 2, "Should store 2 player stat records"

        # Query stats
        df = duckdb_storage.query_stats(player_name="Test", limit=10)
        assert len(df) >= 2, "Should find at least 2 test stat records"

        # Validate data structure
        assert "player_id" in df.columns
        assert "points_per_game" in df.columns
        assert "season" in df.columns

    @pytest.mark.asyncio
    async def test_query_stats_with_filters(self, duckdb_storage):
        """Test querying stats with various filters."""
        # Query by season
        df = duckdb_storage.query_stats(season="2024-25", limit=100)
        assert isinstance(df, pd.DataFrame)

        # Query by minimum PPG
        df = duckdb_storage.query_stats(min_ppg=20.0, limit=100)
        assert isinstance(df, pd.DataFrame)

        if len(df) > 0:
            # All results should meet minimum PPG
            assert all(df["points_per_game"] >= 20.0)

        # Combined filters
        df = duckdb_storage.query_stats(
            season="2024-25",
            min_ppg=15.0,
            source="eybl",
            limit=50
        )
        assert isinstance(df, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, duckdb_storage):
        """Test getting statistical leaderboards."""
        # Get PPG leaderboard
        df = duckdb_storage.get_leaderboard(
            stat="points_per_game",
            season="2024-25",
            limit=10
        )

        assert isinstance(df, pd.DataFrame)

        if len(df) > 0:
            # Should be sorted descending
            ppg_values = df["points_per_game"].tolist()
            assert ppg_values == sorted(ppg_values, reverse=True)

            # Should have rank column
            assert "rank" in df.columns

    @pytest.mark.asyncio
    async def test_get_analytics_summary(self, duckdb_storage):
        """Test getting analytics summary."""
        summary = duckdb_storage.get_analytics_summary()

        assert isinstance(summary, dict)
        assert "total_players" in summary
        assert "total_stats" in summary
        assert "players_by_source" in summary

        # Validate structure
        assert isinstance(summary["total_players"], int)
        assert isinstance(summary["players_by_source"], dict)

    @pytest.mark.asyncio
    async def test_store_teams(self, duckdb_storage):
        """Test storing teams."""
        data_source = DataSourceMetadata(
            source_type="eybl",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_teams = [
            Team(
                team_id="test_team_1",
                team_name="Test Team 1",
                school_name="Test High School",
                city="Los Angeles",
                state="CA",
                country="USA",
                league="EYBL",
                season="2024-25",
                wins=10,
                losses=5,
                data_source=data_source
            )
        ]

        count = await duckdb_storage.store_teams(test_teams)
        assert count == 1, "Should store 1 team"

    @pytest.mark.asyncio
    async def test_upsert_behavior(self, duckdb_storage):
        """Test that duplicate entries are properly handled (upsert)."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        # Create and store a player
        player = Player(
            player_id="test_upsert_player",
            first_name="Test",
            last_name="Upsert",
            full_name="Test Upsert",
            school_name="Test School",
            grad_year=2025,
            data_source=data_source
        )

        # Store once
        count1 = await duckdb_storage.store_players([player])
        assert count1 == 1

        # Store again (should update, not duplicate)
        count2 = await duckdb_storage.store_players([player])
        assert count2 == 1

        # Verify no duplicates
        df = duckdb_storage.query_players(name="Test Upsert", limit=10)
        assert len(df) == 1, "Should have exactly 1 player, not duplicates"

    @pytest.mark.asyncio
    async def test_empty_results(self, duckdb_storage):
        """Test handling of queries with no results."""
        df = duckdb_storage.query_players(name="XyZqWvUiOpAsD", limit=10)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert df.empty

    @pytest.mark.asyncio
    async def test_limit_enforcement(self, duckdb_storage):
        """Test that query limits are enforced."""
        # Query with small limit
        df = duckdb_storage.query_players(limit=5)
        assert len(df) <= 5

        # Query with larger limit
        df = duckdb_storage.query_players(limit=100)
        assert len(df) <= 100

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, duckdb_storage):
        """Test that SQL injection is prevented."""
        # Attempt SQL injection in name parameter
        df = duckdb_storage.query_players(
            name="'; DROP TABLE players; --",
            limit=10
        )

        # Should safely handle, not execute injection
        assert isinstance(df, pd.DataFrame)

        # Verify table still exists
        tables_query = "SHOW TABLES"
        result = duckdb_storage.conn.execute(tables_query).fetchall()
        table_names = [row[0] for row in result]
        assert "players" in table_names, "Players table should still exist"

    @pytest.mark.asyncio
    async def test_large_batch_insert(self, duckdb_storage):
        """Test inserting a large batch of players."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        # Create 100 test players
        large_batch = [
            Player(
                player_id=f"test_batch_player_{i}",
                first_name=f"Player{i}",
                last_name="Batch",
                full_name=f"Player{i} Batch",
                school_name="Batch Test School",
                grad_year=2025,
                data_source=data_source
            )
            for i in range(100)
        ]

        # Store large batch
        count = await duckdb_storage.store_players(large_batch)
        assert count == 100, "Should store all 100 players"

        # Verify storage
        df = duckdb_storage.query_players(school="Batch Test School", limit=150)
        assert len(df) >= 100
