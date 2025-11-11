# Unified Dataset Layer

The unified dataset layer provides a **canonical, category-rich schema** for basketball data from all sources. It enables cross-source analytics, ML model training, and consistent reporting.

## Overview

**Problem**: Each data source (EYBL, FHSAA, UAA, etc.) has its own schema, naming conventions, and data quality. This makes it hard to:
- Compare players across circuits
- Track players who appear in multiple sources
- Build ML models on consistent features
- Run analytics queries across all data

**Solution**: The unified layer normalizes all sources into **7 canonical tables** with:
- Deterministic unique identifiers (UIDs)
- Categorical encodings for ML
- Lineage tracking (source_url, fetched_at)
- Consistent naming (circuit, level, gender, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Raw Source Data (per-source DataFrames)                    │
│  - eybl: {teams, games, boxes}                              │
│  - fhsaa: {games, events}                                   │
│  - uaa: {teams, games, boxes}                               │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  build_unified_dataset()                                     │
│  - Normalize gender/level/circuit                           │
│  - Generate deterministic UIDs                              │
│  - Map country/state metadata                               │
│  - Deduplicate on UIDs                                      │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Canonical Tables (dims + facts)                            │
│  - dim_source (70+ sources)                                 │
│  - dim_competition (leagues/tournaments)                    │
│  - dim_team (schools/clubs/AAU)                             │
│  - fact_game (scores, dates, venues)                        │
│  - fact_box (player stats per game)                         │
│  - fact_roster (team rosters)                               │
│  - fact_event (camps, brackets, showcases)                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  DuckDB + Parquet                                           │
│  - Fast SQL analytics (10-100x faster than Pandas)         │
│  - Parquet exports for ML pipelines                         │
│  - Analytics views (leaderboards, rollups, etc.)           │
└─────────────────────────────────────────────────────────────┘
```

## Schema

### Dimensions (slowly changing)

**dim_source**: Data source metadata
- `source_key`: Source identifier (e.g., "eybl", "fhsaa")
- `source_type`: Type (CIRCUIT, ASSOCIATION, PLATFORM, etc.)
- `circuit`: Canonical circuit name (EYBL, 3SSB, UAA, GHSA, etc.)
- `country`, `state`, `region`: Geographic metadata

**dim_competition**: Leagues/tournaments/seasons
- `competition_uid`: Unique ID (format: `{CIRCUIT}:{season}:{name}`)
- `circuit`, `level`, `gender`, `age_group`: Categorical features
- `season`: Season identifier (e.g., "2024", "2024-25")
- `country`, `state`: Geographic metadata

**dim_team**: Schools/clubs/AAU teams
- `team_uid`: Unique ID (format: `{source}:{season}:{team_name}`)
- `team_name`, `school_uid`, `org_type`: Team metadata
- `country`, `state`, `city`: Geographic metadata

**dim_player** (future): Unique players across sources
- `player_uid`: From identity resolution (name + school + grad_year)
- `full_name`, `birth_year`, `height_cm`, `position_std`: Player attributes

### Facts (event-driven)

**fact_game**: Game results
- `game_uid`: Unique ID (format: `{source}:{season}:{date}:{home}|{away}`)
- `competition_uid`, `home_team_uid`, `away_team_uid`: Foreign keys
- `date_utc`, `venue`, `result`: Game metadata
- `source_id`, `source_url`, `fetched_at`: Lineage

**fact_box**: Box score statistics
- `game_uid`, `player_uid`, `team_uid`: Foreign keys
- `pts`, `reb`, `ast`, `stl`, `blk`, etc.: Standard stats
- `fgm`, `fga`, `fg3m`, `fg3a`, `ftm`, `fta`: Shooting stats
- `minutes`, `plus_minus`, `starters_flag`: Game context
- `source_id`: Lineage

**fact_roster**: Team rosters
- `season`, `competition_uid`, `team_uid`, `player_uid`: Foreign keys
- `jersey`, `role`: Roster metadata

**fact_event**: Non-game events (brackets, camps, showcases)
- `season`, `competition_uid`: Foreign keys
- `event_type`, `label`, `date_utc`, `meta`: Event metadata

## Usage

### 1. Build Unified Dataset (Python)

```python
import pandas as pd
from src.unified import build_unified_dataset

# Prepare per-source DataFrames
pulled = {
    "eybl": {
        "teams": eybl_teams_df,
        "games": eybl_games_df,
        "boxes": eybl_boxes_df,
    },
    "fhsaa": {
        "games": fhsaa_games_df,
        "events": fhsaa_events_df,
    },
}

# Build unified dataset
tables = build_unified_dataset(
    pulled,
    country_by_source={"eybl": "US", "fhsaa": "US"},
    state_by_source={"fhsaa": "FL"},
)

# Access canonical tables
print(tables["dim_source"])       # Source metadata
print(tables["dim_competition"])  # Competitions
print(tables["dim_team"])         # Teams
print(tables["fact_game"])        # Games
print(tables["fact_box"])         # Box scores
```

### 2. Materialize to DuckDB + Parquet (CLI)

```bash
# Materialize all active sources
python scripts/materialize_unified.py

# Materialize specific sources
python scripts/materialize_unified.py --sources eybl,uaa,fhsaa

# Materialize specific season
python scripts/materialize_unified.py --season 2024
```

Output:
```
data/unified/
├── unified.duckdb           # DuckDB database
├── dim_source.parquet       # Source dimension
├── dim_competition.parquet  # Competition dimension
├── dim_team.parquet         # Team dimension
├── fact_game.parquet        # Game facts
├── fact_box.parquet         # Box score facts
├── fact_roster.parquet      # Roster facts
└── fact_event.parquet       # Event facts
```

### 3. Analytics Queries (SQL)

```sql
-- Connect to unified database
duckdb data/unified/unified.duckdb

-- Load analytics views
.read src/unified/analytics.sql

-- Cross-source player tracking
SELECT * FROM mart_player_season
WHERE player_uid = 'john_smith:lincoln_hs:2025';

-- Circuit comparison (EYBL vs 3SSB vs UAA)
SELECT circuit, level, gender, AVG(ppg), AVG(rpg), AVG(apg)
FROM mart_player_season
GROUP BY circuit, level, gender;

-- Top scorers across all circuits
SELECT * FROM vw_top_scorers
WHERE level = 'HS' AND gender = 'M'
LIMIT 20;

-- State coverage analysis
SELECT * FROM vw_state_coverage
ORDER BY num_games DESC;

-- Export for ML pipeline
COPY (SELECT * FROM vw_ml_features)
TO 'data/exports/ml_features.parquet' (FORMAT PARQUET);
```

## Categorical Encoding

All categorical columns are normalized to canonical values:

**Gender**: `M` (male) or `F` (female)
- Handles: "boys", "girls", "men", "women", "m", "f"

**Level**: `HS`, `PREP`, `U14`, `U15`, `U16`, `U17`, `U18`, `U21`
- Inferred from source type and age_group

**Circuit**: Canonical names (70+ sources)
- Examples: `EYBL`, `3SSB`, `UAA`, `GHSA`, `FHSAA`, `NBBL`, etc.

**Source Type**: 6 categories
- `CIRCUIT`: National grassroots circuits (EYBL, 3SSB, UAA)
- `ASSOCIATION`: State athletic associations (FHSAA, GHSA, etc.)
- `PLATFORM`: Multi-state platforms (SBLive, Bound, RankOne)
- `PREP`: Prep school leagues (NEPSAC, NPA)
- `LEAGUE`: European/global youth leagues (NBBL, FEB, MKL)
- `EVENT`: Event aggregators (Exposure, TournyMachine)

For ML models, use `dim_categorical_codes` table to map strings to integer codes:

```sql
SELECT kind, val, code FROM dim_categorical_codes;
-- circuit, EYBL, 1
-- circuit, 3SSB, 2
-- circuit, UAA, 3
-- level, HS, 1
-- level, PREP, 2
-- level, U17, 3
-- gender, M, 1
-- gender, F, 2
```

## Key Generation

All UIDs are **deterministic** (same inputs → same UID):

**competition_uid**: `{CIRCUIT}:{season}:{name}`
```python
competition_uid("eybl", "Nike EYBL", "2024")
# → "EYBL:2024:nike_eybl"
```

**team_uid**: `{source}:{season}:{team_name}`
```python
team_uid("eybl", "Team Takeover", "2024")
# → "eybl:2024:team_takeover"
```

**game_uid**: `{source}:{season}:{date}:{home}|{away}`
```python
game_uid("eybl", "2024", "Team Takeover", "Expressions Elite", "2024-04-15")
# → "eybl:2024:2024-04-15:team_takeover|expressions_elite"
```

**player_uid**: `{name}:{school}:{grad_year}` (from identity resolution)
```python
player_uid_from_identity("John Smith", "Lincoln HS", 2025)
# → "john_smith:lincoln_hs:2025"
```

Benefits:
- Idempotent backfills (re-run same season → same UIDs)
- Cross-source joins (same player appears in multiple sources)
- No auto-increment IDs (deterministic, reproducible)

## Benefits

✅ **Cross-Source Analytics**: Query players/teams across all sources
✅ **ML-Ready**: Categorical encodings, feature matrices, consistent schema
✅ **Fast Queries**: DuckDB 10-100x faster than Pandas for analytics
✅ **Lineage Tracking**: Know exactly where each data point came from
✅ **Idempotent**: Re-run backfills without creating duplicates
✅ **Scalable**: Columnar storage (Parquet) handles millions of rows
✅ **Audit Trail**: source_url + fetched_at for every fact

## Examples

See `src/unified/analytics.sql` for 10+ example queries:
- Player-season rollups with categorical breakdowns
- Cross-source player tracking
- Circuit performance comparison
- State coverage analysis
- Data quality metrics
- ML feature matrix exports

## Next Steps

1. **Add dim_player**: Build from identity resolution + aggregated stats
2. **Historical Backfill**: CLI tool for multi-season backfills
3. **Auto-Export**: Trigger Parquet exports on DuckDB updates
4. **ML Models**: Player performance prediction, recruitment scoring
5. **Event Adapters**: Exposure Events, TournyMachine for AAU tournaments
