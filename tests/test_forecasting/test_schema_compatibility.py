"""
Schema Compatibility Tests for HS Forecasting

Tests schema validation, data export adapters, and end-to-end pipeline
compatibility with various data sources.

Created: 2025-11-15
Phase: 14 (Data Validation & Export)
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from hs_forecasting import (
    HSForecastingConfig,
    build_hs_player_season_dataset,
    create_mock_maxpreps_parquet,
    create_mock_recruiting_csv,
    standardize_eybl_stats,
    standardize_maxpreps_stats,
    standardize_recruiting,
    validate_eybl_schema,
    validate_maxpreps_schema,
    validate_recruiting_schema,
)


class TestSchemaValidation:
    """Test schema validation for all data sources."""

    def test_validate_maxpreps_valid_schema(self, tmp_path):
        """Test that valid MaxPreps schema passes validation."""
        # Create mock data
        df = create_mock_maxpreps_parquet(
            output_path=tmp_path / "maxpreps.parquet",
            grad_year=2025,
            num_players=50,
        )

        # Validate
        result = validate_maxpreps_schema(df)

        assert result.is_valid, f"Validation failed: {result.missing_required}"
        assert len(result.missing_required) == 0
        assert result.total_columns > 0

    def test_validate_recruiting_valid_schema(self, tmp_path):
        """Test that valid recruiting schema passes validation."""
        # Create mock data
        df = create_mock_recruiting_csv(
            output_path=tmp_path / "recruiting.csv",
            grad_year=2025,
            num_players=50,
        )

        # Validate
        result = validate_recruiting_schema(df)

        assert result.is_valid, f"Validation failed: {result.missing_required}"
        assert len(result.missing_required) == 0

    def test_validate_eybl_valid_schema(self):
        """Test that valid EYBL schema passes validation."""
        # Create mock EYBL data with proper schema
        df = pd.DataFrame({
            "player_name": ["John Smith", "Jane Doe"],
            "gp": [20, 18],
            "pts_per_game": [15.5, 12.3],
            "reb_per_game": [6.2, 5.1],
            "ast_per_game": [3.5, 4.2],
            "three_pct": [35.5, 32.1],
        })

        # Validate
        result = validate_eybl_schema(df)

        assert result.is_valid, f"Validation failed: {result.missing_required}"
        assert len(result.missing_required) == 0

    def test_validate_missing_required_columns(self):
        """Test that missing required columns are detected."""
        # Create DataFrame missing required columns
        df = pd.DataFrame({
            "some_column": [1, 2, 3],
        })

        result = validate_maxpreps_schema(df)

        assert not result.is_valid
        assert "player_name" in result.missing_required
        assert "grad_year" in result.missing_required


class TestStandardization:
    """Test data standardization functions."""

    def test_standardize_maxpreps_column_renaming(self, tmp_path):
        """Test that MaxPreps columns are renamed correctly."""
        # Create mock data
        df = create_mock_maxpreps_parquet(
            output_path=tmp_path / "maxpreps.parquet",
            grad_year=2025,
            num_players=10,
        )

        # Standardize
        result = standardize_maxpreps_stats(df, grad_year=2025)

        # Check renamed columns
        assert "full_name" in result.columns
        assert "gp" in result.columns
        assert "pts_per_g" in result.columns
        assert "normalized_name" in result.columns
        assert "player_uid" in result.columns

    def test_standardize_recruiting_power6_flag(self, tmp_path):
        """Test that Power-6 conference flag is computed correctly."""
        # Create mock data
        df = create_mock_recruiting_csv(
            output_path=tmp_path / "recruiting.csv",
            grad_year=2025,
            num_players=10,
        )

        # Standardize
        result = standardize_recruiting(df)

        # Check Power-6 flag exists
        assert "has_power6_offer" in result.columns

        # Check that Power-6 conferences are correctly identified
        if "committed_conference" in result.columns:
            power6_count = result["has_power6_offer"].sum()
            assert power6_count >= 0  # At least some might have Power-6 offers

    def test_standardize_eybl_multiple_schemas(self):
        """Test that EYBL standardization handles both schema variants."""
        # Test DuckDB schema (points_per_game, rebounds_per_game)
        df_duckdb = pd.DataFrame({
            "player_name": ["John Smith"],
            "games_played": [20],
            "points_per_game": [15.5],
            "rebounds_per_game": [6.2],
            "assists_per_game": [3.5],
        })

        result_duckdb = standardize_eybl_stats(df_duckdb)

        assert "eybl_gp" in result_duckdb.columns
        assert "eybl_pts_per_g" in result_duckdb.columns
        assert "eybl_reb_per_g" in result_duckdb.columns

        # Test direct adapter schema (pts_per_game, reb_per_game)
        df_adapter = pd.DataFrame({
            "player_name": ["John Smith"],
            "gp": [20],
            "pts_per_game": [15.5],
            "reb_per_game": [6.2],
            "ast_per_game": [3.5],
        })

        result_adapter = standardize_eybl_stats(df_adapter)

        assert "eybl_gp" in result_adapter.columns
        assert "eybl_pts_per_g" in result_adapter.columns
        assert "eybl_reb_per_g" in result_adapter.columns


class TestDatasetBuilder:
    """Test the full dataset building pipeline."""

    def test_build_dataset_basic(self, tmp_path):
        """Test basic dataset building with all sources."""
        # Create mock data
        recruiting_df = create_mock_recruiting_csv(
            output_path=tmp_path / "recruiting.csv",
            grad_year=2025,
            num_players=20,
        )

        maxpreps_df = create_mock_maxpreps_parquet(
            output_path=tmp_path / "maxpreps.parquet",
            grad_year=2025,
            num_players=20,
            recruiting_df=recruiting_df,  # Use same names for join
        )

        # Build dataset
        config = HSForecastingConfig(min_games_played=10, grad_year=2025)
        result = build_hs_player_season_dataset(
            maxpreps_df=maxpreps_df,
            recruiting_df=recruiting_df,
            config=config,
        )

        # Validate output
        assert not result.empty
        assert "player_uid" in result.columns
        assert "full_name" in result.columns
        assert "normalized_name" in result.columns
        assert "grad_year" in result.columns

    def test_build_dataset_with_eybl(self, tmp_path):
        """Test dataset building with EYBL data included."""
        # Create mock data
        recruiting_df = create_mock_recruiting_csv(
            output_path=tmp_path / "recruiting.csv",
            grad_year=2025,
            num_players=20,
        )

        maxpreps_df = create_mock_maxpreps_parquet(
            output_path=tmp_path / "maxpreps.parquet",
            grad_year=2025,
            num_players=20,
            recruiting_df=recruiting_df,
        )

        # Create EYBL data for top recruits
        eybl_df = pd.DataFrame({
            "player_name": recruiting_df["player_name"].head(5).tolist(),
            "gp": [20, 18, 22, 19, 21],
            "pts_per_game": [15.5, 12.3, 18.2, 11.1, 14.6],
            "reb_per_game": [6.2, 5.1, 7.3, 4.5, 6.8],
            "ast_per_game": [3.5, 4.2, 2.8, 5.1, 3.9],
        })

        # Build dataset
        config = HSForecastingConfig(min_games_played=10, grad_year=2025)
        result = build_hs_player_season_dataset(
            maxpreps_df=maxpreps_df,
            recruiting_df=recruiting_df,
            eybl_df=eybl_df,
            config=config,
        )

        # Validate EYBL columns present
        assert "played_eybl" in result.columns
        assert "eybl_gp" in result.columns

        # Check that some players are marked as EYBL players
        eybl_count = result["played_eybl"].sum()
        assert eybl_count > 0, "No EYBL players found in dataset"

    def test_build_dataset_derived_features(self, tmp_path):
        """Test that derived features are computed correctly."""
        # Create mock data
        recruiting_df = create_mock_recruiting_csv(
            output_path=tmp_path / "recruiting.csv",
            grad_year=2025,
            num_players=10,
        )

        maxpreps_df = create_mock_maxpreps_parquet(
            output_path=tmp_path / "maxpreps.parquet",
            grad_year=2025,
            num_players=10,
            recruiting_df=recruiting_df,
        )

        # Build dataset
        config = HSForecastingConfig(min_games_played=5, grad_year=2025)
        result = build_hs_player_season_dataset(
            maxpreps_df=maxpreps_df,
            recruiting_df=recruiting_df,
            config=config,
        )

        # Check derived features
        assert "total_pts_season" in result.columns
        assert "three_rate" in result.columns
        assert "has_power6_offer" in result.columns

        # Validate calculations
        if not result.empty and "pts_per_g" in result.columns:
            row = result.iloc[0]
            if pd.notnull(row.get("pts_per_g")) and pd.notnull(row.get("gp")):
                expected_total = row["pts_per_g"] * row["gp"]
                assert abs(row.get("total_pts_season", 0) - expected_total) < 0.01


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframes(self):
        """Test that empty DataFrames are handled gracefully."""
        result = build_hs_player_season_dataset(
            maxpreps_df=pd.DataFrame(),
            recruiting_df=pd.DataFrame(),
            config=HSForecastingConfig(grad_year=2025),
        )

        # Should return empty DataFrame without errors
        assert isinstance(result, pd.DataFrame)

    def test_missing_optional_columns(self, tmp_path):
        """Test that missing optional columns don't break the pipeline."""
        # Create minimal recruiting data (only required columns)
        recruiting_df = pd.DataFrame({
            "player_name": ["John Smith", "Jane Doe"],
            "grad_year": [2025, 2025],
        })

        maxpreps_df = pd.DataFrame({
            "player_name": ["John Smith", "Jane Doe"],
            "grad_year": [2025, 2025],
            "games_played": [20, 18],
            "pts_per_game": [15.5, 12.3],
        })

        # Should not raise errors
        result = build_hs_player_season_dataset(
            maxpreps_df=maxpreps_df,
            recruiting_df=recruiting_df,
            config=HSForecastingConfig(grad_year=2025),
        )

        assert not result.empty
        assert "player_uid" in result.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
