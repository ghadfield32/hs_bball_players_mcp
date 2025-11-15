#!/usr/bin/env python3
"""
Backfill Historical Snapshots & Player Vectors

Populates historical_snapshots and player_vectors tables from existing
player_season_stats data in DuckDB.

**Purpose**: Enable multi-season tracking and player similarity searches
**Tables**: historical_snapshots, player_vectors
**Data Source**: Existing player_season_stats table in DuckDB
**Process**:
  1. Read all player_season_stats records
  2. Create historical snapshot for each player/season combination
  3. Normalize stats to create 12-dimensional player vectors
  4. Insert into DuckDB tables

Usage:
    python scripts/backfill_historical_snapshots.py [--dry-run] [--limit 100]

Author: Claude Code
Date: 2025-11-15
Enhancement: 11 (Coverage Enhancements 3, 4, 8)
"""

import argparse
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.duckdb_storage import get_duckdb_storage
from src.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_stat(
    value: Optional[float],
    min_val: float,
    max_val: float
) -> float:
    """
    Normalize a stat to 0-1 range.

    Args:
        value: Stat value
        min_val: Minimum value in dataset
        max_val: Maximum value in dataset

    Returns:
        Normalized value (0.0-1.0)
    """
    if value is None:
        return 0.0

    if max_val == min_val:
        return 0.5  # All values the same

    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))  # Clamp to [0, 1]


def calculate_per_40_stats(stats: Dict) -> Dict:
    """
    Calculate per-40 minute stats from totals.

    Args:
        stats: Dict with games_played, minutes, points, rebounds, etc.

    Returns:
        Dict with per-40 stats
    """
    games = stats.get("games_played", 0)
    minutes = stats.get("minutes_played")

    if not games or not minutes or minutes == 0:
        return {
            "ppg_per40": 0.0,
            "rpg_per40": 0.0,
            "apg_per40": 0.0,
            "spg_per40": 0.0,
            "bpg_per40": 0.0,
        }

    # Calculate per-game averages first
    ppg = (stats.get("points") or 0) / games
    rpg = (stats.get("rebounds") or 0) / games
    apg = (stats.get("assists") or 0) / games
    spg = (stats.get("steals") or 0) / games
    bpg = (stats.get("blocks") or 0) / games

    # Calculate per-40
    mpg = minutes / games
    if mpg == 0:
        mpg = 1  # Avoid division by zero

    multiplier = 40.0 / mpg

    return {
        "ppg_per40": ppg * multiplier,
        "rpg_per40": rpg * multiplier,
        "apg_per40": apg * multiplier,
        "spg_per40": spg * multiplier,
        "bpg_per40": bpg * multiplier,
    }


def create_player_vector(
    stats: Dict,
    normalization_params: Dict
) -> Dict:
    """
    Create 12-dimensional normalized vector for a player.

    Dimensions:
    1-5: Per-40 stats (PPG, RPG, APG, SPG, BPG)
    6-8: Efficiency (TS%, eFG%, A/TO)
    9-10: Physical (height, weight)
    11: Age context (age_for_grade)
    12: Usage (MPG)

    Args:
        stats: Player stats dict
        normalization_params: Min/max values for normalization

    Returns:
        Dict with normalized vector components
    """
    # Calculate per-40 stats
    per40 = calculate_per_40_stats(stats)

    # Get normalization ranges
    ppg_range = normalization_params.get("ppg_per40", (0, 40))
    rpg_range = normalization_params.get("rpg_per40", (0, 20))
    apg_range = normalization_params.get("apg_per40", (0, 15))
    spg_range = normalization_params.get("spg_per40", (0, 5))
    bpg_range = normalization_params.get("bpg_per40", (0, 5))
    ts_range = normalization_params.get("ts_pct", (0, 1))
    efg_range = normalization_params.get("efg_pct", (0, 1))
    ato_range = normalization_params.get("ato_ratio", (0, 5))
    height_range = normalization_params.get("height", (65, 85))
    weight_range = normalization_params.get("weight", (150, 300))
    age_range = normalization_params.get("age_for_grade", (-2, 2))
    mpg_range = normalization_params.get("mpg", (0, 40))

    # Create normalized vector
    vector = {
        "ppg_per40_norm": normalize_stat(per40["ppg_per40"], *ppg_range),
        "rpg_per40_norm": normalize_stat(per40["rpg_per40"], *rpg_range),
        "apg_per40_norm": normalize_stat(per40["apg_per40"], *apg_range),
        "spg_per40_norm": normalize_stat(per40["spg_per40"], *spg_range),
        "bpg_per40_norm": normalize_stat(per40["bpg_per40"], *bpg_range),
        "ts_pct_norm": normalize_stat(stats.get("true_shooting_pct"), *ts_range),
        "efg_pct_norm": normalize_stat(stats.get("effective_fg_pct"), *efg_range),
        "ato_ratio_norm": normalize_stat(stats.get("assist_to_turnover_ratio"), *ato_range),
        "height_norm": normalize_stat(stats.get("height"), *height_range),
        "weight_norm": normalize_stat(stats.get("weight"), *weight_range),
        "age_for_grade_norm": normalize_stat(stats.get("age_for_grade"), *age_range),
        "mpg_norm": normalize_stat(
            stats.get("minutes_played") / stats.get("games_played", 1) if stats.get("games_played") else 0,
            *mpg_range
        ),
    }

    return vector


async def read_player_season_stats(storage, limit: Optional[int] = None) -> List[Dict]:
    """
    Read all player_season_stats from DuckDB.

    Args:
        storage: DuckDBStorage instance
        limit: Optional limit on number of records

    Returns:
        List of stats dicts
    """
    query = """
        SELECT
            player_id,
            player_name,
            season,
            league,
            games_played,
            minutes_played,
            points,
            rebounds,
            assists,
            steals,
            blocks,
            turnovers,
            true_shooting_pct,
            effective_fg_pct,
            assist_to_turnover_ratio,
            field_goal_pct,
            three_point_pct,
            free_throw_pct,
            source_type
        FROM player_season_stats
    """

    if limit:
        query += f" LIMIT {limit}"

    result = storage.conn.execute(query).fetchall()

    stats_list = []
    for row in result:
        stats_list.append({
            "player_id": row[0],
            "player_name": row[1],
            "season": row[2],
            "league": row[3],
            "games_played": row[4],
            "minutes_played": row[5],
            "points": row[6],
            "rebounds": row[7],
            "assists": row[8],
            "steals": row[9],
            "blocks": row[10],
            "turnovers": row[11],
            "true_shooting_pct": row[12],
            "effective_fg_pct": row[13],
            "assist_to_turnover_ratio": row[14],
            "field_goal_pct": row[15],
            "three_point_pct": row[16],
            "free_throw_pct": row[17],
            "source_type": row[18],
        })

    logger.info(f"Read {len(stats_list)} player_season_stats records from DuckDB")
    return stats_list


async def create_snapshots_and_vectors(
    stats_list: List[Dict],
    dry_run: bool = False
) -> Tuple[List[Dict], List[Dict]]:
    """
    Create historical snapshots and player vectors from stats.

    Args:
        stats_list: List of player_season_stats dicts
        dry_run: If True, don't insert into database

    Returns:
        Tuple of (snapshots, vectors)
    """
    if not stats_list:
        return [], []

    # Calculate normalization parameters (min/max for each stat)
    normalization_params = {
        "ppg_per40": (0, 50),  # Reasonable ranges
        "rpg_per40": (0, 25),
        "apg_per40": (0, 20),
        "spg_per40": (0, 6),
        "bpg_per40": (0, 6),
        "ts_pct": (0.0, 1.0),
        "efg_pct": (0.0, 1.0),
        "ato_ratio": (0.0, 6.0),
        "height": (65, 85),  # inches
        "weight": (150, 300),  # lbs
        "age_for_grade": (-2.0, 2.0),  # years
        "mpg": (0, 40),
    }

    snapshots = []
    vectors = []

    for stats in stats_list:
        # Create historical snapshot
        snapshot_id = str(uuid4())
        player_uid = stats["player_id"]  # Should be enhanced UID in future
        season = stats["season"]

        # Parse season to date (use start of season)
        try:
            season_year = int(season.split("-")[0]) if season else datetime.now().year
            snapshot_date = date(season_year, 10, 1)  # October 1st
        except:
            snapshot_date = date.today()

        # Calculate per-game stats
        games = stats.get("games_played", 0)
        if games > 0:
            ppg = (stats.get("points") or 0) / games
            rpg = (stats.get("rebounds") or 0) / games
            apg = (stats.get("assists") or 0) / games
        else:
            ppg = rpg = apg = 0.0

        snapshot = {
            "snapshot_id": snapshot_id,
            "player_uid": player_uid,
            "snapshot_date": snapshot_date,
            "season": season,
            "grad_year": None,  # Not available in stats table
            # Bio snapshot
            "height": None,
            "weight": None,
            "position": None,
            "birth_date": None,
            # Recruiting snapshot
            "composite_247_rating": None,
            "stars_247": None,
            "power_6_offer_count": None,
            "total_offer_count": None,
            # Performance snapshot
            "ppg": ppg,
            "rpg": rpg,
            "apg": apg,
            "ts_pct": stats.get("true_shooting_pct"),
            "efg_pct": stats.get("effective_fg_pct"),
            "ato_ratio": stats.get("assist_to_turnover_ratio"),
            # Context
            "school_name": None,
            "state": None,
            "league": stats.get("league"),
            "competition_level": "Circuit" if stats.get("league") in ["EYBL", "UAA", "3SSB"] else "State/Regional",
            "source_type": stats.get("source_type", "unknown"),
            "retrieved_at": datetime.now(),
        }

        snapshots.append(snapshot)

        # Create player vector
        vector_id = str(uuid4())
        vector_data = create_player_vector(stats, normalization_params)

        vector = {
            "vector_id": vector_id,
            "player_uid": player_uid,
            "season": season,
            **vector_data,
        }

        vectors.append(vector)

    logger.info(f"Created {len(snapshots)} snapshots and {len(vectors)} vectors")

    return snapshots, vectors


async def insert_snapshots(storage, snapshots: List[Dict], dry_run: bool = False) -> int:
    """
    Insert historical snapshots into DuckDB.

    Args:
        storage: DuckDBStorage instance
        snapshots: List of snapshot dicts
        dry_run: If True, don't actually insert

    Returns:
        Number of snapshots inserted
    """
    if dry_run:
        logger.info(f"DRY RUN: Would insert {len(snapshots)} snapshots")
        return 0

    if not snapshots:
        return 0

    # Use parameterized insert for efficiency
    insert_query = """
        INSERT INTO historical_snapshots (
            snapshot_id, player_uid, snapshot_date, season, grad_year,
            height, weight, position, birth_date,
            composite_247_rating, stars_247, power_6_offer_count, total_offer_count,
            ppg, rpg, apg, ts_pct, efg_pct, ato_ratio,
            school_name, state, league, competition_level,
            source_type, retrieved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    inserted = 0
    for snapshot in snapshots:
        try:
            storage.conn.execute(insert_query, [
                snapshot["snapshot_id"],
                snapshot["player_uid"],
                snapshot["snapshot_date"],
                snapshot["season"],
                snapshot["grad_year"],
                snapshot["height"],
                snapshot["weight"],
                snapshot["position"],
                snapshot["birth_date"],
                snapshot["composite_247_rating"],
                snapshot["stars_247"],
                snapshot["power_6_offer_count"],
                snapshot["total_offer_count"],
                snapshot["ppg"],
                snapshot["rpg"],
                snapshot["apg"],
                snapshot["ts_pct"],
                snapshot["efg_pct"],
                snapshot["ato_ratio"],
                snapshot["school_name"],
                snapshot["state"],
                snapshot["league"],
                snapshot["competition_level"],
                snapshot["source_type"],
                snapshot["retrieved_at"],
            ])
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert snapshot: {e}")

    logger.info(f"Inserted {inserted} historical snapshots into DuckDB")
    return inserted


async def insert_vectors(storage, vectors: List[Dict], dry_run: bool = False) -> int:
    """
    Insert player vectors into DuckDB.

    Args:
        storage: DuckDBStorage instance
        vectors: List of vector dicts
        dry_run: If True, don't actually insert

    Returns:
        Number of vectors inserted
    """
    if dry_run:
        logger.info(f"DRY RUN: Would insert {len(vectors)} vectors")
        return 0

    if not vectors:
        return 0

    insert_query = """
        INSERT INTO player_vectors (
            vector_id, player_uid, season,
            ppg_per40_norm, rpg_per40_norm, apg_per40_norm, spg_per40_norm, bpg_per40_norm,
            ts_pct_norm, efg_pct_norm, ato_ratio_norm,
            height_norm, weight_norm, age_for_grade_norm, mpg_norm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    inserted = 0
    for vector in vectors:
        try:
            storage.conn.execute(insert_query, [
                vector["vector_id"],
                vector["player_uid"],
                vector["season"],
                vector["ppg_per40_norm"],
                vector["rpg_per40_norm"],
                vector["apg_per40_norm"],
                vector["spg_per40_norm"],
                vector["bpg_per40_norm"],
                vector["ts_pct_norm"],
                vector["efg_pct_norm"],
                vector["ato_ratio_norm"],
                vector["height_norm"],
                vector["weight_norm"],
                vector["age_for_grade_norm"],
                vector["mpg_norm"],
            ])
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert vector: {e}")

    logger.info(f"Inserted {inserted} player vectors into DuckDB")
    return inserted


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill historical snapshots and player vectors from existing data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't actually insert data)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of records to process"
    )

    args = parser.parse_args()

    logger.info("Starting backfill of historical snapshots and player vectors")

    # Connect to DuckDB
    storage = get_duckdb_storage()

    # Read existing player_season_stats
    stats_list = await read_player_season_stats(storage, limit=args.limit)

    if not stats_list:
        logger.warning("No player_season_stats found in DuckDB. Exiting.")
        return

    # Create snapshots and vectors
    snapshots, vectors = await create_snapshots_and_vectors(stats_list, dry_run=args.dry_run)

    # Insert into DuckDB
    snapshot_count = await insert_snapshots(storage, snapshots, dry_run=args.dry_run)
    vector_count = await insert_vectors(storage, vectors, dry_run=args.dry_run)

    # Summary
    print(f"\n{'='*80}")
    print(f"BACKFILL SUMMARY")
    print(f"{'='*80}")
    print(f"Stats Records Processed: {len(stats_list)}")
    print(f"Historical Snapshots Created: {len(snapshots)}")
    print(f"Player Vectors Created: {len(vectors)}")
    if not args.dry_run:
        print(f"Snapshots Inserted: {snapshot_count}")
        print(f"Vectors Inserted: {vector_count}")
    else:
        print(f"DRY RUN - No data inserted")
    print(f"{'='*80}\n")

    logger.info("✅ Backfill complete!")


if __name__ == "__main__":
    asyncio.run(main())
