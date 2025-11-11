"""
Historical Backfill CLI

Pulls historical data from multiple sources for specified seasons.
Supports parallel pulls with rate limiting and progress tracking.

Usage:
    python scripts/backfill_historical.py --sources eybl,uaa --seasons 2020,2021,2022
    python scripts/backfill_historical.py --sources all --start-year 2016 --end-year 2024
    python scripts/backfill_historical.py --source eybl --seasons 2020-2024
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.aggregator import get_aggregator
from src.unified.build import build_unified_dataset
from src.utils.logger import get_logger

import duckdb
import pandas as pd

logger = get_logger(__name__)


# Source metadata configuration (from materialize_unified.py)
COUNTRY_BY_SOURCE = {
    # US sources
    "eybl": "US", "eybl_girls": "US", "three_ssb": "US", "three_ssb_girls": "US",
    "uaa": "US", "uaa_girls": "US", "ote": "US", "grind_session": "US",
    "sblive": "US", "bound": "US", "rankone": "US", "psal": "US", "mn_hub": "US",
    "wsn": "US", "nepsac": "US", "fhsaa": "US", "hhsaa": "US", "cifsshome": "US",
    "uil_brackets": "US", "exposure_events": "US", "tourneymachine": "US",
    # All state associations
    "ghsa": "US", "nchsaa": "US", "vhsl": "US", "tssaa": "US", "schsl": "US",
    "ahsaa": "US", "lhsaa": "US", "mhsaa_ms": "US", "aaa_ar": "US", "khsaa": "US",
    "wvssac": "US", "ciac": "US", "diaa": "US", "miaa": "US", "mpssaa": "US",
    "mpa": "US", "nhiaa": "US", "njsiaa": "US", "piaa": "US", "riil": "US",
    "vpa": "US", "ihsaa": "US", "ohsaa": "US", "kshsaa": "US", "mhsaa_mi": "US",
    "mshsaa": "US", "ndhsaa": "US", "nsaa": "US", "chsaa": "US", "nmaa": "US",
    "ossaa": "US", "uhsaa": "US", "asaa": "US", "mhsa": "US", "whsaa": "US",
    "dciaa": "US", "oia": "US",
    # European sources
    "angt": "EU", "nbbl": "DE", "feb": "ES", "lnb_espoirs": "FR", "mkl": "LT",
    "fiba": "GLOBAL", "fiba_youth": "GLOBAL", "fiba_livestats": "GLOBAL",
    # Canadian sources
    "osba": "CA", "npa": "CA",
    # Australian sources
    "playhq": "AU",
}

STATE_BY_SOURCE = {
    "psal": "NY", "mn_hub": "MN", "wsn": "WI", "fhsaa": "FL", "hhsaa": "HI",
    "cifsshome": "CA", "uil_brackets": "TX",
    # State associations
    "ghsa": "GA", "nchsaa": "NC", "vhsl": "VA", "tssaa": "TN", "schsl": "SC",
    "ahsaa": "AL", "lhsaa": "LA", "mhsaa_ms": "MS", "aaa_ar": "AR", "khsaa": "KY",
    "wvssac": "WV", "ciac": "CT", "diaa": "DE", "miaa": "MA", "mpssaa": "MD",
    "mpa": "ME", "nhiaa": "NH", "njsiaa": "NJ", "piaa": "PA", "riil": "RI",
    "vpa": "VT", "ihsaa": "IN", "ohsaa": "OH", "kshsaa": "KS", "mhsaa_mi": "MI",
    "mshsaa": "MO", "ndhsaa": "ND", "nsaa": "NE", "chsaa": "CO", "nmaa": "NM",
    "ossaa": "OK", "uhsaa": "UT", "asaa": "AK", "mhsa": "MT", "whsaa": "WY",
    "dciaa": "DC", "oia": "HI", "osba": "ON",
}


def parse_seasons(seasons_arg: str) -> list[str]:
    """
    Parse seasons argument into list of season strings.

    Args:
        seasons_arg: Comma-separated seasons or range (e.g., "2020,2021" or "2020-2024")

    Returns:
        List of season strings

    Examples:
        >>> parse_seasons("2020,2021,2022")
        ['2020', '2021', '2022']
        >>> parse_seasons("2020-2024")
        ['2020', '2021', '2022', '2023', '2024']
    """
    seasons = []

    for part in seasons_arg.split(","):
        part = part.strip()

        # Check for range (e.g., "2020-2024")
        if "-" in part and len(part.split("-")) == 2:
            try:
                start, end = part.split("-")
                start_year = int(start)
                end_year = int(end)

                for year in range(start_year, end_year + 1):
                    seasons.append(str(year))
            except ValueError:
                logger.warning(f"Invalid season range: {part}")
        else:
            # Single season
            seasons.append(part)

    return seasons


async def backfill_source_season(
    aggregator,
    source_key: str,
    season: str,
) -> dict[str, pd.DataFrame]:
    """
    Backfill a single source for a single season.

    Returns dict with keys: teams, games, boxes, events, rosters
    """
    logger.info(f"Backfilling {source_key} for season {season}...")

    # TODO: Implement actual data pulling logic per source
    # This is a simplified placeholder - in practice, you'd need to call
    # specific methods on each datasource to get teams, games, etc.

    # For now, return empty DataFrames
    return {
        "teams": pd.DataFrame(),
        "games": pd.DataFrame(),
        "boxes": pd.DataFrame(),
        "events": pd.DataFrame(),
        "rosters": pd.DataFrame(),
    }


async def main(
    sources: list[str] | None = None,
    seasons: list[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    parallel: bool = True,
):
    """
    Main backfill workflow.

    Args:
        sources: List of source keys to backfill (None = all active)
        seasons: List of seasons to backfill
        start_year: Start year for range backfill
        end_year: End year for range backfill
        parallel: Run backfills in parallel (default: True)
    """
    logger.info("Starting historical backfill...")

    # Initialize aggregator
    aggregator = get_aggregator()
    available_sources = aggregator.get_available_sources()

    # Determine which sources to backfill
    if sources:
        backfill_sources = [s for s in sources if s in available_sources]
    else:
        backfill_sources = available_sources

    if not backfill_sources:
        logger.error("No valid sources to backfill")
        return

    # Determine which seasons to backfill
    if seasons:
        backfill_seasons = seasons
    elif start_year and end_year:
        backfill_seasons = [str(year) for year in range(start_year, end_year + 1)]
    else:
        # Default: current year only
        backfill_seasons = [str(datetime.now().year)]

    logger.info(
        f"Backfilling {len(backfill_sources)} sources for {len(backfill_seasons)} seasons",
        sources=backfill_sources,
        seasons=backfill_seasons,
    )

    # Create backfill tasks
    all_pulled = {}

    if parallel:
        # Parallel backfill
        tasks = []
        for source_key in backfill_sources:
            for season in backfill_seasons:
                task = backfill_source_season(aggregator, source_key, season)
                tasks.append((source_key, season, task))

        # Gather results
        for source_key, season, task in tasks:
            try:
                data = await task
                key = f"{source_key}_{season}"
                all_pulled[key] = data
                logger.info(f"Completed backfill: {source_key} {season}")
            except Exception as e:
                logger.error(f"Failed to backfill {source_key} {season}", error=str(e))
    else:
        # Sequential backfill
        for source_key in backfill_sources:
            for season in backfill_seasons:
                try:
                    data = await backfill_source_season(aggregator, source_key, season)
                    key = f"{source_key}_{season}"
                    all_pulled[key] = data
                    logger.info(f"Completed backfill: {source_key} {season}")
                except Exception as e:
                    logger.error(f"Failed to backfill {source_key} {season}", error=str(e))

    # Build unified dataset
    logger.info("Building unified dataset from backfilled data...")

    # Group by source (collapse seasons)
    pulled_by_source = {}
    for key, data in all_pulled.items():
        source_key = "_".join(key.split("_")[:-1])
        if source_key not in pulled_by_source:
            pulled_by_source[source_key] = {
                "teams": [],
                "games": [],
                "boxes": [],
                "events": [],
                "rosters": [],
            }

        for table_name, df in data.items():
            if not df.empty:
                pulled_by_source[source_key][table_name].append(df)

    # Concatenate DataFrames per source
    for source_key, tables_dict in pulled_by_source.items():
        for table_name, dfs in tables_dict.items():
            if dfs:
                pulled_by_source[source_key][table_name] = pd.concat(dfs, ignore_index=True)
            else:
                pulled_by_source[source_key][table_name] = pd.DataFrame()

    # Build unified dataset
    tables = build_unified_dataset(
        pulled_by_source,
        country_by_source=COUNTRY_BY_SOURCE,
        state_by_source=STATE_BY_SOURCE,
    )

    # Log table sizes
    for name, df in tables.items():
        logger.info(f"{name}: {len(df)} rows")

    # Materialize to DuckDB and Parquet
    output_dir = Path("data/unified")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Materializing backfilled data to DuckDB and Parquet...")

    # DuckDB
    db_path = output_dir / "unified.duckdb"
    con = duckdb.connect(str(db_path))

    for name, df in tables.items():
        if not df.empty:
            # Append to existing table (or create if doesn't exist)
            try:
                # Try to append
                con.execute(f"INSERT INTO {name} SELECT * FROM df")
                logger.info(f"Appended to DuckDB table: {name}")
            except:
                # Create table if doesn't exist
                con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
                logger.info(f"Created DuckDB table: {name}")

            # Export to Parquet (append mode)
            parquet_path = output_dir / f"{name}.parquet"
            df.to_parquet(parquet_path, index=False, mode="append")
            logger.info(f"Appended Parquet: {name}.parquet")

    con.close()

    logger.info(f"Historical backfill complete! Data saved to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Historical data backfill")
    parser.add_argument(
        "--sources",
        type=str,
        help="Comma-separated list of sources (default: all active)",
        default=None,
    )
    parser.add_argument(
        "--seasons",
        type=str,
        help="Comma-separated seasons or range (e.g., '2020,2021' or '2020-2024')",
        default=None,
    )
    parser.add_argument(
        "--start-year",
        type=int,
        help="Start year for range backfill",
        default=None,
    )
    parser.add_argument(
        "--end-year",
        type=int,
        help="End year for range backfill",
        default=None,
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run backfills sequentially (default: parallel)",
    )

    args = parser.parse_args()

    # Parse arguments
    sources_list = args.sources.split(",") if args.sources else None
    seasons_list = parse_seasons(args.seasons) if args.seasons else None

    asyncio.run(
        main(
            sources=sources_list,
            seasons=seasons_list,
            start_year=args.start_year,
            end_year=args.end_year,
            parallel=not args.sequential,
        )
    )
