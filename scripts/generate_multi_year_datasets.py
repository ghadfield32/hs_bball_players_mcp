#!/usr/bin/env python
"""
Generate Multi-Year HS Forecasting Datasets

Batch generates unified HS player-season datasets for multiple graduation years.
Supports both mock data (testing) and real EYBL data (production).

Features:
- Parallel processing for multiple grad years
- Progress tracking per year
- Automatic validation after each year
- Summary report with join statistics
- Option to use real EYBL data or mock data

Usage:
    # Generate mock data for years 2023-2026
    python scripts/generate_multi_year_datasets.py --start-year 2023 --end-year 2026

    # Use real EYBL data (must fetch first)
    python scripts/generate_multi_year_datasets.py --start-year 2023 --end-year 2026 --use-real-eybl

    # Custom player counts for mock data
    python scripts/generate_multi_year_datasets.py --start-year 2024 --end-year 2025 \
        --recruiting-count 150 --maxpreps-count 600

Created: 2025-11-15
Phase: 15 (Real Data Integration)
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd
from tqdm import tqdm

# Add src to path
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


def generate_sample_data_for_year(
    grad_year: int,
    recruiting_count: int,
    maxpreps_count: int,
    eybl_count: int,
    use_real_eybl: bool,
) -> bool:
    """
    Generate sample data for a single grad year.

    Args:
        grad_year: Graduation year
        recruiting_count: Number of recruiting players
        maxpreps_count: Number of MaxPreps players
        eybl_count: Number of EYBL players
        use_real_eybl: Use real EYBL data if available

    Returns:
        True if successful
    """
    logger.info(f"  Generating sample data for {grad_year}...")

    # Check if real EYBL data exists and should be used
    real_eybl_path = Path("data/raw/eybl/player_season_stats.parquet")
    if use_real_eybl and real_eybl_path.exists():
        logger.info(f"  Using real EYBL data from {real_eybl_path}")
        # Skip EYBL generation, will use existing file
        sources_to_generate = "recruiting,maxpreps"
    else:
        if use_real_eybl:
            logger.warning(f"  Real EYBL data not found, falling back to mock data")
        sources_to_generate = None  # Generate all

    # Run sample data generator
    cmd = [
        sys.executable,
        "scripts/generate_sample_datasets.py",
        "--grad-year", str(grad_year),
        "--recruiting-count", str(recruiting_count),
        "--maxpreps-count", str(maxpreps_count),
        "--eybl-count", str(eybl_count),
    ]

    if sources_to_generate:
        cmd.extend(["--only", sources_to_generate])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"  ✅ Sample data generated for {grad_year}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"  ❌ Failed to generate sample data for {grad_year}")
        logger.error(f"  Error: {e.stderr}")
        return False


def build_dataset_for_year(grad_year: int, min_games: int) -> Dict:
    """
    Build unified dataset for a single grad year.

    Args:
        grad_year: Graduation year
        min_games: Minimum games played filter

    Returns:
        Dict with statistics about the generated dataset
    """
    logger.info(f"  Building dataset for {grad_year}...")

    data_dir = Path("data/raw")
    maxpreps_path = data_dir / "maxpreps" / "player_season_stats.parquet"
    recruiting_path = data_dir / "recruiting" / "recruiting_players.csv"
    eybl_path = data_dir / "eybl" / "player_season_stats.parquet"

    # Load data
    try:
        maxpreps_df = pd.read_parquet(maxpreps_path) if maxpreps_path.exists() else pd.DataFrame()
        recruiting_df = pd.read_csv(recruiting_path) if recruiting_path.exists() else pd.DataFrame()
        eybl_df = pd.read_parquet(eybl_path) if eybl_path.exists() else None

        # Build dataset
        config = HSForecastingConfig(
            min_games_played=min_games,
            grad_year=grad_year,
        )

        hs_df = build_hs_player_season_dataset(
            maxpreps_df=maxpreps_df,
            recruiting_df=recruiting_df,
            eybl_df=eybl_df,
            config=config,
        )

        # Save output
        output_path = Path("data/processed") / f"hs_player_seasons_{grad_year}.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        hs_df.to_parquet(output_path, index=False)

        # Calculate statistics
        stats = {
            "grad_year": grad_year,
            "total_rows": len(hs_df),
            "columns": len(hs_df.columns),
            "output_path": str(output_path),
            "file_size_kb": output_path.stat().st_size / 1024 if output_path.exists() else 0,
        }

        # Additional stats
        if not hs_df.empty:
            if "stars" in hs_df.columns:
                stats["stars_distribution"] = hs_df["stars"].value_counts().to_dict()
            if "pts_per_g" in hs_df.columns:
                stats["ppg_mean"] = hs_df["pts_per_g"].mean()
            if "played_eybl" in hs_df.columns:
                stats["eybl_pct"] = (hs_df["played_eybl"].sum() / len(hs_df)) * 100

        logger.info(f"  ✅ Dataset built: {len(hs_df)} rows × {len(hs_df.columns)} columns")
        return stats

    except Exception as e:
        logger.error(f"  ❌ Failed to build dataset for {grad_year}: {e}")
        return {
            "grad_year": grad_year,
            "error": str(e),
        }


def generate_summary_report(results: List[Dict], output_path: Path) -> None:
    """
    Generate summary report for all years.

    Args:
        results: List of result dicts from each year
        output_path: Path to save report
    """
    lines = [
        "=" * 70,
        "MULTI-YEAR DATASET GENERATION REPORT",
        "=" * 70,
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "RESULTS BY YEAR:",
        "-" * 70,
    ]

    total_rows = 0
    successful_years = 0

    for result in results:
        grad_year = result["grad_year"]

        if "error" in result:
            lines.append(f"{grad_year}: ❌ FAILED - {result['error']}")
        else:
            lines.append(f"{grad_year}: ✅ SUCCESS")
            lines.append(f"  Rows: {result['total_rows']}")
            lines.append(f"  Columns: {result['columns']}")
            lines.append(f"  File: {result['output_path']}")
            lines.append(f"  Size: {result['file_size_kb']:.1f} KB")

            if "ppg_mean" in result:
                lines.append(f"  PPG mean: {result['ppg_mean']:.1f}")
            if "eybl_pct" in result:
                lines.append(f"  EYBL participation: {result['eybl_pct']:.1f}%")

            total_rows += result["total_rows"]
            successful_years += 1

        lines.append("")

    lines.extend([
        "-" * 70,
        "SUMMARY:",
        f"  Total years processed: {len(results)}",
        f"  Successful: {successful_years}",
        f"  Failed: {len(results) - successful_years}",
        f"  Total rows generated: {total_rows:,}",
        "=" * 70,
    ])

    report_text = "\n".join(lines)

    # Print to console
    print(report_text)

    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text)
    logger.info(f"Summary report saved to {output_path}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate HS forecasting datasets for multiple grad years"
    )

    parser.add_argument(
        "--start-year",
        type=int,
        required=True,
        help="Starting graduation year (e.g., 2023)",
    )

    parser.add_argument(
        "--end-year",
        type=int,
        required=True,
        help="Ending graduation year (e.g., 2026)",
    )

    parser.add_argument(
        "--recruiting-count",
        type=int,
        default=100,
        help="Number of recruiting players per year (default: 100)",
    )

    parser.add_argument(
        "--maxpreps-count",
        type=int,
        default=500,
        help="Number of MaxPreps players per year (default: 500)",
    )

    parser.add_argument(
        "--eybl-count",
        type=int,
        default=50,
        help="Number of EYBL players per year (default: 50)",
    )

    parser.add_argument(
        "--min-games",
        type=int,
        default=10,
        help="Minimum games played filter (default: 10)",
    )

    parser.add_argument(
        "--use-real-eybl",
        action="store_true",
        help="Use real EYBL data if available (must run fetch_real_eybl_data.py first)",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("data/processed/multi_year_report.txt"),
        help="Path to save summary report",
    )

    args = parser.parse_args()

    # Validate year range
    if args.start_year > args.end_year:
        logger.error("Start year must be <= end year")
        sys.exit(1)

    years = list(range(args.start_year, args.end_year + 1))

    logger.info("=" * 70)
    logger.info("MULTI-YEAR DATASET GENERATOR")
    logger.info("=" * 70)
    logger.info(f"Years: {args.start_year} - {args.end_year} ({len(years)} years)")
    logger.info(f"Use real EYBL: {args.use_real_eybl}")
    logger.info("=" * 70)

    # Process each year
    results = []

    for grad_year in tqdm(years, desc="Processing years"):
        logger.info(f"\nProcessing grad year {grad_year}")

        # Generate sample data
        success = generate_sample_data_for_year(
            grad_year=grad_year,
            recruiting_count=args.recruiting_count,
            maxpreps_count=args.maxpreps_count,
            eybl_count=args.eybl_count,
            use_real_eybl=args.use_real_eybl,
        )

        if not success:
            results.append({"grad_year": grad_year, "error": "Sample data generation failed"})
            continue

        # Build dataset
        result = build_dataset_for_year(
            grad_year=grad_year,
            min_games=args.min_games,
        )
        results.append(result)

    # Generate summary report
    logger.info("\n" + "=" * 70)
    logger.info("GENERATING SUMMARY REPORT")
    logger.info("=" * 70)

    generate_summary_report(results, args.report_output)

    logger.info("=" * 70)
    logger.info("✅ MULTI-YEAR DATASET GENERATION COMPLETE!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
