"""
Unified Dataset Builder

Merges per-source DataFrames into canonical dimensions and facts.
Handles normalization, deduplication, and lineage tracking.
"""

from datetime import datetime
from typing import Any, Dict, Iterable

import pandas as pd

from .categories import map_source_meta, normalize_gender, normalize_level
from .mapper import (
    competition_uid,
    extract_date_from_datetime,
    game_uid,
    infer_season_from_date,
    team_uid,
)


def build_unified_dataset(
    pulled: Dict[str, Dict[str, pd.DataFrame]],
    *,
    country_by_source: Dict[str, str],
    state_by_source: Dict[str, str] | None = None,
    region_by_source: Dict[str, str] | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    Merge per-source DataFrames into canonical dims/facts.

    Args:
        pulled: Dict mapping source_key -> {table_name: DataFrame}
                Expected tables: "teams", "games", "boxes", "events", "rosters"
        country_by_source: Dict mapping source_key -> ISO-2 country code
        state_by_source: Dict mapping source_key -> USPS state code (optional)
        region_by_source: Dict mapping source_key -> region name (optional)

    Returns:
        Dict with canonical tables:
        - dim_source: Source metadata
        - dim_competition: Competitions/leagues/tournaments
        - dim_team: Teams
        - fact_game: Games with scores
        - fact_box: Box score statistics
        - fact_roster: Team rosters
        - fact_event: Non-game events

    Example:
        >>> pulled = {
        ...     "eybl": {"teams": teams_df, "games": games_df, "boxes": boxes_df},
        ...     "fhsaa": {"games": games_df, "events": events_df}
        ... }
        >>> tables = build_unified_dataset(
        ...     pulled,
        ...     country_by_source={"eybl": "US", "fhsaa": "US"},
        ...     state_by_source={"fhsaa": "FL"}
        ... )
    """
    state_by_source = state_by_source or {}
    region_by_source = region_by_source or {}

    dims_source, dims_comp, dims_team = [], [], []
    fact_game, fact_box, fact_roster, fact_event = [], [], [], []

    for skey, tables in pulled.items():
        country = country_by_source.get(skey, "US")
        state = state_by_source.get(skey)
        region = region_by_source.get(skey, "US" if country == "US" else "GLOBAL")

        circuit, stype = map_source_meta(skey)

        # Extract tables
        teams = tables.get("teams", pd.DataFrame())
        games = tables.get("games", pd.DataFrame())
        boxes = tables.get("boxes", pd.DataFrame())
        events = tables.get("events", pd.DataFrame())
        rosters = tables.get("rosters", pd.DataFrame())

        # ===== DIM: TEAMS =====
        if not teams.empty:
            tdf = _build_teams_dim(teams, skey, country, state)
            dims_team.append(tdf)

        # ===== FACT: GAMES =====
        if not games.empty:
            gdf = _build_games_fact(games, skey, circuit)
            fact_game.append(gdf)

            # ===== DIM: COMPETITIONS (from games) =====
            cdf = _build_competitions_dim(games, skey, circuit, country, state)
            dims_comp.append(cdf)

        # ===== FACT: BOXES =====
        if not boxes.empty:
            bdf = _build_boxes_fact(boxes, skey)
            fact_box.append(bdf)

        # ===== FACT: ROSTERS =====
        if not rosters.empty:
            rdf = _build_rosters_fact(rosters, skey, circuit)
            fact_roster.append(rdf)

        # ===== FACT: EVENTS =====
        if not events.empty:
            edf = _build_events_fact(events, skey, circuit)
            fact_event.append(edf)

        # ===== DIM: SOURCE (once per source) =====
        dims_source.append(
            pd.DataFrame.from_records(
                [
                    {
                        "source_id": skey,
                        "source_key": skey,
                        "source_type": stype,
                        "operator": circuit,
                        "region": region,
                        "country": country,
                        "state": state,
                        "notes": None,
                    }
                ]
            )
        )

    # Concatenate safely (handle empty lists)
    def cat(parts):
        if not parts:
            return pd.DataFrame()
        valid = [p for p in parts if len(p) > 0]
        return pd.concat(valid, ignore_index=True) if valid else pd.DataFrame()

    return {
        "dim_source": cat(dims_source).drop_duplicates("source_id"),
        "dim_competition": cat(dims_comp).drop_duplicates("competition_uid"),
        "dim_team": cat(dims_team).drop_duplicates("team_uid"),
        "fact_game": cat(fact_game).drop_duplicates("game_uid"),
        "fact_box": cat(fact_box),
        "fact_roster": cat(fact_roster),
        "fact_event": cat(fact_event),
    }


def _build_teams_dim(
    teams: pd.DataFrame, skey: str, country: str, state: str | None
) -> pd.DataFrame:
    """Build dim_team from teams DataFrame."""
    season_col = teams.get("season", pd.Series(["2024"] * len(teams)))

    return pd.DataFrame(
        {
            "team_uid": teams.apply(
                lambda r: team_uid(
                    skey,
                    r.get("team_name") or r.get("name", "unknown"),
                    r.get("season", "2024"),
                ),
                axis=1,
            ),
            "team_name": teams.get("team_name", teams.get("name", "Unknown")),
            "school_uid": teams.get("school_uid"),
            "org_type": teams.get("org_type", "SCHOOL"),
            "country": country,
            "state": teams.get("state", state),
            "city": teams.get("city"),
        }
    )


def _build_games_fact(
    games: pd.DataFrame, skey: str, circuit: str
) -> pd.DataFrame:
    """Build fact_game from games DataFrame."""
    # Normalize date column
    date_col = games.get("date_utc", games.get("date", pd.Series([""] * len(games))))
    date_col = date_col.apply(extract_date_from_datetime)

    # Infer season if not present
    if "season" not in games or games["season"].isnull().all():
        season_col = date_col.apply(infer_season_from_date)
    else:
        season_col = games["season"]

    return pd.DataFrame(
        {
            "game_uid": games.apply(
                lambda r: game_uid(
                    skey,
                    r.get("season", infer_season_from_date(r.get("date_utc", r.get("date", "")))),
                    r.get("home_team", "home"),
                    r.get("away_team", "away"),
                    extract_date_from_datetime(r.get("date_utc", r.get("date", ""))),
                ),
                axis=1,
            ),
            "competition_uid": games.apply(
                lambda r: competition_uid(
                    skey,
                    r.get("competition_name", circuit),
                    r.get("season", infer_season_from_date(r.get("date_utc", r.get("date", "")))),
                ),
                axis=1,
            ),
            "season": season_col,
            "date_utc": games.get("date_utc", games.get("date")),
            "venue": games.get("venue"),
            "home_team_uid": games.apply(
                lambda r: team_uid(
                    skey,
                    r.get("home_team", "home"),
                    r.get("season", infer_season_from_date(r.get("date_utc", r.get("date", "")))),
                ),
                axis=1,
            ),
            "away_team_uid": games.apply(
                lambda r: team_uid(
                    skey,
                    r.get("away_team", "away"),
                    r.get("season", infer_season_from_date(r.get("date_utc", r.get("date", "")))),
                ),
                axis=1,
            ),
            "result": games.get("result"),
            "source_id": skey,
            "source_url": games.get("source_url"),
            "fetched_at": games.get("fetched_at", datetime.utcnow().isoformat()),
        }
    )


def _build_competitions_dim(
    games: pd.DataFrame, skey: str, circuit: str, country: str, state: str | None
) -> pd.DataFrame:
    """Build dim_competition from games DataFrame."""
    # Infer season if not present
    if "season" not in games or games["season"].isnull().all():
        date_col = games.get("date_utc", games.get("date", pd.Series([""] * len(games))))
        date_col = date_col.apply(extract_date_from_datetime)
        season_col = date_col.apply(infer_season_from_date)
    else:
        season_col = games["season"]

    cdf = pd.DataFrame(
        {
            "competition_uid": games.apply(
                lambda r: competition_uid(
                    skey,
                    r.get("competition_name", circuit),
                    r.get("season", infer_season_from_date(r.get("date_utc", r.get("date", "")))),
                ),
                axis=1,
            ),
            "season": season_col,
        }
    ).drop_duplicates()

    cdf["name"] = circuit
    cdf["circuit"] = circuit
    cdf["level"] = normalize_level(
        skey, games.get("age_group").iloc[0] if "age_group" in games else None
    )
    cdf["gender"] = normalize_gender(
        games.get("gender").iloc[0] if "gender" in games else None
    )
    cdf["age_group"] = games.get("age_group").iloc[0] if "age_group" in games else None
    cdf["country"] = country
    cdf["state"] = state

    return cdf


def _build_boxes_fact(boxes: pd.DataFrame, skey: str) -> pd.DataFrame:
    """Build fact_box from boxes DataFrame."""
    # Ensure we have required columns
    required = ["game_uid", "player_uid", "team_uid"]
    for col in required:
        if col not in boxes:
            boxes[col] = None

    return pd.DataFrame(
        {
            "game_uid": boxes.get("game_uid"),
            "player_uid": boxes.get("player_uid"),
            "team_uid": boxes.get("team_uid"),
            "minutes": boxes.get("minutes"),
            "pts": boxes.get("pts", boxes.get("points")),
            "fgm": boxes.get("fgm"),
            "fga": boxes.get("fga"),
            "fg3m": boxes.get("fg3m"),
            "fg3a": boxes.get("fg3a"),
            "ftm": boxes.get("ftm"),
            "fta": boxes.get("fta"),
            "oreb": boxes.get("oreb"),
            "dreb": boxes.get("dreb"),
            "reb": boxes.get("reb", boxes.get("rebounds")),
            "ast": boxes.get("ast", boxes.get("assists")),
            "stl": boxes.get("stl", boxes.get("steals")),
            "blk": boxes.get("blk", boxes.get("blocks")),
            "tov": boxes.get("tov", boxes.get("turnovers")),
            "pf": boxes.get("pf", boxes.get("fouls")),
            "plus_minus": boxes.get("plus_minus"),
            "starters_flag": boxes.get("starters_flag", boxes.get("starter")),
            "source_id": skey,
        }
    )


def _build_rosters_fact(
    rosters: pd.DataFrame, skey: str, circuit: str
) -> pd.DataFrame:
    """Build fact_roster from rosters DataFrame."""
    return pd.DataFrame(
        {
            "season": rosters.get("season", "2024"),
            "competition_uid": rosters.apply(
                lambda r: competition_uid(
                    skey, r.get("competition_name", circuit), r.get("season", "2024")
                ),
                axis=1,
            ),
            "team_uid": rosters.apply(
                lambda r: team_uid(skey, r.get("team_name", "unknown"), r.get("season", "2024")),
                axis=1,
            ),
            "player_uid": rosters.get("player_uid"),
            "jersey": rosters.get("jersey"),
            "role": rosters.get("role"),
            "source_id": skey,
        }
    )


def _build_events_fact(events: pd.DataFrame, skey: str, circuit: str) -> pd.DataFrame:
    """Build fact_event from events DataFrame."""
    return pd.DataFrame(
        {
            "season": events.get("season", "2024"),
            "competition_uid": events.apply(
                lambda r: competition_uid(
                    skey, r.get("competition_name", circuit), r.get("season", "2024")
                ),
                axis=1,
            ),
            "event_type": events.get("event_type", "EVENT"),
            "label": events.get("label", events.get("name", "Unknown Event")),
            "date_utc": events.get("date_utc", events.get("date")),
            "meta": events.get("meta"),
            "source_id": skey,
        }
    )
