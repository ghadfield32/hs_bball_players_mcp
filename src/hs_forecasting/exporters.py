"""
Data Export Adapters for HS Forecasting

This module bridges the gap between existing datasource schemas (DuckDB, Pydantic models)
and the dataset_builder expected schemas. It handles column mapping, type conversion,
and graceful handling of missing data.

Created: 2025-11-15
Phase: 14 (Data Validation & Export)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def export_eybl_from_duckdb(
    duckdb_conn,
    output_path: Path,
    season: Optional[str] = None,
    grad_year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Export EYBL player season stats from DuckDB to dataset_builder compatible Parquet.

    This function queries the DuckDB player_season_stats table and maps columns
    to match the schema expected by standardize_eybl_stats().

    Args:
        duckdb_conn: DuckDB connection object
        output_path: Output path for Parquet file
        season: Optional season filter (e.g., "2024-25")
        grad_year: Optional grad year filter (requires join with players table)

    Returns:
        DataFrame with EYBL stats in dataset_builder schema

    Schema Mapping:
        DuckDB Column          → dataset_builder Column
        -------------------      ----------------------
        player_name            → player_name
        games_played           → gp
        points_per_game        → pts_per_game
        rebounds_per_game      → reb_per_game
        assists_per_game       → ast_per_game
        three_point_percentage → three_pct (converted from % to decimal)
    """
    try:
        logger.info("Exporting EYBL data from DuckDB")

        # Build query with optional filters
        query = """
            SELECT
                s.player_name,
                s.games_played,
                s.points_per_game,
                s.rebounds_per_game,
                s.assists_per_game,
                s.steals_per_game,
                s.blocks_per_game,
                s.field_goals_made,
                s.field_goals_attempted,
                s.three_pointers_made,
                s.three_pointers_attempted,
                s.free_throws_made,
                s.free_throws_attempted,
                s.turnovers,
                s.season,
                s.source_type
            FROM player_season_stats s
            WHERE s.source_type IN ('eybl', 'eybl_girls')
        """

        # Add filters
        if season:
            query += f" AND s.season = '{season}'"

        # If grad_year is provided, join with players table
        if grad_year:
            query = query.replace(
                "FROM player_season_stats s",
                """
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
                """,
            )
            query += f" AND p.grad_year = {grad_year}"

        # Execute query
        df = duckdb_conn.execute(query).df()

        if df.empty:
            logger.warning(
                "No EYBL data found in DuckDB",
                filters={"season": season, "grad_year": grad_year},
            )
            return df

        logger.info(f"Retrieved {len(df)} EYBL player-season records from DuckDB")

        # Column mapping to dataset_builder schema
        rename_map = {
            "games_played": "gp",
            "points_per_game": "pts_per_game",
            "rebounds_per_game": "reb_per_game",
            "assists_per_game": "ast_per_game",
            "steals_per_game": "stl_per_game",
            "blocks_per_game": "blk_per_game",
        }

        df = df.rename(columns=rename_map)

        # Calculate shooting percentages (convert from totals if needed)
        if "field_goals_made" in df.columns and "field_goals_attempted" in df.columns:
            df["fg_pct"] = (
                df["field_goals_made"] / df["field_goals_attempted"].replace(0, pd.NA)
            ) * 100

        if "three_pointers_made" in df.columns and "three_pointers_attempted" in df.columns:
            df["three_pct"] = (
                df["three_pointers_made"] / df["three_pointers_attempted"].replace(0, pd.NA)
            ) * 100

        if "free_throws_made" in df.columns and "free_throws_attempted" in df.columns:
            df["ft_pct"] = (
                df["free_throws_made"] / df["free_throws_attempted"].replace(0, pd.NA)
            ) * 100

        # Calculate per-game attempt stats
        if "gp" in df.columns and df["gp"].notna().any():
            if "field_goals_attempted" in df.columns:
                df["fga_per_game"] = df["field_goals_attempted"] / df["gp"]

            if "three_pointers_attempted" in df.columns:
                df["three_att_per_game"] = df["three_pointers_attempted"] / df["gp"]

            if "free_throws_attempted" in df.columns:
                df["fta_per_game"] = df["free_throws_attempted"] / df["gp"]

            if "turnovers" in df.columns:
                df["tov_per_game"] = df["turnovers"] / df["gp"]

        # Save to Parquet
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        logger.info(f"EYBL data exported to {output_path}")

        return df

    except Exception as e:
        logger.error(f"Failed to export EYBL data from DuckDB: {e}", exc_info=True)
        return pd.DataFrame()


def export_players_from_duckdb(
    duckdb_conn,
    output_path: Path,
    source_type: Optional[str] = None,
    grad_year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Export player biographical data from DuckDB to Parquet.

    This can be used to supplement recruiting data or as a fallback
    when recruiting CSV is not available.

    Args:
        duckdb_conn: DuckDB connection object
        output_path: Output path for Parquet file
        source_type: Optional source filter (e.g., "eybl", "maxpreps")
        grad_year: Optional grad year filter

    Returns:
        DataFrame with player biographical data

    Schema:
        player_id, player_name, position, height_inches, weight_lbs,
        school_name, school_state, grad_year, source_type
    """
    try:
        logger.info("Exporting player data from DuckDB")

        query = """
            SELECT
                player_id,
                full_name as player_name,
                position,
                height_inches,
                weight_lbs,
                school_name,
                school_state as state,
                grad_year,
                source_type
            FROM players
            WHERE 1=1
        """

        if source_type:
            query += f" AND source_type = '{source_type}'"

        if grad_year:
            query += f" AND grad_year = {grad_year}"

        df = duckdb_conn.execute(query).df()

        if df.empty:
            logger.warning(
                "No player data found in DuckDB",
                filters={"source_type": source_type, "grad_year": grad_year},
            )
            return df

        logger.info(f"Retrieved {len(df)} player records from DuckDB")

        # Save to Parquet
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        logger.info(f"Player data exported to {output_path}")

        return df

    except Exception as e:
        logger.error(f"Failed to export player data from DuckDB: {e}", exc_info=True)
        return pd.DataFrame()


def create_mock_recruiting_csv(
    output_path: Path,
    grad_year: int,
    num_players: int = 100,
) -> pd.DataFrame:
    """
    Create a mock recruiting CSV file with realistic data for testing.

    This generates synthetic but realistic recruiting rankings data
    to test the pipeline when real recruiting data is not available.

    Args:
        output_path: Output path for CSV file
        grad_year: Graduation year for the cohort
        num_players: Number of players to generate

    Returns:
        DataFrame with mock recruiting data

    Schema:
        player_name, grad_year, position, height_inches, weight_lbs,
        stars, composite_rating, national_rank, state_rank, position_rank,
        state, committed_school, committed_conference
    """
    import numpy as np

    logger.info(f"Creating mock recruiting CSV for grad_year={grad_year}")

    # Realistic distributions
    positions = ["PG", "SG", "SF", "PF", "C"]
    states = [
        "CA", "TX", "FL", "NY", "GA", "NC", "OH", "PA", "IL", "MI",
        "VA", "NJ", "TN", "IN", "MD", "WA", "MA", "AZ", "MO", "WI",
    ]
    conferences = [
        "ACC", "Big Ten", "Big 12", "SEC", "Pac-12", "Big East",
        "American", "Mountain West", "Conference USA", "MAC",
    ]

    # Generate names (simple but varied)
    first_names = [
        "James", "Michael", "Robert", "John", "David", "William", "Richard",
        "Joseph", "Thomas", "Christopher", "Daniel", "Matthew", "Anthony",
        "Marcus", "Jaylen", "Tyrese", "Jalen", "Isaiah", "Jordan", "Cameron",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson",
        "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee",
    ]

    data = []
    for i in range(num_players):
        # Generate realistic stats based on rank
        national_rank = i + 1
        stars = (
            5 if national_rank <= 25
            else 4 if national_rank <= 100
            else 3 if national_rank <= 300
            else 2
        )
        composite_rating = max(70, 100 - (national_rank * 0.1))

        # Position-specific heights
        pos = np.random.choice(positions)
        if pos == "PG":
            height = np.random.randint(70, 76)
            weight = np.random.randint(160, 190)
        elif pos == "SG":
            height = np.random.randint(73, 78)
            weight = np.random.randint(175, 210)
        elif pos == "SF":
            height = np.random.randint(75, 80)
            weight = np.random.randint(190, 225)
        elif pos == "PF":
            height = np.random.randint(77, 82)
            weight = np.random.randint(210, 245)
        else:  # C
            height = np.random.randint(79, 85)
            weight = np.random.randint(225, 280)

        state = np.random.choice(states)
        state_rank = np.random.randint(1, 21)
        position_rank = np.random.randint(1, 41)

        # Top players more likely to commit to Power-6
        if stars >= 4:
            conference = np.random.choice(conferences[:6], p=[0.2, 0.2, 0.15, 0.2, 0.15, 0.1])
        else:
            conference = np.random.choice(conferences)

        # Some players uncommitted
        if np.random.random() > 0.7:
            committed_school = None
            committed_conference = None
        else:
            committed_school = f"{conference} University"
            committed_conference = conference

        player = {
            "player_name": f"{np.random.choice(first_names)} {np.random.choice(last_names)}",
            "grad_year": grad_year,
            "position": pos,
            "height_inches": height,
            "weight_lbs": weight,
            "stars": stars,
            "composite_rating": round(composite_rating, 2),
            "national_rank": national_rank,
            "state_rank": state_rank,
            "position_rank": position_rank,
            "state": state,
            "committed_school": committed_school,
            "committed_conference": committed_conference,
        }
        data.append(player)

    df = pd.DataFrame(data)

    # Save to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Mock recruiting CSV created at {output_path} ({len(df)} players)")

    return df


def create_mock_maxpreps_parquet(
    output_path: Path,
    grad_year: int,
    num_players: int = 500,
    recruiting_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Create a mock MaxPreps Parquet file with realistic HS stats for testing.

    If recruiting_df is provided, uses player names from recruiting data
    to enable proper joining.

    Args:
        output_path: Output path for Parquet file
        grad_year: Graduation year for the cohort
        num_players: Number of players to generate
        recruiting_df: Optional recruiting DataFrame to match names

    Returns:
        DataFrame with mock MaxPreps stats

    Schema:
        player_name, grad_year, state, team_name, games_played,
        pts_per_game, reb_per_game, ast_per_game, stl_per_game, blk_per_game,
        tov_per_game, fg_pct, three_pct, ft_pct,
        fga_per_game, three_att_per_game, fta_per_game
    """
    import numpy as np

    logger.info(f"Creating mock MaxPreps Parquet for grad_year={grad_year}")

    # If recruiting data provided, use those names (enables joining)
    if recruiting_df is not None and not recruiting_df.empty:
        player_names = recruiting_df["player_name"].tolist()
        states = recruiting_df["state"].tolist()
        num_players = len(player_names)
    else:
        # Generate random names
        first_names = [
            "James", "Michael", "Robert", "John", "David", "William",
            "Marcus", "Jaylen", "Tyrese", "Jalen", "Isaiah", "Jordan",
        ]
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
            "Davis", "Martinez", "Wilson", "Anderson", "Thomas", "Taylor",
        ]
        player_names = [
            f"{np.random.choice(first_names)} {np.random.choice(last_names)}"
            for _ in range(num_players)
        ]
        states = np.random.choice(
            ["CA", "TX", "FL", "NY", "GA", "NC", "OH", "PA", "IL", "MI"],
            size=num_players,
        )

    data = []
    for i, name in enumerate(player_names):
        # Generate realistic stats (correlated with talent level)
        # Higher-ranked players (lower index if from recruiting) have better stats
        talent_factor = 1.0 - (i / num_players) * 0.5  # Ranges from 1.0 to 0.5

        games_played = np.random.randint(15, 31)

        # Scoring
        pts_per_game = np.random.normal(15 * talent_factor, 5)
        pts_per_game = max(5, min(35, pts_per_game))

        # Rebounds
        reb_per_game = np.random.normal(6 * talent_factor, 2)
        reb_per_game = max(2, min(15, reb_per_game))

        # Assists
        ast_per_game = np.random.normal(3 * talent_factor, 1.5)
        ast_per_game = max(0.5, min(10, ast_per_game))

        # Defense
        stl_per_game = np.random.normal(1.5 * talent_factor, 0.8)
        stl_per_game = max(0.3, min(4, stl_per_game))

        blk_per_game = np.random.normal(1.0 * talent_factor, 0.7)
        blk_per_game = max(0.1, min(5, blk_per_game))

        # Turnovers
        tov_per_game = np.random.normal(2.5, 1)
        tov_per_game = max(0.5, min(6, tov_per_game))

        # Shooting percentages
        fg_pct = np.random.normal(45 + (talent_factor * 10), 7)
        fg_pct = max(30, min(70, fg_pct))

        three_pct = np.random.normal(32 + (talent_factor * 8), 8)
        three_pct = max(15, min(50, three_pct))

        ft_pct = np.random.normal(70 + (talent_factor * 10), 10)
        ft_pct = max(50, min(95, ft_pct))

        # Attempt stats (derived from makes and percentages)
        fga_per_game = pts_per_game / (fg_pct / 100) / 2  # Rough estimate
        three_att_per_game = fga_per_game * 0.3  # ~30% of shots are 3s
        fta_per_game = pts_per_game * 0.2  # Rough estimate

        player_data = {
            "player_name": name,
            "grad_year": grad_year,
            "state": states[i] if isinstance(states, list) else states,
            "team_name": f"{np.random.choice(['Central', 'North', 'South', 'East', 'West'])} High School",
            "games_played": games_played,
            "pts_per_game": round(pts_per_game, 1),
            "reb_per_game": round(reb_per_game, 1),
            "ast_per_game": round(ast_per_game, 1),
            "stl_per_game": round(stl_per_game, 1),
            "blk_per_game": round(blk_per_game, 1),
            "tov_per_game": round(tov_per_game, 1),
            "fg_pct": round(fg_pct, 1),
            "three_pct": round(three_pct, 1),
            "ft_pct": round(ft_pct, 1),
            "fga_per_game": round(fga_per_game, 1),
            "three_att_per_game": round(three_att_per_game, 1),
            "fta_per_game": round(fta_per_game, 1),
        }
        data.append(player_data)

    df = pd.DataFrame(data)

    # Save to Parquet
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info(f"Mock MaxPreps Parquet created at {output_path} ({len(df)} players)")

    return df
