# QUICKSTART: Push the Red Button 🔴

**Status**: Ready to produce first parquet files ✅
**Time to First Data**: 1-2 hours (including 30 min manual test case extraction)

---

## Overview

You've built a complete HS player-season data pipeline:

```
Config (YAML) → Adapters → Validation → Backfill → Parquet → DuckDB → QA
```

**This guide gets you from zero to first production parquet files.**

---

## Prerequisites

### 1. Install Dependencies

```bash
# Install Python packages
pip install -e .

# Install Playwright browsers (required for EYBL, SBLive)
playwright install chromium --with-deps
```

### 2. Verify Setup

```bash
# Test imports
python -c "import pandas, pyarrow, duckdb, playwright; print('✅ All dependencies OK')"

# Check scripts are executable
chmod +x scripts/run_full_hs_pipeline.sh
```

---

## Phase 1: EYBL Green (30-50 minutes)

### Step 1: Extract Real Player Names (15-30 min, MANUAL)

**Why**: `config/datasource_test_cases.yaml` has placeholder values. We need 3 real EYBL player names.

**How**:

1. Visit https://nikeeyb.com/cumulative-season-stats
2. Select **2024 season** from dropdown
3. Pick **3 players** with complete stats (10+ games, 5+ PPG)
4. Copy their names, teams, and stats

**Example**:
```
Player: "John Smith"
Team: "Las Vegas Prospects"
Games: 15, PPG: 18.5, RPG: 6.2
```

### Step 2: Update Test Cases

Edit `config/datasource_test_cases.yaml`:

```yaml
eybl:
  - player_name: "John Smith"  # ← Real name from nikeeyb.com
    season: "2024"
    team_hint: "Las Vegas Prospects"
    expected_min_games: 10
    expected_min_ppg: 5.0
    expected_max_ppg: 30.0
    notes: "Top scorer from 2024 session"

  - player_name: "Jane Doe"  # ← Second real player
    season: "2024"
    team_hint: "Team Final"
    expected_min_games: 10
    expected_min_ppg: 5.0
    expected_max_ppg: 30.0

  - player_name: "Bob Johnson"  # ← Third real player
    season: "2024"
    team_hint: "Expressions Elite"
    expected_min_games: 10
    expected_min_ppg: 5.0
    expected_max_ppg: 30.0
```

### Step 3: Run Validation

```bash
python scripts/validate_datasource_stats.py --source eybl --verbose
```

**Expected Output**:
```
✅ Test case 1: John Smith → PASS
✅ Test case 2: Jane Doe → PASS
✅ Test case 3: Bob Johnson → PASS

Summary: 3/3 passed
```

**If failures occur**: Check player names are exact matches. Visit nikeeyb.com to verify spelling.

### Step 4: Backfill EYBL Data

```bash
# Full backfill (2024, 2023, 2022 seasons)
python scripts/backfill_eybl_player_seasons.py --seasons 2024 2023 2022

# Output:
# ✅ data/eybl/eybl_player_seasons_2024.parquet (500-800 players)
# ✅ data/eybl/eybl_player_seasons_2023.parquet
# ✅ data/eybl/eybl_player_seasons_2022.parquet
# ✅ data/eybl/eybl_player_seasons_all.parquet (combined)
```

**Expected**: 1,500-2,400 player-season records across 3 years.

### Step 5: Load to DuckDB

```bash
python scripts/load_to_duckdb.py --sources eybl

# Output:
# ✅ Loaded 1,847 records to data/hs_player_seasons.duckdb
# By source:
#   - eybl: 1,847
# By season:
#   - 2024: 623
#   - 2023: 615
#   - 2022: 609
```

### Step 6: Run QA Validation

```bash
python scripts/qa_player_seasons.py --source eybl --export-report reports/qa_eybl.md

# Expected output:
# ✅ shooting_sanity: PASS
# ✅ three_point_sanity: PASS
# ✅ percentage_bounds: PASS
# ... (8 checks total)
#
# ✅ QA PASSED: All validation checks passed
```

**If QA fails**: Review `reports/qa_eybl.md` for specific violations. Fix EYBL adapter logic.

### Step 7: Mark EYBL Green

Edit `config/datasource_status.yaml`:

```yaml
eybl:
  status: "green"  # ← Change from yellow to green
  validation_passing: true
  parquet_exports: true
  last_validated: "2025-11-16"
  notes: "Fully validated with 3 test cases. 1,847 player-seasons exported."
```

**🎉 EYBL is now GREEN!**

---

## Phase 2: SBLive Green (3-4 hours)

### Step 1: Extract Player Names for WA, OR, CA (30 min, MANUAL)

Visit each state's SBLive site and extract 1 player per state:

**Washington**:
1. Visit https://www.sblive.com/washington/high-school-basketball/players
2. Pick 1 player with 10+ games, 5+ PPG
3. Note: Name, School, Season (2024-25)

**Oregon**:
1. Visit https://www.sblive.com/oregon/high-school-basketball/players
2. Pick 1 player with complete stats

**California**:
1. Visit https://www.sblive.com/california/high-school-basketball/players
2. Pick 1 player with complete stats

### Step 2: Update Test Cases

Edit `config/datasource_test_cases.yaml`:

```yaml
sblive:
  - player_name: "Michael Johnson"  # ← Real WA player
    season: "2024-25"
    state: "WA"
    team_hint: "O'Dea High School"
    expected_min_games: 5
    expected_min_ppg: 5.0
    expected_max_ppg: 40.0

  - player_name: "Sarah Williams"  # ← Real OR player
    season: "2024-25"
    state: "OR"
    team_hint: "South Salem High School"
    expected_min_games: 5
    expected_min_ppg: 5.0
    expected_max_ppg: 40.0

  - player_name: "David Lee"  # ← Real CA player
    season: "2024-25"
    state: "CA"
    team_hint: "Sierra Canyon High School"
    expected_min_games: 5
    expected_min_ppg: 5.0
    expected_max_ppg: 40.0
```

### Step 3: Run Validation

```bash
python scripts/validate_datasource_stats.py --source sblive --verbose
```

### Step 4: Backfill SBLive Data

```bash
# Backfill WA, OR, CA for 2024-25 season
python scripts/backfill_sblive_player_seasons.py --states WA OR CA --season 2024-25

# Output:
# ✅ data/sblive/sblive_player_seasons_WA_2024-25.parquet (500-1000 players)
# ✅ data/sblive/sblive_player_seasons_OR_2024-25.parquet
# ✅ data/sblive/sblive_player_seasons_CA_2024-25.parquet
# ✅ data/sblive/sblive_player_seasons_all.parquet
```

**Expected**: 1,500-3,000 player-season records from 3 states.

### Step 5: Load to DuckDB

```bash
python scripts/load_to_duckdb.py --sources sblive

# Now DuckDB has both EYBL + SBLive data!
# Total records: ~3,500-5,500
```

### Step 6: Run QA

```bash
python scripts/qa_player_seasons.py --source sblive --export-report reports/qa_sblive.md
```

### Step 7: Mark SBLive Green

```yaml
sblive:
  status: "green"
  validation_passing: true
  parquet_exports: true
  states_covered: ["WA", "OR", "CA"]
```

**🎉 SBLive is now GREEN!**

---

## Phase 3: Master Pipeline (Optional)

Once both sources are green, use the master runner:

```bash
# Run full pipeline for all green sources
./scripts/run_full_hs_pipeline.sh

# Run EYBL only
./scripts/run_full_hs_pipeline.sh --source eybl

# Dry-run (validation only, no backfill)
./scripts/run_full_hs_pipeline.sh --dry-run
```

**What it does**:
1. ✅ Check dependencies
2. ✅ Create directories (data/eybl, data/sblive, reports/)
3. ✅ Run validation for each source
4. ✅ Run backfill (if validation passes)
5. ✅ Load to DuckDB
6. ✅ Run QA validation
7. ✅ Generate summary report

**Output Example**:
```
================================================================================
Pipeline Summary
================================================================================
✅ Pipeline complete!

Parquet files generated:
  - EYBL: 4 file(s)
  - SBLive: 4 file(s)

DuckDB database: data/hs_player_seasons.duckdb

Query your data with:
  duckdb data/hs_player_seasons.duckdb "SELECT source, season, COUNT(*) FROM hs_player_seasons GROUP BY source, season;"
================================================================================
```

---

## Phase 4: Query Your Data

```bash
# Connect to DuckDB
duckdb data/hs_player_seasons.duckdb

# Example queries:
-- Total player-seasons by source
SELECT source, COUNT(*) as records
FROM hs_player_seasons
GROUP BY source;

-- Top scorers across all sources
SELECT full_name, source, season, points_per_game, team_name
FROM hs_player_seasons
WHERE points_per_game IS NOT NULL
ORDER BY points_per_game DESC
LIMIT 25;

-- Coverage by state
SELECT state_code, COUNT(*) as players
FROM hs_player_seasons
WHERE state_code IS NOT NULL
GROUP BY state_code
ORDER BY players DESC;

-- Compare EYBL vs SBLive stats
SELECT
    source,
    AVG(points_per_game) as avg_ppg,
    AVG(rebounds_per_game) as avg_rpg,
    AVG(assists_per_game) as avg_apg,
    AVG(field_goal_percentage) as avg_fg_pct
FROM hs_player_seasons
WHERE games_played >= 5
GROUP BY source;
```

---

## Phase 5: Expand Coverage

### SBLive State Expansion (3-4 hours)

Add more states (TX, FL, GA, NC, VA, OH, PA, etc.):

```bash
# Add test cases for new states in datasource_test_cases.yaml
# Then backfill:
python scripts/backfill_sblive_player_seasons.py --states TX FL GA NC --season 2024-25

# Load to DuckDB
python scripts/load_to_duckdb.py --sources sblive

# QA check
python scripts/qa_player_seasons.py --source sblive
```

**Target**: 20+ states = 10,000-20,000 player-seasons

---

## Troubleshooting

### Validation Fails: "Player not found"

**Cause**: Player name doesn't exactly match source website.

**Fix**:
1. Visit source website (nikeeyb.com or sblive.com)
2. Copy exact spelling of player name
3. Update `datasource_test_cases.yaml` with exact match

### Backfill Produces 0 Records

**Cause**: Browser automation error (Cloudflare block, crashed browser, etc.)

**Fix**:
1. Ensure Playwright browsers installed: `playwright install chromium --with-deps`
2. Check internet connection
3. Try with `--limit 10` first to test
4. Check logs for specific error messages

### QA Validation Errors

**Cause**: Data violates schema rules (FGM > FGA, percentages > 1, etc.)

**Fix**:
1. Review `reports/qa_*.md` for specific violations
2. Inspect raw data: `duckdb data/hs_player_seasons.duckdb "SELECT * FROM hs_player_seasons WHERE field_goals_made > field_goals_attempted;"`
3. Fix adapter parsing logic in `src/datasources/us/<source>/`
4. Re-run backfill

### DuckDB "Primary Key Violation"

**Cause**: Duplicate (source, source_player_id, season) combinations.

**Fix**:
1. Use `--rebuild` flag to drop and recreate table:
   ```bash
   python scripts/load_to_duckdb.py --rebuild
   ```

---

## Next Steps After Green

Once EYBL + SBLive are green with parquet exports:

1. **Entity Resolution** (Phase 17): Merge same player across sources
2. **HS → College Linkage**: Match HS players to college rosters by name + grad_year
3. **Forecasting Model**: Predict college success from HS stats
4. **Additional Sources**: OSBA, 3SSB, UAA, FIBA (using same playbook)

---

## File Locations

```
config/
  ├── datasource_status.yaml        # Green/Yellow/Red status tracking
  ├── datasource_test_cases.yaml    # Test cases (UPDATE THIS)
  └── hs_player_season_schema.yaml  # Canonical schema definition

scripts/
  ├── run_full_hs_pipeline.sh       # 🔴 Master pipeline runner
  ├── validate_datasource_stats.py  # Validation (step 1)
  ├── backfill_eybl_player_seasons.py      # EYBL export (step 2)
  ├── backfill_sblive_player_seasons.py    # SBLive export (step 2)
  ├── load_to_duckdb.py             # Combine sources (step 3)
  └── qa_player_seasons.py          # QA validation (step 4)

data/
  ├── eybl/
  │   ├── eybl_player_seasons_2024.parquet
  │   ├── eybl_player_seasons_2023.parquet
  │   ├── eybl_player_seasons_2022.parquet
  │   └── eybl_player_seasons_all.parquet
  ├── sblive/
  │   ├── sblive_player_seasons_WA_2024-25.parquet
  │   ├── sblive_player_seasons_OR_2024-25.parquet
  │   └── sblive_player_seasons_CA_2024-25.parquet
  └── hs_player_seasons.duckdb      # Combined database

reports/
  ├── qa_eybl_20251116.md           # QA report for EYBL
  └── qa_sblive_20251116.md         # QA report for SBLive
```

---

## Summary: 1-2 Hours to First Data

| Phase | Time | Status |
|-------|------|--------|
| **Extract EYBL test cases** | 15-30 min | ⚠️ MANUAL REQUIRED |
| **Validate + Backfill EYBL** | 15-20 min | ✅ AUTOMATED |
| **Extract SBLive test cases** | 30 min | ⚠️ MANUAL REQUIRED |
| **Validate + Backfill SBLive** | 20-30 min | ✅ AUTOMATED |
| **Load DuckDB + QA** | 5 min | ✅ AUTOMATED |
| **TOTAL** | **1-2 hours** | **🔴 READY** |

**🎉 You're ready to push the red button and produce your first production parquet files!**
