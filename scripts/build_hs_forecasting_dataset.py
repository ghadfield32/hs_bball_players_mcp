#!/usr/bin/env python
"""
Build a high-school player-season dataset for college-forecasting.

Usage (example):

  python scripts/build_hs_forecasting_dataset.py \
      --grad-year 2025 \
      --maxpreps data/raw/maxpreps/player_season_stats.parquet \
      --recruiting data/raw/recruiting/recruiting_players.csv \
      --eybl data/raw/eybl/player_season_stats.parquet \
      --output data/processed/hs_player_seasons_2025.parquet
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from hs_forecasting.dataset_builder import (
    HSForecastingConfig,
    build_hs_player_season_dataset,
)

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build HS player-season dataset for college forecasting."
    )
    parser.add_argument("--grad-year", type=int, required=True, help="Graduation year (e.g., 2025).")
    parser.add_argument(
        "--maxpreps",
        type=Path,
        required=True,
        help="Path to MaxPreps player-season stats (Parquet).",
    )
    parser.add_argument(
        "--recruiting",
        type=Path,
        required=True,
        help="Path to recruiting CSV file.",
    )
    parser.add_argument(
        "--eybl",
        type=Path,
        required=False,
        help="Optional path to EYBL player-season stats (Parquet).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for processed HS player-season Parquet.",
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=10,
        help="Minimum games played in HS stats to keep a player.",
    )
    return parser.parse_args()


def load_parquet(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        logger.warning("%s file not found at %s, returning empty dataframe.", label, path)
        return pd.DataFrame()
    logger.info("Loading %s from %s", label, path)
    return pd.read_parquet(path)


def load_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        logger.warning("%s file not found at %s, returning empty dataframe.", label, path)
        return pd.DataFrame()
    logger.info("Loading %s from %s", label, path)
    return pd.read_csv(path)


def main() -> None:
    _setup_logging()
    args = parse_args()

    logger.info("Starting HS forecasting dataset build for grad_year=%s", args.grad_year)

    maxpreps_df = load_parquet(args.maxpreps, "MaxPreps stats")
    recruiting_df = load_csv(args.recruiting, "Recruiting CSV")
    eybl_df: Optional[pd.DataFrame] = None

    if args.eybl is not None:
        eybl_df = load_parquet(args.eybl, "EYBL stats")

    config = HSForecastingConfig(
        min_games_played=args.min_games,
        grad_year=args.grad_year,
    )

    hs_df = build_hs_player_season_dataset(
        maxpreps_df=maxpreps_df,
        recruiting_df=recruiting_df,
        eybl_df=eybl_df,
        config=config,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Writing HS dataset to %s", args.output)
    hs_df.to_parquet(args.output, index=False)

    logger.info("Done. HS dataset shape: %s rows x %s columns", hs_df.shape[0], hs_df.shape[1])
    logger.info("Sample columns: %s", list(hs_df.columns))


if __name__ == "__main__":
    main()
