#!/usr/bin/env python3
"""
DuckDB Loader for HS Player-Season Data

Loads canonical HS_PLAYER_SEASON parquet files into DuckDB for unified querying.
Creates a single hs_player_seasons table combining all datasources.

Usage:
    python scripts/load_to_duckdb.py --data-dir data/ --db-path data/hs_player_seasons.db
    python scripts/load_to_duckdb.py --rebuild  # Drop and recreate table
    python scripts/load_to_duckdb.py --sources eybl sblive  # Load specific sources only

Author: Phase 16 - First HS Player-Season Exports
Date: 2025-11-16
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import duckdb

# ==============================================================================
# DUCKDB SCHEMA - Matches canonical HS_PLAYER_SEASON schema
# ==============================================================================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hs_player_seasons (
    -- Identifiers
    global_player_id VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    source_player_id VARCHAR NOT NULL,
    season VARCHAR NOT NULL,

    -- Player metadata
    first_name VARCHAR,
    last_name VARCHAR,
    full_name VARCHAR NOT NULL,

    -- Context
    league VARCHAR NOT NULL,
    team_id VARCHAR,
    team_name VARCHAR,
    state_code VARCHAR,
    country_code VARCHAR,

    -- Core stats
    games_played INTEGER NOT NULL,
    games_started INTEGER,
    minutes DOUBLE,

    -- Shooting
    field_goals_made INTEGER,
    field_goals_attempted INTEGER,
    three_pointers_made INTEGER,
    three_pointers_attempted INTEGER,
    free_throws_made INTEGER,
    free_throws_attempted INTEGER,

    -- Rebounding
    offensive_rebounds INTEGER,
    defensive_rebounds INTEGER,
    total_rebounds INTEGER,

    -- Other stats
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    points INTEGER,

    -- Player attributes
    position VARCHAR,
    jersey_number INTEGER,
    height_inches INTEGER,
    weight_lbs INTEGER,
    graduation_year INTEGER,
    grade INTEGER,
    age INTEGER,

    -- Percentages
    field_goal_percentage DOUBLE,
    three_point_percentage DOUBLE,
    free_throw_percentage DOUBLE,

    -- Per-game averages
    points_per_game DOUBLE,
    rebounds_per_game DOUBLE,
    assists_per_game DOUBLE,
    steals_per_game DOUBLE,
    blocks_per_game DOUBLE,
    minutes_per_game DOUBLE,

    -- Advanced stats
    true_shooting_percentage DOUBLE,
    effective_field_goal_percentage DOUBLE,
    assist_to_turnover_ratio DOUBLE,

    -- Metadata
    per_game_stats BOOLEAN,
    data_quality_flag VARCHAR,
    source_url VARCHAR,
    scraped_at VARCHAR,
    notes VARCHAR,

    -- Constraints
    PRIMARY KEY (source, source_player_id, season)
);
"""

# Indexes for common queries
CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_source ON hs_player_seasons(source);",
    "CREATE INDEX IF NOT EXISTS idx_season ON hs_player_seasons(season);",
    "CREATE INDEX IF NOT EXISTS idx_state_season ON hs_player_seasons(state_code, season);",
    "CREATE INDEX IF NOT EXISTS idx_league ON hs_player_seasons(league);",
    "CREATE INDEX IF NOT EXISTS idx_grad_year ON hs_player_seasons(graduation_year);",
    "CREATE INDEX IF NOT EXISTS idx_global_player ON hs_player_seasons(global_player_id);",
]


# ==============================================================================
# LOADER FUNCTIONS
# ==============================================================================

def find_parquet_files(data_dir: Path, sources: Optional[List[str]] = None) -> List[Path]:
    """
    Find all player-season parquet files in data directory.

    Args:
        data_dir: Root data directory
        sources: Optional list of sources to filter (e.g., ["eybl", "sblive"])

    Returns:
        List of parquet file paths
    """
    parquet_files = []

    # If sources specified, only search those subdirectories
    if sources:
        for source in sources:
            source_dir = data_dir / source
            if source_dir.exists():
                parquet_files.extend(source_dir.glob("*.parquet"))
    else:
        # Search all subdirectories
        parquet_files = list(data_dir.rglob("*.parquet"))

    return sorted(parquet_files)


def load_parquet_to_duckdb(
    db_path: Path,
    parquet_files: List[Path],
    rebuild: bool = False
) -> None:
    """
    Load parquet files into DuckDB.

    Args:
        db_path: Path to DuckDB database file
        parquet_files: List of parquet files to load
        rebuild: If True, drop and recreate table first
    """
    print(f"\n{'='*80}")
    print(f"Loading HS Player-Season Data to DuckDB")
    print(f"{'='*80}")
    print(f"Database: {db_path}")
    print(f"Parquet files: {len(parquet_files)}")
    print(f"Rebuild: {rebuild}")
    print(f"{'='*80}\n")

    # Create DB directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect to DuckDB
    print("🔧 Connecting to DuckDB...")
    con = duckdb.connect(str(db_path))

    try:
        # Drop table if rebuilding
        if rebuild:
            print("⚠️  Rebuilding - dropping existing table...")
            con.execute("DROP TABLE IF EXISTS hs_player_seasons;")

        # Create table
        print("📊 Creating hs_player_seasons table...")
        con.execute(CREATE_TABLE_SQL)

        # Create indexes
        print("🔍 Creating indexes...")
        for index_sql in CREATE_INDEXES_SQL:
            con.execute(index_sql)

        # Load each parquet file
        print(f"\n📥 Loading {len(parquet_files)} parquet files...")

        for i, parquet_file in enumerate(parquet_files, 1):
            try:
                # Get record count before
                before_count = con.execute("SELECT COUNT(*) FROM hs_player_seasons").fetchone()[0]

                # Load parquet
                print(f"  [{i}/{len(parquet_files)}] Loading {parquet_file.name}...")

                # Insert from parquet (DuckDB can read parquet directly)
                con.execute(f"""
                    INSERT OR REPLACE INTO hs_player_seasons
                    SELECT * FROM read_parquet('{parquet_file}')
                """)

                # Get record count after
                after_count = con.execute("SELECT COUNT(*) FROM hs_player_seasons").fetchone()[0]
                added = after_count - before_count

                print(f"      ✅ Added {added:,} records (total: {after_count:,})")

            except Exception as e:
                print(f"      ❌ Error loading {parquet_file.name}: {e}")

        # Final summary
        print(f"\n{'='*80}")
        print(f"Load Summary")
        print(f"{'='*80}")

        # Total records
        total_records = con.execute("SELECT COUNT(*) FROM hs_player_seasons").fetchone()[0]
        print(f"Total records: {total_records:,}")

        # By source
        print(f"\nRecords by source:")
        by_source = con.execute("""
            SELECT source, COUNT(*) as count
            FROM hs_player_seasons
            GROUP BY source
            ORDER BY count DESC
        """).fetchall()
        for source, count in by_source:
            print(f"  - {source}: {count:,}")

        # By season
        print(f"\nRecords by season:")
        by_season = con.execute("""
            SELECT season, COUNT(*) as count
            FROM hs_player_seasons
            GROUP BY season
            ORDER BY season DESC
        """).fetchall()
        for season, count in by_season:
            print(f"  - {season}: {count:,}")

        # By state (top 10)
        print(f"\nTop 10 states by coverage:")
        by_state = con.execute("""
            SELECT state_code, COUNT(*) as count
            FROM hs_player_seasons
            WHERE state_code IS NOT NULL
            GROUP BY state_code
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        for state, count in by_state:
            print(f"  - {state}: {count:,}")

        print(f"\n{'='*80}")
        print(f"✅ Load complete! Database ready at: {db_path}")
        print(f"{'='*80}\n")

    finally:
        con.close()


# ==============================================================================
# CLI
# ==============================================================================

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Load HS player-season parquet files into DuckDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load all parquet files from data/ directory
  python scripts/load_to_duckdb.py

  # Rebuild database from scratch
  python scripts/load_to_duckdb.py --rebuild

  # Load only specific sources
  python scripts/load_to_duckdb.py --sources eybl sblive

  # Custom data directory and database path
  python scripts/load_to_duckdb.py --data-dir /path/to/data --db-path /path/to/db.duckdb
        """
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Root data directory containing parquet files (default: data/)"
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/hs_player_seasons.duckdb"),
        help="Path to DuckDB database file (default: data/hs_player_seasons.duckdb)"
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        help="Load only specific sources (e.g., eybl sblive)"
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop and recreate table before loading"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Find parquet files
    parquet_files = find_parquet_files(args.data_dir, args.sources)

    if not parquet_files:
        print(f"❌ No parquet files found in {args.data_dir}")
        if args.sources:
            print(f"   Searched sources: {', '.join(args.sources)}")
        sys.exit(1)

    # Load to DuckDB
    load_parquet_to_duckdb(
        db_path=args.db_path,
        parquet_files=parquet_files,
        rebuild=args.rebuild
    )


if __name__ == "__main__":
    main()
