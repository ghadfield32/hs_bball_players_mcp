# src/hs_forecasting/dataset_builder.py

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class HSForecastingConfig:
    """
    Configuration for building the high-school player-season dataset.

    You can extend this later (e.g., thresholds, feature toggles).
    """
    min_games_played: int = 10
    grad_year: Optional[int] = None


def normalize_name(name: str) -> str:
    """
    Simple deterministic name normalizer:
    - Lowercase
    - Remove non-letters
    - Collapse whitespace

    This is intentionally simple so it's easy to reason about and replicate
    across repos (MCP, Neo4j, etc.).
    """
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[^a-z\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def make_player_uid(normalized_name: str, grad_year: Optional[int], state: str) -> str:
    """
    Create a stable UID from normalized_name + grad_year + state.
    If grad_year is missing, we still form a UID from available pieces.
    """
    parts = [normalized_name or "", str(grad_year or ""), state or ""]
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def standardize_maxpreps_stats(
    maxpreps_df: pd.DataFrame,
    grad_year: Optional[int] = None,
    min_games_played: int = 10,
) -> pd.DataFrame:
    """
    Standardize MaxPreps player-season stats into a canonical schema.

    EXPECTED INPUT (adjust column names to your actual importer):
      - player_name
      - grad_year
      - state
      - team_name
      - games_played
      - pts_per_game
      - reb_per_game
      - ast_per_game
      - stl_per_game
      - blk_per_game
      - tov_per_game
      - fg_pct
      - three_pct
      - ft_pct
      - fga_per_game
      - three_att_per_game
      - fta_per_game

    TODO: if your importer uses different names, change the `rename` mapping below.
    """
    if maxpreps_df.empty:
        logger.warning("MaxPreps dataframe is empty; returning empty standardized frame.")
        return maxpreps_df.copy()

    df = maxpreps_df.copy()

    rename_map = {
        # IDENTIFIERS
        "player_name": "full_name",
        "team_name": "hs_team",
        "state": "state",
        "grad_year": "grad_year",
        # CORE STATS
        "games_played": "gp",
        "pts_per_game": "pts_per_g",
        "reb_per_game": "reb_per_g",
        "ast_per_game": "ast_per_g",
        "stl_per_game": "stl_per_g",
        "blk_per_game": "blk_per_g",
        "tov_per_game": "tov_per_g",
        "fg_pct": "fg_pct",
        "three_pct": "three_pct",
        "ft_pct": "ft_pct",
        "fga_per_game": "fga_per_g",
        "three_att_per_game": "three_att_per_g",
        "fta_per_game": "fta_per_g",
    }
    # Only rename columns that actually exist
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Filter by grad_year if requested
    if grad_year is not None and "grad_year" in df.columns:
        before = len(df)
        df = df[df["grad_year"] == grad_year].copy()
        logger.info("Filtered MaxPreps to grad_year=%s: %d → %d rows", grad_year, before, len(df))

    # Filter by games played
    if "gp" in df.columns:
        before = len(df)
        df = df[df["gp"] >= min_games_played].copy()
        logger.info(
            "Filtered MaxPreps by min_games_played=%d: %d → %d rows",
            min_games_played,
            before,
            len(df),
        )

    # Normalize names and fill basics
    df["full_name"] = df.get("full_name", "").fillna("")
    df["normalized_name"] = df["full_name"].map(normalize_name)
    df["state"] = df.get("state", "").fillna("")
    df["grad_year"] = df.get("grad_year", grad_year).astype("Int64")

    df["player_uid"] = df.apply(
        lambda r: make_player_uid(
            r["normalized_name"],
            int(r["grad_year"]) if pd.notnull(r["grad_year"]) else None,
            r["state"],
        ),
        axis=1,
    )

    return df


def standardize_recruiting(recruiting_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize recruiting CSV into a canonical schema.

    EXPECTED INPUT (adjust column names to your CSV schema):
      - player_name
      - grad_year
      - position
      - height_inches
      - weight_lbs
      - stars
      - composite_rating
      - national_rank
      - state_rank
      - position_rank
      - state
      - committed_school
      - committed_conference
    """
    if recruiting_df.empty:
        logger.warning("Recruiting dataframe is empty; returning empty standardized frame.")
        return recruiting_df.copy()

    df = recruiting_df.copy()

    rename_map = {
        "player_name": "full_name",
        "grad_year": "grad_year",
        "pos": "position",
        "position": "position",
        "height_in": "height_inches",
        "height_inches": "height_inches",
        "weight_lbs": "weight_lbs",
        "stars": "stars",
        "rating": "composite_rating",
        "composite_rating": "composite_rating",
        "national_rank": "national_rank",
        "state_rank": "state_rank",
        "position_rank": "position_rank",
        "state": "state",
        "school": "committed_school",
        "committed_school": "committed_school",
        "conference": "committed_conference",
        "committed_conference": "committed_conference",
    }
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    df["full_name"] = df.get("full_name", "").fillna("")
    df["normalized_name"] = df["full_name"].map(normalize_name)
    df["state"] = df.get("state", "").fillna("")
    if "grad_year" in df.columns:
        df["grad_year"] = df["grad_year"].astype("Int64")

    # Basic cleaning
    for col in ["stars", "composite_rating", "national_rank", "state_rank", "position_rank"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Simple Power-6 indicator if committed_conference exists
    power6 = {"acc", "big ten", "big 12", "sec", "pac-12", "pac 12", "big east"}
    if "committed_conference" in df.columns:
        df["committed_conference_norm"] = (
            df["committed_conference"].fillna("").str.lower().str.strip()
        )
        df["has_power6_offer"] = df["committed_conference_norm"].isin(power6)
    else:
        df["has_power6_offer"] = False

    return df


def standardize_eybl_stats(eybl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize EYBL stats into a canonical schema.

    UPDATED (Phase 14): Now handles BOTH schema variants:
      1. Direct adapter schema: pts_per_game, reb_per_game, ast_per_game
      2. DuckDB export schema: points_per_game, rebounds_per_game, assists_per_game

    EXPECTED INPUT (multiple naming conventions supported):
      - player_name (required)
      - season (optional, or grad_year proxy)
      - gp OR games_played (required)
      - pts_per_game OR points_per_game (optional)
      - reb_per_game OR rebounds_per_game (optional)
      - ast_per_game OR assists_per_game (optional)
      - stl_per_game OR steals_per_game (optional)
      - blk_per_game OR blocks_per_game (optional)
      - three_pct OR three_point_percentage (optional)
    """
    if eybl_df.empty:
        logger.info("EYBL dataframe is empty; returning empty standardized frame.")
        return eybl_df.copy()

    df = eybl_df.copy()

    # Expanded rename map to handle BOTH schemas
    rename_map = {
        # Player name variants
        "player_name": "full_name",
        "full_name": "full_name",  # Already correct

        # Games played variants
        "gp": "eybl_gp",
        "games_played": "eybl_gp",

        # Points variants (SHORT form or LONG form)
        "pts_per_game": "eybl_pts_per_g",
        "points_per_game": "eybl_pts_per_g",  # DuckDB schema

        # Rebounds variants
        "reb_per_game": "eybl_reb_per_g",
        "rebounds_per_game": "eybl_reb_per_g",  # DuckDB schema

        # Assists variants
        "ast_per_game": "eybl_ast_per_g",
        "assists_per_game": "eybl_ast_per_g",  # DuckDB schema

        # Steals variants
        "stl_per_game": "eybl_stl_per_g",
        "steals_per_game": "eybl_stl_per_g",  # DuckDB schema

        # Blocks variants
        "blk_per_game": "eybl_blk_per_g",
        "blocks_per_game": "eybl_blk_per_g",  # DuckDB schema

        # Three-point percentage variants
        "three_pct": "eybl_three_pct",
        "three_point_percentage": "eybl_three_pct",  # DuckDB schema
    }

    # Only rename columns that actually exist in the DataFrame
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Ensure full_name exists
    if "full_name" not in df.columns:
        logger.warning("EYBL data missing 'player_name' or 'full_name' column")
        df["full_name"] = ""

    df["full_name"] = df["full_name"].fillna("")
    df["normalized_name"] = df["full_name"].map(normalize_name)

    # If you have a direct grad_year in EYBL, add it here later.
    logger.info(
        f"Standardized EYBL stats: {len(df)} rows, "
        f"columns: {list(df.columns)}"
    )

    return df


def build_hs_player_season_dataset(
    maxpreps_df: pd.DataFrame,
    recruiting_df: pd.DataFrame,
    eybl_df: Optional[pd.DataFrame] = None,
    config: Optional[HSForecastingConfig] = None,
) -> pd.DataFrame:
    """
    Core function: build a unified HS player-season dataset suitable for
    college-success forecasting.

    It:
      - Standardizes each source.
      - Filters by grad_year and min_games_played (via config).
      - Merges recruiting + MaxPreps on (normalized_name, grad_year).
      - Left-joins EYBL on normalized_name.
      - Adds a stable player_uid.
      - Computes a few simple derived features.
    """
    if config is None:
        config = HSForecastingConfig()

    logger.info("Building HS player-season dataset with config=%s", config)

    maxpreps_std = standardize_maxpreps_stats(
        maxpreps_df,
        grad_year=config.grad_year,
        min_games_played=config.min_games_played,
    )
    recruiting_std = standardize_recruiting(recruiting_df)

    if config.grad_year is not None and "grad_year" in recruiting_std.columns:
        before = len(recruiting_std)
        recruiting_std = recruiting_std[recruiting_std["grad_year"] == config.grad_year].copy()
        logger.info(
            "Filtered recruiting to grad_year=%s: %d → %d rows",
            config.grad_year,
            before,
            len(recruiting_std),
        )

    # Merge recruiting + MaxPreps
    merge_keys = ["normalized_name"]
    if "grad_year" in maxpreps_std.columns and "grad_year" in recruiting_std.columns:
        merge_keys.append("grad_year")

    logger.info("Merging recruiting and MaxPreps on keys=%s", merge_keys)
    hs_df = pd.merge(
        recruiting_std,
        maxpreps_std,
        on=merge_keys,
        how="outer",
        suffixes=("_recruit", "_hs"),
        validate="m:m",
    )

    # Combine / coalesce basic identity fields
    hs_df["full_name"] = hs_df.get("full_name_recruit", "").fillna("")
    mask_missing_name = hs_df["full_name"] == ""
    if "full_name_hs" in hs_df.columns:
        hs_df.loc[mask_missing_name, "full_name"] = hs_df.loc[mask_missing_name, "full_name_hs"]
    hs_df["normalized_name"] = hs_df["full_name"].map(normalize_name)

    if "state_recruit" in hs_df.columns or "state_hs" in hs_df.columns:
        hs_df["state"] = hs_df.get("state_recruit", "").fillna("")
        mask_missing_state = hs_df["state"] == ""
        if "state_hs" in hs_df.columns:
            hs_df.loc[mask_missing_state, "state"] = hs_df.loc[mask_missing_state, "state_hs"]
    else:
        hs_df["state"] = ""

    if "grad_year" in hs_df.columns:
        hs_df["grad_year"] = hs_df["grad_year"].astype("Int64")
    else:
        hs_df["grad_year"] = config.grad_year

    # Player UID – we reapply to guarantee consistency post-merge
    hs_df["player_uid"] = hs_df.apply(
        lambda r: make_player_uid(
            r["normalized_name"],
            int(r["grad_year"]) if pd.notnull(r["grad_year"]) else None,
            r["state"],
        ),
        axis=1,
    )

    # Attach EYBL if provided
    if eybl_df is not None and not eybl_df.empty:
        eybl_std = standardize_eybl_stats(eybl_df)
        logger.info("Merging EYBL stats on normalized_name")
        hs_df = pd.merge(
            hs_df,
            eybl_std[
                [
                    "normalized_name",
                    "eybl_gp",
                    "eybl_pts_per_g",
                    "eybl_reb_per_g",
                    "eybl_ast_per_g",
                    "eybl_three_pct",
                ]
            ].drop_duplicates("normalized_name"),
            on="normalized_name",
            how="left",
        )
        hs_df["played_eybl"] = hs_df["eybl_gp"].fillna(0) > 0
    else:
        hs_df["played_eybl"] = False

    # Simple derived features
    if "pts_per_g" in hs_df.columns and "gp" in hs_df.columns:
        hs_df["total_pts_season"] = hs_df["pts_per_g"].fillna(0) * hs_df["gp"].fillna(0)

    if "three_att_per_g" in hs_df.columns and "fga_per_g" in hs_df.columns:
        with pd.option_context("mode.use_inf_as_na", True):
            hs_df["three_rate"] = hs_df["three_att_per_g"] / hs_df["fga_per_g"]
    else:
        hs_df["three_rate"] = pd.NA

    # Keep only columns we actually need for modeling (you can extend this)
    cols_to_keep = [
        "player_uid",
        "full_name",
        "normalized_name",
        "grad_year",
        "state",
        # Recruiting
        "position",
        "height_inches",
        "weight_lbs",
        "stars",
        "composite_rating",
        "national_rank",
        "state_rank",
        "position_rank",
        "committed_school",
        "committed_conference",
        "has_power6_offer",
        # HS stats
        "hs_team" if "hs_team" in hs_df.columns else None,
        "gp",
        "pts_per_g",
        "reb_per_g",
        "ast_per_g",
        "stl_per_g",
        "blk_per_g",
        "tov_per_g",
        "fg_pct",
        "three_pct",
        "ft_pct",
        "fga_per_g",
        "three_att_per_g",
        "fta_per_g",
        "three_rate",
        "total_pts_season",
        # EYBL
        "played_eybl",
        "eybl_gp",
        "eybl_pts_per_g",
        "eybl_reb_per_g",
        "eybl_ast_per_g",
        "eybl_three_pct",
    ]

    cols_to_keep = [c for c in cols_to_keep if c in hs_df.columns]
    hs_df = hs_df[cols_to_keep].copy()

    logger.info("HS player-season dataset built: %d rows, %d columns", len(hs_df), len(hs_df.columns))
    return hs_df
