#!/usr/bin/env python
"""
Data Source Validation Script

Validates schema compatibility for all HS forecasting data sources
and generates detailed validation reports.

Usage:
    # Validate all sources
    python scripts/validate_data_sources.py --all

    # Validate specific source
    python scripts/validate_data_sources.py --source eybl --path data/raw/eybl/stats.parquet

    # Generate detailed report
    python scripts/validate_data_sources.py --all --output validation_report.txt

Created: 2025-11-15
Phase: 14 (Data Validation & Export)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hs_forecasting.schema_validator import (
    check_join_compatibility,
    generate_schema_report,
    validate_eybl_schema,
    validate_maxpreps_schema,
    validate_recruiting_schema,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_dataframe(path: Path, source_type: str) -> pd.DataFrame:
    """
    Load DataFrame from file (Parquet or CSV).

    Args:
        path: Path to data file
        source_type: Type of source (for logging)

    Returns:
        DataFrame or empty DataFrame if load fails
    """
    if not path.exists():
        logger.error(f"{source_type} file not found: {path}")
        return pd.DataFrame()

    try:
        if path.suffix == ".parquet":
            df = pd.read_parquet(path)
            logger.info(f"Loaded {source_type} Parquet: {len(df)} rows from {path}")
        elif path.suffix == ".csv":
            df = pd.read_csv(path)
            logger.info(f"Loaded {source_type} CSV: {len(df)} rows from {path}")
        else:
            logger.error(f"Unsupported file type: {path.suffix}")
            return pd.DataFrame()

        return df

    except Exception as e:
        logger.error(f"Failed to load {source_type} data from {path}: {e}")
        return pd.DataFrame()


def validate_single_source(
    source: str,
    path: Path,
) -> None:
    """
    Validate a single data source.

    Args:
        source: Source name (maxpreps, recruiting, eybl)
        path: Path to data file
    """
    logger.info(f"Validating {source} data source")

    # Load data
    df = load_dataframe(path, source)

    if df.empty:
        logger.error(f"Cannot validate {source}: empty or failed to load")
        return

    # Validate based on source type
    if source == "maxpreps":
        result = validate_maxpreps_schema(df)
    elif source == "recruiting":
        result = validate_recruiting_schema(df)
    elif source == "eybl":
        result = validate_eybl_schema(df)
    else:
        logger.error(f"Unknown source type: {source}")
        return

    # Print result
    print(result)

    if result.is_valid:
        logger.info(f"✅ {source} validation PASSED")
    else:
        logger.error(f"❌ {source} validation FAILED")


def validate_all_sources(
    maxpreps_path: Optional[Path] = None,
    recruiting_path: Optional[Path] = None,
    eybl_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> None:
    """
    Validate all data sources and generate comprehensive report.

    Args:
        maxpreps_path: Path to MaxPreps Parquet
        recruiting_path: Path to recruiting CSV
        eybl_path: Path to EYBL Parquet
        output_path: Optional path to save report
    """
    logger.info("Validating all data sources")

    # Load all DataFrames
    maxpreps_df = None
    recruiting_df = None
    eybl_df = None

    if maxpreps_path:
        maxpreps_df = load_dataframe(maxpreps_path, "MaxPreps")

    if recruiting_path:
        recruiting_df = load_dataframe(recruiting_path, "Recruiting")

    if eybl_path:
        eybl_df = load_dataframe(eybl_path, "EYBL")

    # Generate comprehensive report
    report = generate_schema_report(
        maxpreps_df=maxpreps_df,
        recruiting_df=recruiting_df,
        eybl_df=eybl_df,
        output_path=output_path,
    )

    print(report)

    # Check join compatibility if we have multiple sources
    if maxpreps_df is not None and recruiting_df is not None:
        logger.info("\nChecking MaxPreps <-> Recruiting join compatibility")
        join_results = check_join_compatibility(
            df1=recruiting_df,
            df2=maxpreps_df,
            join_keys=["normalized_name", "grad_year"]
            if "normalized_name" in recruiting_df.columns
            else ["player_name"],
            source1_name="Recruiting",
            source2_name="MaxPreps",
        )

        print("\n" + "=" * 70)
        print("JOIN COMPATIBILITY: Recruiting <-> MaxPreps")
        print("=" * 70)
        print(f"Can join: {'✅ YES' if join_results['can_join'] else '❌ NO'}")

        if join_results["issues"]:
            print("\nIssues:")
            for issue in join_results["issues"]:
                print(f"  - {issue}")

        if join_results["statistics"]:
            print("\nStatistics:")
            for key, stats in join_results["statistics"].items():
                print(f"  {key}:")
                for stat_name, value in stats.items():
                    print(f"    {stat_name}: {value}")

    logger.info("Validation complete!")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate HS forecasting data sources"
    )

    # Single source validation
    parser.add_argument(
        "--source",
        choices=["maxpreps", "recruiting", "eybl"],
        help="Validate single source",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Path to data file (for single source validation)",
    )

    # All sources validation
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all sources",
    )
    parser.add_argument(
        "--maxpreps",
        type=Path,
        help="Path to MaxPreps Parquet file",
    )
    parser.add_argument(
        "--recruiting",
        type=Path,
        help="Path to recruiting CSV file",
    )
    parser.add_argument(
        "--eybl",
        type=Path,
        help="Path to EYBL Parquet file",
    )

    # Output
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to save validation report",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.source and not args.path:
        parser.error("--path is required when using --source")

    if not args.source and not args.all:
        parser.error("Must specify either --source or --all")

    # Execute validation
    if args.source:
        validate_single_source(args.source, args.path)
    else:
        validate_all_sources(
            maxpreps_path=args.maxpreps,
            recruiting_path=args.recruiting,
            eybl_path=args.eybl,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
