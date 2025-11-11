"""
Materialize Unified Dataset

Pulls data from all sources, builds the unified dataset, and materializes
to DuckDB and Parquet formats for analytics.

Usage:
    python scripts/materialize_unified.py [--sources eybl,fhsaa,uaa] [--season 2024]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
import pandas as pd

from src.services.aggregator import get_aggregator
from src.unified.build import build_unified_dataset
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Source metadata configuration
COUNTRY_BY_SOURCE = {
    # US sources
    "eybl": "US",
    "eybl_girls": "US",
    "three_ssb": "US",
    "three_ssb_girls": "US",
    "uaa": "US",
    "uaa_girls": "US",
    "ote": "US",
    "grind_session": "US",
    "sblive": "US",
    "bound": "US",
    "rankone": "US",
    "psal": "US",
    "mn_hub": "US",
    "wsn": "US",
    "nepsac": "US",
    "fhsaa": "US",
    "hhsaa": "US",
    "ghsa": "US",
    "nchsaa": "US",
    "vhsl": "US",
    "tssaa": "US",
    "schsl": "US",
    "ahsaa": "US",
    "lhsaa": "US",
    "mhsaa_ms": "US",
    "aaa_ar": "US",
    "khsaa": "US",
    "wvssac": "US",
    "ciac": "US",
    "diaa": "US",
    "miaa": "US",
    "mpssaa": "US",
    "mpa": "US",
    "nhiaa": "US",
    "njsiaa": "US",
    "piaa": "US",
    "riil": "US",
    "vpa": "US",
    "ihsaa": "US",
    "ohsaa": "US",
    "kshsaa": "US",
    "mhsaa_mi": "US",
    "mshsaa": "US",
    "ndhsaa": "US",
    "nsaa": "US",
    "chsaa": "US",
    "nmaa": "US",
    "ossaa": "US",
    "uhsaa": "US",
    "asaa": "US",
    "mhsa": "US",
    "whsaa": "US",
    "dciaa": "US",
    "oia": "US",
    # European sources
    "angt": "EU",
    "nbbl": "DE",
    "feb": "ES",
    "lnb_espoirs": "FR",
    "mkl": "LT",
    "fiba": "GLOBAL",
    "fiba_youth": "GLOBAL",
    "fiba_livestats": "GLOBAL",
    # Canadian sources
    "osba": "CA",
    "npa": "CA",
    # Australian sources
    "playhq": "AU",
}

STATE_BY_SOURCE = {
    "psal": "NY",
    "mn_hub": "MN",
    "wsn": "WI",
    "fhsaa": "FL",
    "hhsaa": "HI",
    "ghsa": "GA",
    "nchsaa": "NC",
    "vhsl": "VA",
    "tssaa": "TN",
    "schsl": "SC",
    "ahsaa": "AL",
    "lhsaa": "LA",
    "mhsaa_ms": "MS",
    "aaa_ar": "AR",
    "khsaa": "KY",
    "wvssac": "WV",
    "ciac": "CT",
    "diaa": "DE",
    "miaa": "MA",
    "mpssaa": "MD",
    "mpa": "ME",
    "nhiaa": "NH",
    "njsiaa": "NJ",
    "piaa": "PA",
    "riil": "RI",
    "vpa": "VT",
    "ihsaa": "IN",
    "ohsaa": "OH",
    "kshsaa": "KS",
    "mhsaa_mi": "MI",
    "mshsaa": "MO",
    "ndhsaa": "ND",
    "nsaa": "NE",
    "chsaa": "CO",
    "nmaa": "NM",
    "ossaa": "OK",
    "uhsaa": "UT",
    "asaa": "AK",
    "mhsa": "MT",
    "whsaa": "WY",
    "dciaa": "DC",
    "oia": "HI",
    "osba": "ON",
}


async def pull_source_data(
    aggregator, source_key: str, season: str | None = None
) -> dict[str, pd.DataFrame]:
    """
    Pull data from a single source.

    Returns dict with keys: teams, games, boxes, events, rosters
    """
    logger.info(f"Pulling data from {source_key}...")

    # This is a simplified example - in practice, you'd need to call
    # specific methods on each datasource to get teams, games, etc.
    # For now, return empty DataFrames as placeholders

    # TODO: Implement actual data pulling logic per source
    # Example:
    # - Call datasource.get_teams()
    # - Call datasource.get_games(season=season)
    # - Call datasource.get_leaderboard() for player stats
    # - Transform into expected DataFrame format

    return {
        "teams": pd.DataFrame(),
        "games": pd.DataFrame(),
        "boxes": pd.DataFrame(),
        "events": pd.DataFrame(),
        "rosters": pd.DataFrame(),
    }


async def main(sources: list[str] | None = None, season: str | None = None):
    """
    Main materialization workflow.

    Args:
        sources: List of source keys to pull (None = all active)
        season: Season to pull (None = current)
    """
    logger.info("Starting unified dataset materialization...")

    # Initialize aggregator
    aggregator = get_aggregator()
    available_sources = aggregator.get_available_sources()

    # Determine which sources to pull
    if sources:
        pull_sources = [s for s in sources if s in available_sources]
    else:
        pull_sources = available_sources

    if not pull_sources:
        logger.error("No valid sources to pull")
        return

    logger.info(f"Pulling from {len(pull_sources)} sources: {pull_sources}")

    # Pull data from all sources
    pulled = {}
    for source_key in pull_sources:
        try:
            data = await pull_source_data(aggregator, source_key, season)
            pulled[source_key] = data
            logger.info(f"Successfully pulled from {source_key}")
        except Exception as e:
            logger.error(f"Failed to pull from {source_key}: {e}")

    # Build unified dataset
    logger.info("Building unified dataset...")
    tables = build_unified_dataset(
        pulled,
        country_by_source=COUNTRY_BY_SOURCE,
        state_by_source=STATE_BY_SOURCE,
    )

    # Log table sizes
    for name, df in tables.items():
        logger.info(f"{name}: {len(df)} rows")

    # Materialize to DuckDB and Parquet
    output_dir = Path("data/unified")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Materializing to DuckDB and Parquet...")

    # DuckDB
    db_path = output_dir / "unified.duckdb"
    con = duckdb.connect(str(db_path))

    for name, df in tables.items():
        if not df.empty:
            # Create table in DuckDB
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM df")
            logger.info(f"Created DuckDB table: {name}")

            # Export to Parquet
            parquet_path = output_dir / f"{name}.parquet"
            df.to_parquet(parquet_path, index=False)
            logger.info(f"Exported Parquet: {name}.parquet")

    con.close()

    logger.info(f"Unified dataset materialized to {output_dir}")
    logger.info("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Materialize unified dataset")
    parser.add_argument(
        "--sources",
        type=str,
        help="Comma-separated list of sources (default: all active)",
        default=None,
    )
    parser.add_argument(
        "--season",
        type=str,
        help="Season to pull (default: current)",
        default=None,
    )

    args = parser.parse_args()

    sources_list = args.sources.split(",") if args.sources else None

    asyncio.run(main(sources=sources_list, season=args.season))
