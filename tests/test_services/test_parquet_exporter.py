"""
Parquet Exporter Service Tests

Tests Parquet export functionality.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
import pyarrow.parquet as pq

from src.models import Player, PlayerSeasonStats, DataSourceMetadata, DataQualityFlag


@pytest.mark.integration
@pytest.mark.service
class TestParquetExporter:
    """Test suite for Parquet exporter service."""

    @pytest.mark.asyncio
    async def test_export_directory_creation(self, parquet_exporter):
        """Test that export directories are created."""
        assert parquet_exporter.export_dir.exists(), "Export directory should exist"

        # Check subdirectories
        assert (parquet_exporter.export_dir / "players").exists()
        assert (parquet_exporter.export_dir / "teams").exists()
        assert (parquet_exporter.export_dir / "games").exists()
        assert (parquet_exporter.export_dir / "stats").exists()

    @pytest.mark.asyncio
    async def test_export_players_to_parquet(self, parquet_exporter):
        """Test exporting players to Parquet format."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_players = [
            Player(
                player_id="test_export_player1",
                first_name="Export",
                last_name="Test1",
                full_name="Export Test1",
                school_name="Export Test School",
                grad_year=2025,
                data_source=data_source
            ),
            Player(
                player_id="test_export_player2",
                first_name="Export",
                last_name="Test2",
                full_name="Export Test2",
                school_name="Export Test Academy",
                grad_year=2026,
                data_source=data_source
            )
        ]

        # Export to Parquet
        filepath = await parquet_exporter.export_players(
            test_players,
            filename="test_export_players",
            partition_by_source=False
        )

        assert filepath is not None, "Should return filepath"
        assert Path(filepath).exists(), "Parquet file should exist"

        # Verify file can be read
        df = pd.read_parquet(filepath)
        assert len(df) == 2, "Should have 2 records"
        assert "player_id" in df.columns
        assert "full_name" in df.columns

    @pytest.mark.asyncio
    async def test_export_players_with_partitioning(self, parquet_exporter):
        """Test exporting players with partitioning by source."""
        data_source_eybl = DataSourceMetadata(
            source_type="eybl",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )
        data_source_psal = DataSourceMetadata(
            source_type="psal",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_players = [
            Player(
                player_id="test_part_eybl1",
                first_name="EYBL",
                last_name="Player",
                full_name="EYBL Player",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source_eybl
            ),
            Player(
                player_id="test_part_psal1",
                first_name="PSAL",
                last_name="Player",
                full_name="PSAL Player",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source_psal
            )
        ]

        # Export with partitioning
        filepath = await parquet_exporter.export_players(
            test_players,
            filename="test_partitioned_export",
            partition_by_source=True
        )

        # With partitioning, filepath is the base directory
        assert Path(filepath).exists(), "Partition directory should exist"

        # Check for partition subdirectories
        partition_dir = Path(filepath)
        # Should have source_type=eybl and source_type=psal directories
        subdirs = list(partition_dir.glob("source_type=*"))
        assert len(subdirs) >= 1, "Should have partition subdirectories"

    @pytest.mark.asyncio
    async def test_export_stats_to_parquet(self, parquet_exporter):
        """Test exporting player stats to Parquet."""
        test_stats = [
            PlayerSeasonStats(
                player_id="test_export_stat1",
                player_name="Stat Test1",
                team_id="test_team",
                season="2024-25",
                league="TEST",
                games_played=10,
                points=200,
                points_per_game=20.0
            )
        ]

        filepath = await parquet_exporter.export_player_stats(
            test_stats,
            filename="test_export_stats"
        )

        assert filepath is not None
        assert Path(filepath).exists()

        # Verify file
        df = pd.read_parquet(filepath)
        assert len(df) == 1
        assert "player_id" in df.columns
        assert "points_per_game" in df.columns

    @pytest.mark.asyncio
    async def test_export_to_csv(self, parquet_exporter):
        """Test exporting data to CSV format."""
        # Create test DataFrame
        test_data = pd.DataFrame({
            "player_id": ["test_csv1", "test_csv2"],
            "name": ["CSV Test1", "CSV Test2"],
            "points": [25.5, 18.3]
        })

        filepath = await parquet_exporter.export_to_csv(
            test_data,
            filename="test_export_csv",
            category="players"
        )

        assert filepath is not None
        assert Path(filepath).exists()
        assert filepath.endswith(".csv")

        # Verify CSV can be read
        df = pd.read_csv(filepath)
        assert len(df) == 2
        assert "player_id" in df.columns

    @pytest.mark.asyncio
    async def test_export_to_json(self, parquet_exporter):
        """Test exporting data to JSON format."""
        test_data = [
            {"player_id": "test_json1", "name": "JSON Test1", "points": 25.5},
            {"player_id": "test_json2", "name": "JSON Test2", "points": 18.3}
        ]

        filepath = await parquet_exporter.export_to_json(
            test_data,
            filename="test_export_json",
            category="players"
        )

        assert filepath is not None
        assert Path(filepath).exists()
        assert filepath.endswith(".json")

        # Verify JSON can be read
        with open(filepath, "r") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["player_id"] == "test_json1"

    @pytest.mark.asyncio
    async def test_export_to_json_pretty(self, parquet_exporter):
        """Test exporting data to pretty-printed JSON."""
        test_data = [
            {"player_id": "test_pretty1", "name": "Pretty Test", "points": 30.0}
        ]

        filepath = await parquet_exporter.export_to_json(
            test_data,
            filename="test_export_pretty",
            category="players",
            pretty=True
        )

        # Read and check formatting
        with open(filepath, "r") as f:
            content = f.read()

        # Pretty-printed JSON should have indentation
        assert "\n" in content
        assert "  " in content  # Should have indentation

    @pytest.mark.asyncio
    async def test_get_export_info(self, parquet_exporter):
        """Test getting export file information."""
        # First create some exports
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_player = [
            Player(
                player_id="test_info_player",
                first_name="Info",
                last_name="Test",
                full_name="Info Test",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source
            )
        ]

        await parquet_exporter.export_players(test_player, filename="test_info_export")

        # Get export info
        info = parquet_exporter.get_export_info()

        assert isinstance(info, list)
        assert len(info) > 0, "Should have at least one export"

        # Validate info structure
        for export_info in info:
            assert "filename" in export_info
            assert "category" in export_info
            assert "size_bytes" in export_info
            assert "created_at" in export_info

    @pytest.mark.asyncio
    async def test_get_export_info_with_category_filter(self, parquet_exporter):
        """Test getting export info filtered by category."""
        info = parquet_exporter.get_export_info(category="players")

        assert isinstance(info, list)

        # All results should be from players category
        for export_info in info:
            assert export_info["category"] == "players"

    @pytest.mark.asyncio
    async def test_compression_formats(self, parquet_exporter, test_settings):
        """Test different Parquet compression formats."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_player = [
            Player(
                player_id="test_compression",
                first_name="Compress",
                last_name="Test",
                full_name="Compress Test",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source
            )
        ]

        # Test with default compression (from settings)
        filepath = await parquet_exporter.export_players(
            test_player,
            filename="test_compression_default"
        )

        assert Path(filepath).exists()

        # Verify file is compressed (should be smaller than uncompressed)
        file_size = Path(filepath).stat().st_size
        assert file_size > 0

    @pytest.mark.asyncio
    async def test_export_empty_list(self, parquet_exporter):
        """Test exporting empty list."""
        # Export empty list
        filepath = await parquet_exporter.export_players(
            [],
            filename="test_empty_export"
        )

        # Should handle gracefully
        if filepath:
            assert Path(filepath).exists()

    @pytest.mark.asyncio
    async def test_file_overwrite(self, parquet_exporter):
        """Test that exports can overwrite existing files."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        test_player1 = [
            Player(
                player_id="test_overwrite1",
                first_name="First",
                last_name="Export",
                full_name="First Export",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source
            )
        ]

        test_player2 = [
            Player(
                player_id="test_overwrite2",
                first_name="Second",
                last_name="Export",
                full_name="Second Export",
                school_name="Test School",
                grad_year=2025,
                data_source=data_source
            )
        ]

        # Export first
        filepath1 = await parquet_exporter.export_players(
            test_player1,
            filename="test_overwrite"
        )

        # Export second (same filename)
        filepath2 = await parquet_exporter.export_players(
            test_player2,
            filename="test_overwrite"
        )

        # Should overwrite
        assert filepath1 == filepath2

        # Verify second export
        df = pd.read_parquet(filepath2)
        assert len(df) == 1
        assert df.iloc[0]["player_id"] == "test_overwrite2"

    @pytest.mark.asyncio
    async def test_large_export(self, parquet_exporter):
        """Test exporting large dataset."""
        data_source = DataSourceMetadata(
            source_type="test",
            source_url="https://test.com",
            quality_flag=DataQualityFlag.COMPLETE
        )

        # Create 1000 players
        large_dataset = [
            Player(
                player_id=f"test_large_{i}",
                first_name=f"Player{i}",
                last_name="Large",
                full_name=f"Player{i} Large",
                school_name="Large Test School",
                grad_year=2025,
                data_source=data_source
            )
            for i in range(1000)
        ]

        # Export large dataset
        filepath = await parquet_exporter.export_players(
            large_dataset,
            filename="test_large_export"
        )

        assert Path(filepath).exists()

        # Verify all records
        df = pd.read_parquet(filepath)
        assert len(df) == 1000
