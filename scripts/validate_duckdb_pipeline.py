#!/usr/bin/env python
"""
Validate DuckDB → Dataset Builder Pipeline

Tests the integration between DuckDB storage and the HS forecasting dataset builder.
Validates that data exported from DuckDB can be properly consumed by the dataset builder.

Features:
- Export EYBL stats from DuckDB
- Validate schema compatibility
- Test join with recruiting data
- Performance benchmarks
- End-to-end validation

Usage:
    # Run full validation (requires DuckDB with data)
    python scripts/validate_duckdb_pipeline.py

    # Use mock data to populate DuckDB first
    python scripts/validate_duckdb_pipeline.py --populate-with-mock

    # Specify grad year
    python scripts/validate_duckdb_pipeline.py --grad-year 2025

Created: 2025-11-15
Phase: 15 (Real Data Integration)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hs_forecasting import (
    HSForecastingConfig,
    build_hs_player_season_dataset,
    check_join_compatibility,
    create_mock_recruiting_csv,
    export_eybl_from_duckdb,
    generate_schema_report,
)
from services.duckdb_storage import get_duckdb_storage

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def populate_duckdb_with_mock_data(grad_year: int) -> bool:
    """
    Populate DuckDB with mock EYBL data for testing.

    Args:
        grad_year: Graduation year

    Returns:
        True if successful
    """
    logger.info(f"Populating DuckDB with mock EYBL data for {grad_year}")

    try:
        # Generate mock EYBL data
        eybl_data = []
        import numpy as np

        for i in range(50):
            eybl_data.append({
                "player_name": f"Player {i}",
                "player_id": f"eybl_{i}",
                "team_id": f"team_{i % 10}",
                "season": f"{grad_year-1}-{str(grad_year)[-2:]}",
                "league": "Nike EYBL",
                "games_played": np.random.randint(15, 25),
                "points_per_game": np.random.uniform(8, 25),
                "rebounds_per_game": np.random.uniform(3, 12),
                "assists_per_game": np.random.uniform(1, 8),
                "steals_per_game": np.random.uniform(0.5, 3),
                "blocks_per_game": np.random.uniform(0.2, 2.5),
                "source_type": "eybl",
            })

        df = pd.DataFrame(eybl_data)

        # Insert into DuckDB directly using SQL
        duckdb = get_duckdb_storage()
        if not duckdb or not duckdb.conn:
            logger.error("DuckDB not available")
            return False

        # Convert DataFrame to DuckDB-compatible format
        duckdb.conn.execute("""
            CREATE TABLE IF NOT EXISTS temp_eybl_stats AS
            SELECT * FROM df
        """)

        # Insert into player_season_stats table
        duckdb.conn.execute("""
            INSERT OR REPLACE INTO player_season_stats (
                stat_id, player_id, player_name, team_id, source_type,
                season, league, games_played, points_per_game,
                rebounds_per_game, assists_per_game, steals_per_game,
                blocks_per_game, retrieved_at
            )
            SELECT
                player_id || '_' || season as stat_id,
                player_id, player_name, team_id, source_type,
                season, league, games_played, points_per_game,
                rebounds_per_game, assists_per_game, steals_per_game,
                blocks_per_game, CURRENT_TIMESTAMP as retrieved_at
            FROM temp_eybl_stats
        """)

        # Drop temp table
        duckdb.conn.execute("DROP TABLE temp_eybl_stats")

        logger.info(f"✅ Populated DuckDB with {len(df)} mock EYBL stats")
        return True

    except Exception as e:
        logger.error(f"Failed to populate DuckDB: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_duckdb_export(grad_year: int) -> pd.DataFrame:
    """
    Test exporting EYBL data from DuckDB.

    Args:
        grad_year: Graduation year

    Returns:
        DataFrame with exported data
    """
    logger.info("Testing DuckDB export...")

    duckdb = get_duckdb_storage()
    if not duckdb or not duckdb.conn:
        logger.error("DuckDB not available")
        return pd.DataFrame()

    try:
        # Export using our adapter function
        output_path = Path("data/test/eybl_from_duckdb.parquet")

        eybl_df = export_eybl_from_duckdb(
            duckdb_conn=duckdb.conn,
            output_path=output_path,
            grad_year=None,  # Get all
        )

        if eybl_df.empty:
            logger.warning("No data exported from DuckDB")
            return eybl_df

        logger.info(f"✅ Exported {len(eybl_df)} rows from DuckDB")
        logger.info(f"Columns: {list(eybl_df.columns)}")

        return eybl_df

    except Exception as e:
        logger.error(f"Failed to export from DuckDB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def test_full_pipeline(grad_year: int) -> bool:
    """
    Test the complete pipeline from DuckDB to final dataset.

    Args:
        grad_year: Graduation year

    Returns:
        True if successful
    """
    logger.info(f"\nTesting full pipeline for grad_year={grad_year}")

    # Export EYBL from DuckDB
    eybl_df = validate_duckdb_export(grad_year)

    if eybl_df.empty:
        logger.error("Cannot proceed without EYBL data")
        return False

    # Create mock recruiting data
    recruiting_path = Path("data/test/recruiting.csv")
    recruiting_df = create_mock_recruiting_csv(
        output_path=recruiting_path,
        grad_year=grad_year,
        num_players=100,
    )

    # Validate schemas
    logger.info("\nValidating schemas...")
    report = generate_schema_report(
        recruiting_df=recruiting_df,
        eybl_df=eybl_df,
    )
    print(report)

    # Check join compatibility
    logger.info("\nChecking join compatibility...")
    if "normalized_name" not in eybl_df.columns:
        from hs_forecasting import normalize_name
        eybl_df["normalized_name"] = eybl_df.get("player_name", "").map(normalize_name)

    if "normalized_name" not in recruiting_df.columns:
        from hs_forecasting import normalize_name
        recruiting_df["normalized_name"] = recruiting_df.get("player_name", "").map(normalize_name)

    join_results = check_join_compatibility(
        df1=recruiting_df,
        df2=eybl_df,
        join_keys=["normalized_name"],
        source1_name="Recruiting",
        source2_name="EYBL (from DuckDB)",
    )

    logger.info(f"Join compatibility: {join_results}")

    # Build dataset
    logger.info("\nBuilding unified dataset...")
    config = HSForecastingConfig(min_games_played=5, grad_year=grad_year)

    # Create minimal MaxPreps data (not in DuckDB yet)
    maxpreps_df = pd.DataFrame({
        "player_name": recruiting_df["player_name"].head(20).tolist(),
        "grad_year": grad_year,
        "state": "CA",
        "games_played": 20,
        "pts_per_game": 15.0,
    })

    final_df = build_hs_player_season_dataset(
        maxpreps_df=maxpreps_df,
        recruiting_df=recruiting_df,
        eybl_df=eybl_df,
        config=config,
    )

    logger.info(f"✅ Final dataset: {len(final_df)} rows × {len(final_df.columns)} columns")

    if not final_df.empty:
        logger.info("\nSample output:")
        print(final_df[['full_name', 'pts_per_g', 'eybl_pts_per_g', 'played_eybl']].head())

    return True


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Validate DuckDB → Dataset Builder pipeline"
    )

    parser.add_argument(
        "--grad-year",
        type=int,
        default=2025,
        help="Graduation year to test (default: 2025)",
    )

    parser.add_argument(
        "--populate-with-mock",
        action="store_true",
        help="Populate DuckDB with mock data before testing",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("DUCKDB → DATASET BUILDER PIPELINE VALIDATION")
    logger.info("=" * 70)

    # Populate with mock data if requested
    if args.populate_with_mock:
        success = populate_duckdb_with_mock_data(args.grad_year)
        if not success:
            logger.error("Failed to populate DuckDB with mock data")
            sys.exit(1)

    # Run validation
    start_time = time.time()

    success = test_full_pipeline(args.grad_year)

    elapsed = time.time() - start_time

    logger.info("=" * 70)
    if success:
        logger.info(f"✅ VALIDATION PASSED (elapsed: {elapsed:.1f}s)")
    else:
        logger.error(f"❌ VALIDATION FAILED (elapsed: {elapsed:.1f}s)")
    logger.info("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
