#!/usr/bin/env python3
"""
EYBL Player Season Backfill Script

Fetches historical player season statistics from Nike EYBL and exports to
canonical HS_PLAYER_SEASON schema as parquet files.

Usage:
    python scripts/backfill_eybl_player_seasons.py --seasons 2024 2023 2022
    python scripts/backfill_eybl_player_seasons.py --seasons 2024 --output data/eybl/
    python scripts/backfill_eybl_player_seasons.py --seasons 2024 --limit 100 --dry-run

Author: Phase 16 - First HS Player-Season Exports
Date: 2025-11-16
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.eybl import EYBLDataSource
from src.models import PlayerSeasonStats


# ==============================================================================
# SCHEMA MAPPING: EYBL Adapter → Canonical HS_PLAYER_SEASON
# ==============================================================================

def map_eybl_to_canonical(
    player_season: PlayerSeasonStats,
    source_url: str,
    scraped_at: datetime
) -> Dict:
    """
    Map EYBL PlayerSeasonStats to canonical HS_PLAYER_SEASON schema.

    EYBL provides per-game averages, not season totals.
    We store averages in the *_per_game fields and set per_game_stats=True.

    Args:
        player_season: PlayerSeasonStats from EYBL adapter
        source_url: URL where stats were scraped
        scraped_at: Timestamp of scraping

    Returns:
        Dictionary conforming to hs_player_season_schema.yaml
    """
    # Extract player ID and name
    player_id = player_season.player_id  # Format: eybl_{name}
    full_name = player_id.replace("eybl_", "").replace("_", " ").title()

    # Split name (best effort)
    name_parts = full_name.split()
    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

    # Build canonical record
    record = {
        # ======================================================================
        # REQUIRED FIELDS
        # ======================================================================

        # Identifiers
        "global_player_id": player_id,  # Initially same as source_player_id
        "source": "eybl",
        "source_player_id": player_id,
        "season": player_season.season,

        # Player metadata
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,

        # Context
        "league": "Nike EYBL",
        "team_id": None,  # EYBL adapter doesn't track team_id yet
        "team_name": player_season.team_name if hasattr(player_season, 'team_name') else None,
        "state_code": None,  # EYBL is national, not state-specific
        "country_code": "US",

        # Core stats (EYBL provides per-game averages, not totals)
        "games_played": player_season.games_played or 0,
        "games_started": None,  # EYBL doesn't track GS
        "minutes": None,  # EYBL doesn't provide minutes

        # Shooting (EYBL doesn't provide raw counts, only percentages)
        "field_goals_made": None,
        "field_goals_attempted": None,
        "three_pointers_made": None,
        "three_pointers_attempted": None,
        "free_throws_made": None,
        "free_throws_attempted": None,

        # Rebounding (EYBL doesn't split OREB/DREB)
        "offensive_rebounds": None,
        "defensive_rebounds": None,
        "total_rebounds": None,  # Will use rebounds_per_game instead

        # Other stats
        "assists": None,
        "steals": None,
        "blocks": None,
        "turnovers": None,
        "personal_fouls": None,
        "points": None,  # Will use points_per_game instead

        # ======================================================================
        # OPTIONAL FIELDS
        # ======================================================================

        # Player attributes
        "position": player_season.position.value if player_season.position else None,
        "jersey_number": None,
        "height_inches": None,
        "weight_lbs": None,
        "graduation_year": None,  # EYBL doesn't provide
        "grade": None,
        "age": None,

        # Percentages (EYBL provides these)
        "field_goal_percentage": player_season.field_goal_percentage,
        "three_point_percentage": player_season.three_point_percentage,
        "free_throw_percentage": player_season.free_throw_percentage,

        # Per-game averages (EYBL's native format)
        "points_per_game": player_season.points_per_game,
        "rebounds_per_game": player_season.rebounds_per_game,
        "assists_per_game": player_season.assists_per_game,
        "steals_per_game": player_season.steals_per_game,
        "blocks_per_game": player_season.blocks_per_game,
        "minutes_per_game": None,

        # Advanced stats
        "true_shooting_percentage": None,
        "effective_field_goal_percentage": None,
        "assist_to_turnover_ratio": None,

        # Metadata
        "per_game_stats": True,  # EYBL provides averages, not totals
        "data_quality_flag": "COMPLETE" if player_season.games_played and player_season.games_played > 0 else "PARTIAL",
        "source_url": source_url,
        "scraped_at": scraped_at.isoformat(),
        "notes": None,
    }

    return record


# ==============================================================================
# BACKFILL LOGIC
# ==============================================================================

async def fetch_eybl_season_stats(
    datasource: EYBLDataSource,
    season: str,
    limit: Optional[int] = None
) -> List[Dict]:
    """
    Fetch all player season stats for a given EYBL season.

    Strategy:
    1. Search for players (gets top scorers/leaderboard)
    2. For each player, fetch full season stats
    3. Convert to canonical schema

    Args:
        datasource: EYBLDataSource instance
        season: Season identifier (e.g., "2024")
        limit: Optional limit on number of players to fetch

    Returns:
        List of player-season records in canonical schema
    """
    print(f"\n{'='*80}")
    print(f"Fetching EYBL {season} Season Stats")
    print(f"{'='*80}\n")

    # Step 1: Get player list (EYBL search_players returns top players)
    print(f"🔍 Searching for EYBL players (season {season})...")
    players = await datasource.search_players(
        name=None,  # Get all players
        season=season,
        limit=limit or 500  # Default to top 500
    )

    if not players:
        print(f"❌ No players found for EYBL {season}")
        return []

    print(f"✅ Found {len(players)} players for season {season}")

    # Step 2: Fetch season stats for each player
    print(f"\n📊 Fetching season stats for {len(players)} players...")

    records = []
    errors = []
    source_url = f"https://nikeeyb.com/cumulative-season-stats?season={season}"
    scraped_at = datetime.utcnow()

    for i, player in enumerate(players, 1):
        try:
            # Fetch season stats
            player_season = await datasource.get_player_season_stats(
                player_id=player.player_id,
                season=season
            )

            if not player_season:
                print(f"  ⚠️  [{i}/{len(players)}] No stats for {player.full_name}")
                continue

            # Convert to canonical schema
            record = map_eybl_to_canonical(player_season, source_url, scraped_at)
            records.append(record)

            # Progress indicator
            if i % 50 == 0:
                print(f"  ✅ [{i}/{len(players)}] Processed {len(records)} player-seasons")

        except Exception as e:
            error_msg = f"Player {player.full_name} ({player.player_id}): {e}"
            errors.append(error_msg)
            print(f"  ❌ [{i}/{len(players)}] {error_msg}")

    print(f"\n✅ Successfully processed {len(records)} player-seasons")
    if errors:
        print(f"⚠️  {len(errors)} errors encountered")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")

    return records


async def backfill_eybl_seasons(
    seasons: List[str],
    output_dir: Path,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> None:
    """
    Backfill EYBL player season stats for specified seasons.

    Args:
        seasons: List of season identifiers (e.g., ["2024", "2023", "2022"])
        output_dir: Directory to write parquet files
        limit: Optional limit on players per season
        dry_run: If True, fetch data but don't write files
    """
    print(f"\n{'='*80}")
    print(f"EYBL Player-Season Backfill")
    print(f"{'='*80}")
    print(f"Seasons: {', '.join(seasons)}")
    print(f"Output: {output_dir}")
    print(f"Limit: {limit or 'None (all players)'}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*80}\n")

    # Initialize EYBL datasource
    print("🔧 Initializing EYBL datasource...")
    datasource = EYBLDataSource()

    all_records = []

    try:
        for season in seasons:
            # Fetch season stats
            records = await fetch_eybl_season_stats(datasource, season, limit)
            all_records.extend(records)

            # Write season-specific parquet
            if records and not dry_run:
                season_file = output_dir / f"eybl_player_seasons_{season}.parquet"
                write_parquet(records, season_file)

        # Write combined parquet for all seasons
        if all_records and not dry_run:
            combined_file = output_dir / "eybl_player_seasons_all.parquet"
            write_parquet(all_records, combined_file)
            print(f"\n✅ Combined file: {combined_file}")

        # Summary
        print(f"\n{'='*80}")
        print(f"Backfill Summary")
        print(f"{'='*80}")
        print(f"Total player-seasons: {len(all_records)}")
        print(f"Seasons covered: {len(seasons)}")
        print(f"Output directory: {output_dir}")
        if dry_run:
            print(f"⚠️  DRY RUN - No files written")
        print(f"{'='*80}\n")

    finally:
        # Clean up
        await datasource.close()


def write_parquet(records: List[Dict], output_file: Path) -> None:
    """
    Write records to parquet file with proper schema.

    Args:
        records: List of player-season records
        output_file: Path to output parquet file
    """
    if not records:
        print(f"⚠️  No records to write to {output_file}")
        return

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert to pandas DataFrame
    df = pd.DataFrame(records)

    # Define schema (ensures consistent types across files)
    schema = pa.schema([
        # Identifiers
        ("global_player_id", pa.string()),
        ("source", pa.string()),
        ("source_player_id", pa.string()),
        ("season", pa.string()),

        # Player metadata
        ("first_name", pa.string()),
        ("last_name", pa.string()),
        ("full_name", pa.string()),

        # Context
        ("league", pa.string()),
        ("team_id", pa.string()),
        ("team_name", pa.string()),
        ("state_code", pa.string()),
        ("country_code", pa.string()),

        # Core stats
        ("games_played", pa.int64()),
        ("games_started", pa.int64()),
        ("minutes", pa.float64()),

        # Shooting
        ("field_goals_made", pa.int64()),
        ("field_goals_attempted", pa.int64()),
        ("three_pointers_made", pa.int64()),
        ("three_pointers_attempted", pa.int64()),
        ("free_throws_made", pa.int64()),
        ("free_throws_attempted", pa.int64()),

        # Rebounding
        ("offensive_rebounds", pa.int64()),
        ("defensive_rebounds", pa.int64()),
        ("total_rebounds", pa.int64()),

        # Other stats
        ("assists", pa.int64()),
        ("steals", pa.int64()),
        ("blocks", pa.int64()),
        ("turnovers", pa.int64()),
        ("personal_fouls", pa.int64()),
        ("points", pa.int64()),

        # Player attributes
        ("position", pa.string()),
        ("jersey_number", pa.int64()),
        ("height_inches", pa.int64()),
        ("weight_lbs", pa.int64()),
        ("graduation_year", pa.int64()),
        ("grade", pa.int64()),
        ("age", pa.int64()),

        # Percentages
        ("field_goal_percentage", pa.float64()),
        ("three_point_percentage", pa.float64()),
        ("free_throw_percentage", pa.float64()),

        # Per-game averages
        ("points_per_game", pa.float64()),
        ("rebounds_per_game", pa.float64()),
        ("assists_per_game", pa.float64()),
        ("steals_per_game", pa.float64()),
        ("blocks_per_game", pa.float64()),
        ("minutes_per_game", pa.float64()),

        # Advanced stats
        ("true_shooting_percentage", pa.float64()),
        ("effective_field_goal_percentage", pa.float64()),
        ("assist_to_turnover_ratio", pa.float64()),

        # Metadata
        ("per_game_stats", pa.bool_()),
        ("data_quality_flag", pa.string()),
        ("source_url", pa.string()),
        ("scraped_at", pa.string()),
        ("notes", pa.string()),
    ])

    # Write to parquet
    table = pa.Table.from_pandas(df, schema=schema)
    pq.write_table(table, output_file, compression='snappy')

    print(f"✅ Wrote {len(records)} records to {output_file}")

    # Print summary stats
    print(f"   - Games played: {df['games_played'].sum():,}")
    print(f"   - Avg PPG: {df['points_per_game'].mean():.2f}")
    print(f"   - Avg RPG: {df['rebounds_per_game'].mean():.2f}")
    print(f"   - Avg APG: {df['assists_per_game'].mean():.2f}")


# ==============================================================================
# CLI
# ==============================================================================

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill EYBL player season statistics to parquet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill 2024, 2023, 2022 seasons
  python scripts/backfill_eybl_player_seasons.py --seasons 2024 2023 2022

  # Backfill just 2024 with limit
  python scripts/backfill_eybl_player_seasons.py --seasons 2024 --limit 100

  # Dry run (fetch but don't write)
  python scripts/backfill_eybl_player_seasons.py --seasons 2024 --dry-run

  # Custom output directory
  python scripts/backfill_eybl_player_seasons.py --seasons 2024 --output /tmp/eybl/
        """
    )

    parser.add_argument(
        "--seasons",
        nargs="+",
        required=True,
        help="Seasons to backfill (e.g., 2024 2023 2022)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/eybl"),
        help="Output directory for parquet files (default: data/eybl/)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of players per season (for testing)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch data but don't write files"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Run async backfill
    asyncio.run(backfill_eybl_seasons(
        seasons=args.seasons,
        output_dir=args.output,
        limit=args.limit,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
