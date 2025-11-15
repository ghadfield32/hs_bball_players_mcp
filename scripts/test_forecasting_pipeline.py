#!/usr/bin/env python
"""
End-to-End Forecasting Pipeline Test

Tests the complete HS forecasting pipeline from sample data generation
through dataset building and validation.

Usage:
    # Generate sample data and test pipeline
    python scripts/test_forecasting_pipeline.py --grad-year 2025

    # Test with existing data
    python scripts/test_forecasting_pipeline.py --grad-year 2025 --skip-generation

    # Test with verbose output
    python scripts/test_forecasting_pipeline.py --grad-year 2025 --verbose

Created: 2025-11-15
Phase: 14 (Data Validation & Export)
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hs_forecasting import (
    HSForecastingConfig,
    build_hs_player_season_dataset,
    generate_schema_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_command(cmd: list[str], description: str) -> bool:
    """
    Run a shell command and log results.

    Args:
        cmd: Command and arguments as list
        description: Human-readable description

    Returns:
        True if command succeeded, False otherwise
    """
    logger.info(f"Running: {description}")
    logger.info(f"  Command: {' '.join(str(c) for c in cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout:
            logger.info(f"  Output: {result.stdout[:500]}")  # First 500 chars

        logger.info(f"  ✅ {description} succeeded")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"  ❌ {description} failed")
        logger.error(f"  Error: {e.stderr}")
        return False


def test_pipeline(
    grad_year: int,
    skip_generation: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Test the complete forecasting pipeline.

    Steps:
        1. Generate sample data (unless --skip-generation)
        2. Validate data schemas
        3. Build unified dataset
        4. Validate output
        5. Generate summary statistics

    Args:
        grad_year: Graduation year to test
        skip_generation: Skip sample data generation step
        verbose: Enable verbose logging

    Returns:
        True if all tests passed, False otherwise
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"TESTING HS FORECASTING PIPELINE - Grad Year {grad_year}")
    logger.info(f"{'='*70}\n")

    success = True

    # Step 1: Generate sample data
    if not skip_generation:
        logger.info("STEP 1: Generating sample data")
        cmd = [
            sys.executable,
            "scripts/generate_sample_datasets.py",
            "--grad-year", str(grad_year),
        ]
        if not run_command(cmd, "Sample data generation"):
            logger.error("Failed to generate sample data")
            return False
    else:
        logger.info("STEP 1: Skipped (using existing data)")

    # Step 2: Validate schemas
    logger.info("\nSTEP 2: Validating data schemas")

    data_dir = Path("data/raw")
    maxpreps_path = data_dir / "maxpreps" / "player_season_stats.parquet"
    recruiting_path = data_dir / "recruiting" / "recruiting_players.csv"
    eybl_path = data_dir / "eybl" / "player_season_stats.parquet"

    # Load data
    try:
        maxpreps_df = pd.read_parquet(maxpreps_path) if maxpreps_path.exists() else None
        recruiting_df = pd.read_csv(recruiting_path) if recruiting_path.exists() else None
        eybl_df = pd.read_parquet(eybl_path) if eybl_path.exists() else None

        logger.info(f"  Loaded MaxPreps: {len(maxpreps_df) if maxpreps_df is not None else 0} rows")
        logger.info(f"  Loaded Recruiting: {len(recruiting_df) if recruiting_df is not None else 0} rows")
        logger.info(f"  Loaded EYBL: {len(eybl_df) if eybl_df is not None else 0} rows")

        # Validate schemas
        report = generate_schema_report(
            maxpreps_df=maxpreps_df,
            recruiting_df=recruiting_df,
            eybl_df=eybl_df,
        )

        if verbose:
            print(report)

        logger.info("  ✅ Schema validation complete")

    except Exception as e:
        logger.error(f"  ❌ Schema validation failed: {e}")
        success = False

    # Step 3: Build unified dataset
    logger.info("\nSTEP 3: Building unified HS player-season dataset")

    try:
        config = HSForecastingConfig(
            min_games_played=10,
            grad_year=grad_year,
        )

        hs_df = build_hs_player_season_dataset(
            maxpreps_df=maxpreps_df if maxpreps_df is not None else pd.DataFrame(),
            recruiting_df=recruiting_df if recruiting_df is not None else pd.DataFrame(),
            eybl_df=eybl_df,
            config=config,
        )

        logger.info(f"  Dataset shape: {hs_df.shape}")
        logger.info(f"  Columns: {list(hs_df.columns)}")

        if hs_df.empty:
            logger.warning("  ⚠️  Dataset is empty (may be expected if no matching data)")
        else:
            logger.info("  ✅ Dataset built successfully")

            # Save output
            output_path = Path("data/processed") / f"hs_player_seasons_{grad_year}.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            hs_df.to_parquet(output_path, index=False)
            logger.info(f"  Saved to: {output_path}")

    except Exception as e:
        logger.error(f"  ❌ Dataset building failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        success = False
        hs_df = pd.DataFrame()

    # Step 4: Validate output
    logger.info("\nSTEP 4: Validating output dataset")

    if not hs_df.empty:
        try:
            # Check required columns
            required_cols = [
                "player_uid", "full_name", "normalized_name", "grad_year",
            ]
            missing_cols = [col for col in required_cols if col not in hs_df.columns]

            if missing_cols:
                logger.error(f"  ❌ Missing required columns: {missing_cols}")
                success = False
            else:
                logger.info("  ✅ All required columns present")

            # Check for duplicates
            dupe_count = hs_df["player_uid"].duplicated().sum()
            if dupe_count > 0:
                logger.warning(f"  ⚠️  Found {dupe_count} duplicate player UIDs")
            else:
                logger.info("  ✅ No duplicate player UIDs")

            # Summary statistics
            logger.info("\n  Summary Statistics:")
            if "stars" in hs_df.columns:
                logger.info(f"    Stars distribution: {hs_df['stars'].value_counts().to_dict()}")
            if "pts_per_g" in hs_df.columns:
                logger.info(f"    PPG mean: {hs_df['pts_per_g'].mean():.1f}")
            if "played_eybl" in hs_df.columns:
                eybl_pct = (hs_df["played_eybl"].sum() / len(hs_df)) * 100
                logger.info(f"    Played EYBL: {eybl_pct:.1f}%")

        except Exception as e:
            logger.error(f"  ❌ Output validation failed: {e}")
            success = False
    else:
        logger.warning("  ⚠️  Cannot validate empty dataset")

    # Final summary
    logger.info(f"\n{'='*70}")
    if success:
        logger.info("✅ PIPELINE TEST PASSED - All steps completed successfully")
    else:
        logger.error("❌ PIPELINE TEST FAILED - Some steps encountered errors")
    logger.info(f"{'='*70}\n")

    return success


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test the HS forecasting pipeline end-to-end"
    )

    parser.add_argument(
        "--grad-year",
        type=int,
        required=True,
        help="Graduation year to test (e.g., 2025)",
    )

    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip sample data generation (use existing data)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run test
    success = test_pipeline(
        grad_year=args.grad_year,
        skip_generation=args.skip_generation,
        verbose=args.verbose,
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
