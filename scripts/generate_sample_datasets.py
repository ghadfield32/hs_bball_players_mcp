#!/usr/bin/env python
"""
Generate Sample Datasets for HS Forecasting

Creates realistic sample data for testing the HS forecasting pipeline.
Generates mock MaxPreps, recruiting, and EYBL data with proper schemas
and realistic statistical distributions.

Usage:
    # Generate all sample data for grad year 2025
    python scripts/generate_sample_datasets.py --grad-year 2025

    # Generate with custom player counts
    python scripts/generate_sample_datasets.py --grad-year 2024 --recruiting-count 150 --maxpreps-count 600

    # Generate only specific sources
    python scripts/generate_sample_datasets.py --grad-year 2025 --only recruiting,maxpreps

Created: 2025-11-15
Phase: 14 (Data Validation & Export)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hs_forecasting.exporters import (
    create_mock_maxpreps_parquet,
    create_mock_recruiting_csv,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_all_sample_data(
    grad_year: int,
    recruiting_count: int = 100,
    maxpreps_count: int = 500,
    eybl_count: int = 50,
    output_dir: Path = None,
    only_sources: list[str] = None,
) -> dict[str, Path]:
    """
    Generate all sample datasets for testing.

    Args:
        grad_year: Graduation year for the cohort
        recruiting_count: Number of recruiting players
        maxpreps_count: Number of MaxPreps players
        eybl_count: Number of EYBL players
        output_dir: Base output directory (defaults to data/raw)
        only_sources: Optional list to generate only specific sources

    Returns:
        Dict mapping source name to output path
    """
    if output_dir is None:
        output_dir = Path("data/raw")

    logger.info(f"Generating sample datasets for grad_year={grad_year}")
    logger.info(f"Output directory: {output_dir}")

    output_paths = {}

    # Generate recruiting data
    if only_sources is None or "recruiting" in only_sources:
        logger.info(f"Generating recruiting data ({recruiting_count} players)")
        recruiting_path = output_dir / "recruiting" / "recruiting_players.csv"
        recruiting_df = create_mock_recruiting_csv(
            output_path=recruiting_path,
            grad_year=grad_year,
            num_players=recruiting_count,
        )
        output_paths["recruiting"] = recruiting_path
        logger.info(f"  ✅ Recruiting CSV: {recruiting_path} ({len(recruiting_df)} rows)")
    else:
        recruiting_df = None

    # Generate MaxPreps data (use recruiting names if available)
    if only_sources is None or "maxpreps" in only_sources:
        logger.info(f"Generating MaxPreps data ({maxpreps_count} players)")
        maxpreps_path = output_dir / "maxpreps" / "player_season_stats.parquet"
        maxpreps_df = create_mock_maxpreps_parquet(
            output_path=maxpreps_path,
            grad_year=grad_year,
            num_players=maxpreps_count,
            recruiting_df=recruiting_df,  # Use recruiting names for joinability
        )
        output_paths["maxpreps"] = maxpreps_path
        logger.info(f"  ✅ MaxPreps Parquet: {maxpreps_path} ({len(maxpreps_df)} rows)")

    # Generate EYBL data (subset of recruiting players)
    if only_sources is None or "eybl" in only_sources:
        if recruiting_df is not None and not recruiting_df.empty:
            logger.info(f"Generating EYBL data ({eybl_count} players from recruiting)")
            eybl_path = output_dir / "eybl" / "player_season_stats.parquet"

            # Select top recruits for EYBL (realistic - elite players play EYBL)
            eybl_players = recruiting_df.nsmallest(eybl_count, "national_rank")

            # Generate EYBL stats for these players
            eybl_data = []
            for _, player in eybl_players.iterrows():
                # EYBL stats tend to be slightly lower than HS (better competition)
                eybl_data.append({
                    "player_name": player["player_name"],
                    "gp": np.random.randint(12, 25),  # EYBL has fewer games
                    "pts_per_game": max(8, player.get("stars", 3) * 4 + np.random.normal(0, 3)),
                    "reb_per_game": max(2, player.get("stars", 3) * 1.5 + np.random.normal(0, 1.5)),
                    "ast_per_game": max(1, player.get("stars", 3) * 0.8 + np.random.normal(0, 1)),
                    "three_pct": max(25, min(45, 32 + np.random.normal(0, 8))),
                })

            eybl_df = pd.DataFrame(eybl_data)
            eybl_path.parent.mkdir(parents=True, exist_ok=True)
            eybl_df.to_parquet(eybl_path, index=False)
            output_paths["eybl"] = eybl_path
            logger.info(f"  ✅ EYBL Parquet: {eybl_path} ({len(eybl_df)} rows)")
        else:
            logger.warning("Skipping EYBL generation (recruiting data not available)")

    logger.info(f"\n✅ Sample data generation complete!")
    logger.info(f"Generated {len(output_paths)} datasets:")
    for source, path in output_paths.items():
        logger.info(f"  - {source}: {path}")

    return output_paths


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate sample datasets for HS forecasting testing"
    )

    parser.add_argument(
        "--grad-year",
        type=int,
        required=True,
        help="Graduation year for the cohort (e.g., 2025)",
    )

    parser.add_argument(
        "--recruiting-count",
        type=int,
        default=100,
        help="Number of recruiting players to generate (default: 100)",
    )

    parser.add_argument(
        "--maxpreps-count",
        type=int,
        default=500,
        help="Number of MaxPreps players to generate (default: 500)",
    )

    parser.add_argument(
        "--eybl-count",
        type=int,
        default=50,
        help="Number of EYBL players to generate (default: 50)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
        help="Base output directory (default: data/raw)",
    )

    parser.add_argument(
        "--only",
        type=str,
        help="Generate only specific sources (comma-separated: recruiting,maxpreps,eybl)",
    )

    args = parser.parse_args()

    # Parse only_sources
    only_sources = None
    if args.only:
        only_sources = [s.strip() for s in args.only.split(",")]
        logger.info(f"Generating only: {only_sources}")

    # Generate data
    generate_all_sample_data(
        grad_year=args.grad_year,
        recruiting_count=args.recruiting_count,
        maxpreps_count=args.maxpreps_count,
        eybl_count=args.eybl_count,
        output_dir=args.output_dir,
        only_sources=only_sources,
    )


if __name__ == "__main__":
    main()
