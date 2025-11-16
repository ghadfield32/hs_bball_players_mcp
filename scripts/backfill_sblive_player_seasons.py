#!/usr/bin/env python3
"""
SBLive Player Season Backfill Script

Fetches player season statistics from SBLive Sports (multi-state) and exports
to canonical HS_PLAYER_SEASON schema as parquet files.

Usage:
    python scripts/backfill_sblive_player_seasons.py --states WA OR CA --season 2024-25
    python scripts/backfill_sblive_player_seasons.py --states TX FL --season 2024-25 --limit 50
    python scripts/backfill_sblive_player_seasons.py --states WA --season 2024-25 --dry-run

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

from src.datasources.us.sblive import SBLiveDataSource
from src.models import PlayerSeasonStats


# ==============================================================================
# SCHEMA MAPPING: SBLive Adapter → Canonical HS_PLAYER_SEASON
# ==============================================================================

def map_sblive_to_canonical(
    player_season: PlayerSeasonStats,
    state_code: str,
    source_url: str,
    scraped_at: datetime
) -> Dict:
    """
    Map SBLive PlayerSeasonStats to canonical HS_PLAYER_SEASON schema.

    SBLive typically provides season totals, not per-game averages.
    We store totals in the count fields and calculate averages.

    Args:
        player_season: PlayerSeasonStats from SBLive adapter
        state_code: State code (WA, OR, CA, etc.)
        source_url: URL where stats were scraped
        scraped_at: Timestamp of scraping

    Returns:
        Dictionary conforming to hs_player_season_schema.yaml
    """
    # Extract player ID and name
    player_id = player_season.player_id  # Format: sblive_{state}_{name}
    full_name = (
        player_id
        .replace(f"sblive_{state_code.lower()}_", "")
        .replace("_", " ")
        .title()
    )

    # Split name (best effort)
    name_parts = full_name.split()
    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

    # Calculate per-game stats if we have totals
    games = player_season.games_played or 1  # Avoid division by zero
    ppg = (player_season.points_per_game or
           (player_season.points / games if player_season.points else None))
    rpg = (player_season.rebounds_per_game or
           (player_season.total_rebounds / games if player_season.total_rebounds else None))
    apg = (player_season.assists_per_game or
           (player_season.assists / games if player_season.assists else None))
    spg = (player_season.steals_per_game or
           (player_season.steals / games if player_season.steals else None))
    bpg = (player_season.blocks_per_game or
           (player_season.blocks / games if player_season.blocks else None))
    mpg = (player_season.minutes_per_game or
           (player_season.minutes / games if player_season.minutes else None))

    # Build canonical record
    record = {
        # ======================================================================
        # REQUIRED FIELDS
        # ======================================================================

        # Identifiers
        "global_player_id": player_id,  # Initially same as source_player_id
        "source": "sblive",
        "source_player_id": player_id,
        "season": player_season.season,

        # Player metadata
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,

        # Context
        "league": f"SBLive {state_code}",
        "team_id": None,  # SBLive adapter could extract this
        "team_name": player_season.team_name if hasattr(player_season, 'team_name') else None,
        "state_code": state_code,
        "country_code": "US",

        # Core stats (SBLive provides season totals)
        "games_played": player_season.games_played or 0,
        "games_started": None,  # SBLive doesn't track GS typically
        "minutes": player_season.minutes,

        # Shooting (SBLive provides raw counts)
        "field_goals_made": player_season.field_goals_made,
        "field_goals_attempted": player_season.field_goals_attempted,
        "three_pointers_made": player_season.three_pointers_made,
        "three_pointers_attempted": player_season.three_pointers_attempted,
        "free_throws_made": player_season.free_throws_made,
        "free_throws_attempted": player_season.free_throws_attempted,

        # Rebounding
        "offensive_rebounds": player_season.offensive_rebounds,
        "defensive_rebounds": player_season.defensive_rebounds,
        "total_rebounds": player_season.total_rebounds,

        # Other stats
        "assists": player_season.assists,
        "steals": player_season.steals,
        "blocks": player_season.blocks,
        "turnovers": player_season.turnovers,
        "personal_fouls": None,  # Check if SBLive tracks this
        "points": player_season.points,

        # ======================================================================
        # OPTIONAL FIELDS
        # ======================================================================

        # Player attributes
        "position": player_season.position.value if player_season.position else None,
        "jersey_number": None,
        "height_inches": None,
        "weight_lbs": None,
        "graduation_year": None,
        "grade": None,
        "age": None,

        # Percentages (calculate from counts)
        "field_goal_percentage": (
            player_season.field_goals_made / player_season.field_goals_attempted
            if player_season.field_goals_made and player_season.field_goals_attempted
            else player_season.field_goal_percentage
        ),
        "three_point_percentage": (
            player_season.three_pointers_made / player_season.three_pointers_attempted
            if player_season.three_pointers_made and player_season.three_pointers_attempted
            else player_season.three_point_percentage
        ),
        "free_throw_percentage": (
            player_season.free_throws_made / player_season.free_throws_attempted
            if player_season.free_throws_made and player_season.free_throws_attempted
            else player_season.free_throw_percentage
        ),

        # Per-game averages (calculated from totals)
        "points_per_game": ppg,
        "rebounds_per_game": rpg,
        "assists_per_game": apg,
        "steals_per_game": spg,
        "blocks_per_game": bpg,
        "minutes_per_game": mpg,

        # Advanced stats
        "true_shooting_percentage": None,  # Can calculate if needed
        "effective_field_goal_percentage": None,
        "assist_to_turnover_ratio": (
            player_season.assists / player_season.turnovers
            if player_season.assists and player_season.turnovers and player_season.turnovers > 0
            else None
        ),

        # Metadata
        "per_game_stats": False,  # SBLive provides totals
        "data_quality_flag": "COMPLETE" if player_season.games_played and player_season.games_played > 0 else "PARTIAL",
        "source_url": source_url,
        "scraped_at": scraped_at.isoformat(),
        "notes": None,
    }

    return record


# ==============================================================================
# BACKFILL LOGIC
# ==============================================================================

async def fetch_sblive_state_stats(
    datasource: SBLiveDataSource,
    state_code: str,
    season: str,
    limit: Optional[int] = None
) -> List[Dict]:
    """
    Fetch all player season stats for a given SBLive state and season.

    Args:
        datasource: SBLiveDataSource instance
        state_code: State code (WA, OR, CA, etc.)
        season: Season identifier (e.g., "2024-25")
        limit: Optional limit on number of players to fetch

    Returns:
        List of player-season records in canonical schema
    """
    print(f"\n{'='*80}")
    print(f"Fetching SBLive {state_code} - {season} Stats")
    print(f"{'='*80}\n")

    # Step 1: Get player list for state
    print(f"🔍 Searching for {state_code} players (season {season})...")
    try:
        players = await datasource.search_players(
            state=state_code,
            name=None,  # Get all players
            season=season,
            limit=limit or 500  # Default to top 500
        )
    except ValueError as e:
        print(f"❌ State validation error: {e}")
        return []

    if not players:
        print(f"❌ No players found for {state_code} {season}")
        return []

    print(f"✅ Found {len(players)} players for {state_code} {season}")

    # Step 2: Fetch season stats for each player
    print(f"\n📊 Fetching season stats for {len(players)} players...")

    records = []
    errors = []
    source_url = f"https://{state_code.lower()}.sblive.com/high-school/boys-basketball/stats"
    scraped_at = datetime.utcnow()

    for i, player in enumerate(players, 1):
        try:
            # Fetch season stats
            player_season = await datasource.get_player_season_stats(
                player_id=player.player_id,
                season=season,
                state=state_code
            )

            if not player_season:
                print(f"  ⚠️  [{i}/{len(players)}] No stats for {player.full_name}")
                continue

            # Convert to canonical schema
            record = map_sblive_to_canonical(
                player_season, state_code, source_url, scraped_at
            )
            records.append(record)

            # Progress indicator
            if i % 50 == 0:
                print(f"  ✅ [{i}/{len(players)}] Processed {len(records)} player-seasons")

        except Exception as e:
            error_msg = f"Player {player.full_name} ({player.player_id}): {e}"
            errors.append(error_msg)
            print(f"  ❌ [{i}/{len(players)}] {error_msg}")

    print(f"\n✅ Successfully processed {len(records)} player-seasons for {state_code}")
    if errors:
        print(f"⚠️  {len(errors)} errors encountered")
        for error in errors[:3]:  # Show first 3 errors
            print(f"  - {error}")
        if len(errors) > 3:
            print(f"  ... and {len(errors) - 3} more")

    return records


async def backfill_sblive_states(
    states: List[str],
    season: str,
    output_dir: Path,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> None:
    """
    Backfill SBLive player season stats for specified states.

    Args:
        states: List of state codes (e.g., ["WA", "OR", "CA"])
        season: Season identifier (e.g., "2024-25")
        output_dir: Directory to write parquet files
        limit: Optional limit on players per state
        dry_run: If True, fetch data but don't write files
    """
    print(f"\n{'='*80}")
    print(f"SBLive Player-Season Backfill")
    print(f"{'='*80}")
    print(f"States: {', '.join(states)}")
    print(f"Season: {season}")
    print(f"Output: {output_dir}")
    print(f"Limit: {limit or 'None (all players)'}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*80}\n")

    # Initialize SBLive datasource
    print("🔧 Initializing SBLive datasource...")
    datasource = SBLiveDataSource()

    all_records = []

    try:
        for state_code in states:
            # Fetch state stats
            records = await fetch_sblive_state_stats(
                datasource, state_code, season, limit
            )
            all_records.extend(records)

            # Write state-specific parquet
            if records and not dry_run:
                state_file = output_dir / f"sblive_{state_code.lower()}_{season.replace('-', '_')}.parquet"
                write_parquet(records, state_file)

        # Write combined parquet for all states
        if all_records and not dry_run:
            combined_file = output_dir / f"sblive_all_states_{season.replace('-', '_')}.parquet"
            write_parquet(all_records, combined_file)
            print(f"\n✅ Combined file: {combined_file}")

        # Summary
        print(f"\n{'='*80}")
        print(f"Backfill Summary")
        print(f"{'='*80}")
        print(f"Total player-seasons: {len(all_records)}")
        print(f"States covered: {len(states)} ({', '.join(states)})")
        print(f"Season: {season}")
        print(f"Output directory: {output_dir}")
        if dry_run:
            print(f"⚠️  DRY RUN - No files written")
        print(f"{'='*80}\n")

    finally:
        # Clean up
        await datasource.close()


def write_parquet(records: List[Dict], output_file: Path) -> None:
    """Write records to parquet file (same schema as EYBL)."""
    if not records:
        print(f"⚠️  No records to write to {output_file}")
        return

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert to pandas DataFrame
    df = pd.DataFrame(records)

    # Define schema (same as EYBL for consistency)
    schema = pa.schema([
        # [Same schema as EYBL backfill - omitted for brevity]
        # See backfill_eybl_player_seasons.py for full schema
        ("global_player_id", pa.string()),
        ("source", pa.string()),
        ("source_player_id", pa.string()),
        ("season", pa.string()),
        ("first_name", pa.string()),
        ("last_name", pa.string()),
        ("full_name", pa.string()),
        ("league", pa.string()),
        ("team_id", pa.string()),
        ("team_name", pa.string()),
        ("state_code", pa.string()),
        ("country_code", pa.string()),
        ("games_played", pa.int64()),
        ("games_started", pa.int64()),
        ("minutes", pa.float64()),
        ("field_goals_made", pa.int64()),
        ("field_goals_attempted", pa.int64()),
        ("three_pointers_made", pa.int64()),
        ("three_pointers_attempted", pa.int64()),
        ("free_throws_made", pa.int64()),
        ("free_throws_attempted", pa.int64()),
        ("offensive_rebounds", pa.int64()),
        ("defensive_rebounds", pa.int64()),
        ("total_rebounds", pa.int64()),
        ("assists", pa.int64()),
        ("steals", pa.int64()),
        ("blocks", pa.int64()),
        ("turnovers", pa.int64()),
        ("personal_fouls", pa.int64()),
        ("points", pa.int64()),
        ("position", pa.string()),
        ("jersey_number", pa.int64()),
        ("height_inches", pa.int64()),
        ("weight_lbs", pa.int64()),
        ("graduation_year", pa.int64()),
        ("grade", pa.int64()),
        ("age", pa.int64()),
        ("field_goal_percentage", pa.float64()),
        ("three_point_percentage", pa.float64()),
        ("free_throw_percentage", pa.float64()),
        ("points_per_game", pa.float64()),
        ("rebounds_per_game", pa.float64()),
        ("assists_per_game", pa.float64()),
        ("steals_per_game", pa.float64()),
        ("blocks_per_game", pa.float64()),
        ("minutes_per_game", pa.float64()),
        ("true_shooting_percentage", pa.float64()),
        ("effective_field_goal_percentage", pa.float64()),
        ("assist_to_turnover_ratio", pa.float64()),
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
    if 'games_played' in df.columns:
        print(f"   - Games played: {df['games_played'].sum():,}")
    if 'points_per_game' in df.columns:
        print(f"   - Avg PPG: {df['points_per_game'].mean():.2f}")
    if 'rebounds_per_game' in df.columns:
        print(f"   - Avg RPG: {df['rebounds_per_game'].mean():.2f}")
    if 'assists_per_game' in df.columns:
        print(f"   - Avg APG: {df['assists_per_game'].mean():.2f}")


# ==============================================================================
# CLI
# ==============================================================================

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill SBLive player season statistics to parquet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill Washington, Oregon, California for 2024-25
  python scripts/backfill_sblive_player_seasons.py --states WA OR CA --season 2024-25

  # Backfill just Texas with limit
  python scripts/backfill_sblive_player_seasons.py --states TX --season 2024-25 --limit 100

  # Dry run
  python scripts/backfill_sblive_player_seasons.py --states WA --season 2024-25 --dry-run

  # Custom output directory
  python scripts/backfill_sblive_player_seasons.py --states WA OR --season 2024-25 --output /tmp/sblive/
        """
    )

    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="State codes to backfill (e.g., WA OR CA TX FL)"
    )

    parser.add_argument(
        "--season",
        required=True,
        help="Season to backfill (e.g., 2024-25)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/sblive"),
        help="Output directory for parquet files (default: data/sblive/)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of players per state (for testing)"
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

    # Normalize state codes to uppercase
    states = [s.upper() for s in args.states]

    # Run async backfill
    asyncio.run(backfill_sblive_states(
        states=states,
        season=args.season,
        output_dir=args.output,
        limit=args.limit,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
