# Coverage Measurement Workflow

**Purpose**: Get from 0% to high coverage on the cohort that matters (D1 college players 2014-2023)

**Reality Check**: Enhancement 12 built the infrastructure, but you don't have 100% coverage yet. This guide shows you how to actually measure and achieve high coverage.

---

## Current Status: What You Have vs What You Need

### ✅ What You Have (Infrastructure)

1. **Coverage Measurement Framework** (Enhancement 9, 10, 11)
   - `scripts/report_coverage.py` - Measures coverage per player
   - `scripts/dashboard_coverage.py` - Visual gap analysis
   - Coverage metrics: CoverageFlags, CoverageScore (0-100%)

2. **State Normalization** (Enhancement 12.1)
   - `MaxPrepsDataSource.normalize_state()` - Handles "Florida"→"FL", "Fla"→"FL"
   - +15-20% potential matching improvement

3. **CSV Recruiting Import** (Enhancement 12.3)
   - `CSVRecruitingDataSource` - Legal recruiting data import
   - No scraping, no ToS issues
   - +20-30% potential recruiting coverage

4. **State Datasource Template** (Enhancement 12.5)
   - `src/datasources/us/state/state_template.py` - Copy and customize
   - Enables targeted state expansion

### ❌ What You Still Need (Data)

1. **College Cohort CSV** - Empty / not populated
2. **Recruiting CSVs** - No actual ranking data imported
3. **State Datasources** - No state-specific sources implemented yet

**Bottom Line**: You have the pipes, but no water flowing through them yet.

---

## Step-by-Step Workflow: 0% → High Coverage

### Phase 1: Measure Current State (Baseline)

#### 1.1 Populate College Cohort CSV

**Option A**: Start with example data (quick test)
```bash
# Use the provided example with 30 real players
cp data/college_cohort_example.csv data/college_cohort_d1_2014_2023.csv
```

**Option B**: Populate with full D1 cohort (real measurement)
```bash
# Use example as template
cp data/college_cohort_example.csv data/college_cohort_d1_2014_2023.csv

# Add your D1 players (2014-2023) following this format:
# player_name,hs_name,hs_state,grad_year,birth_date,college,college_years,drafted,nba_team
```

**CSV Format**:
- `player_name`: Full name (e.g., "Cooper Flagg")
- `hs_name`: High school (e.g., "Montverde Academy")
- `hs_state`: State code (e.g., "FL" - MaxPreps normalizes variants)
- `grad_year`: HS graduation year (e.g., 2025)
- `birth_date`: YYYY-MM-DD format (e.g., "2006-12-21")
- `college`: College attended (e.g., "Duke")
- `college_years`: Years played (e.g., "2025-2026")
- `drafted`: True/False
- `nba_team`: Team name or empty

#### 1.2 Run Initial Coverage Measurement

```bash
# Build filtered cohort
python scripts/build_college_cohort.py \
  --source csv \
  --min-year 2014 \
  --max-year 2023 \
  --output data/college_cohort_filtered.csv

# Run coverage dashboard (visual)
python scripts/dashboard_coverage.py \
  --cohort data/college_cohort_filtered.csv \
  --export data/state_gaps_baseline.csv

# Or run detailed report
python scripts/report_coverage.py \
  --cohort data/college_cohort_filtered.csv \
  --state-gaps data/state_gaps_baseline.csv
```

**What You'll See**:
```
STATE COVERAGE DASHBOARD
========================

🎯 TOP 10 PRIORITY STATES (Player Count × Coverage Gap)

State  Players  Coverage   Gap        Priority
------ -------- ---------- ---------- ------------
FL     8        42.3%      57.7%      🔴 461.6
TX     3        38.5%      61.5%      🔴 184.5
CA     5        55.2%      44.8%      🟡 224.0
...

📊 COVERAGE DISTRIBUTION (Top 10 States)

 1. FL (8p)          ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓·············  42.3%
 2. CA (5p)          ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓······  55.2%
 3. TX (3p)          ░░░░░░░░░░░░░░░░░░░····  38.5%
...

🔍 GAP ANALYSIS (Top 5 Priority States)

1. FL - 8 players, 42.3% coverage
   Missing Breakdown:
     MaxPreps:        65%
     Recruiting:      50%
     Advanced Stats:  72%
   🎯 Actions:
      • Fix MaxPreps state normalization
      • Import FL recruiting CSV (247/ESPN)
      • Consider FL state datasource adapter
...
```

**Expected Baseline**: 30-50% average coverage (without CSV recruiting data)

---

### Phase 2: Quick Wins (CSV Recruiting Import)

#### 2.1 Import Recruiting Rankings

```bash
# Copy example to actual file
cp data/recruiting/247_rankings_example.csv data/recruiting/247_rankings.csv

# (Optional) Add more sources
# data/recruiting/espn_rankings.csv
# data/recruiting/on3_rankings.csv
# data/recruiting/rivals_rankings.csv
```

**CSV Format** (247_rankings.csv):
```csv
player_id,player_name,class_year,state,position,rank_national,rank_state,rank_position,stars,rating,height,weight,high_school,city,committed_to,source
247_cooper_flagg,Cooper Flagg,2025,FL,SF,1,1,1,5,0.9999,6-9,205,Montverde Academy,Montverde,Duke,247Sports
```

#### 2.2 Wire CSV Recruiting into Forecasting

The CSV recruiting source is already available, but you need to wire it into the forecasting aggregator:

**File**: `src/services/forecasting.py`

Add this to Phase 2 (recruiting data fetch):

```python
# Around line 320-350, after 247Sports recruiting fetch

# Enhancement 12.3: CSV Recruiting Import
if "csv_recruiting" in self.aggregator.recruiting_sources:
    try:
        csv_recruiting = self.aggregator.recruiting_sources["csv_recruiting"]
        csv_results = await csv_recruiting.search_players(
            name=player_name,
            class_year=grad_year,
            state=state,
            limit=5
        )

        if csv_results:
            profile["raw_recruiting_ranks"].extend(csv_results)
            # Update recruiting metrics from CSV
            for rank in csv_results:
                if rank.rank_national and (not profile["best_national_rank"] or rank.rank_national < profile["best_national_rank"]):
                    profile["best_national_rank"] = rank.rank_national
                if rank.stars and not profile["stars_247"]:
                    profile["stars_247"] = rank.stars
                if rank.rating and not profile["composite_247_rating"]:
                    profile["composite_247_rating"] = rank.rating

            self.logger.info(f"Added CSV recruiting data", player_name=player_name, ranks=len(csv_results))
    except Exception as e:
        self.logger.warning(f"CSV recruiting fetch failed", error=str(e))
```

#### 2.3 Re-Run Coverage Measurement

```bash
# Re-run dashboard
python scripts/dashboard_coverage.py \
  --cohort data/college_cohort_filtered.csv \
  --export data/state_gaps_after_csv.csv
```

**Expected Improvement**: +20-30% for top-ranked players (those in CSV)

---

### Phase 3: State-Specific Sources (Targeted Expansion)

#### 3.1 Identify High-Value States

Look at your dashboard output for states with:
- HIGH priority (🔴 red)
- Many players
- High coverage gap

Example targets: FL, TX, CA, GA, IL, NY

#### 3.2 Implement State Datasource

**Example: Florida FHSAA**

```bash
# Copy template
cp src/datasources/us/state/state_template.py \
   src/datasources/us/state/fl_fhsaa.py
```

Edit `fl_fhsaa.py`:

```python
# Replace placeholders
STATE_CODE = "FL"
source_name = "Florida FHSAA"
base_url = "https://www.fhsaa.org"  # Or stats partner site

# Implement search_players()
async def search_players(self, state, name, team, season, limit):
    if state != "FL":
        return []

    # Your FL-specific scraping logic here
    # ...
```

Add to `DataSourceType` in `src/models/source.py`:
```python
FHSAA = "fhsaa"  # Florida High School Athletic Association
```

Wire into aggregator in `src/services/aggregator.py`:
```python
# Add to stats_sources dict
"fhsaa": FHSAADataSource(),
```

#### 3.3 Re-Measure Coverage

```bash
python scripts/dashboard_coverage.py \
  --cohort data/college_cohort_filtered.csv \
  --export data/state_gaps_after_fl.csv
```

**Expected Improvement**: +15-25% for FL players specifically

---

### Phase 4: Iterate and Optimize

#### 4.1 Focus on Top 5-10 States

Use 80/20 rule: Top 10 states likely represent 70-80% of D1 players.

Priority order (based on D1 production):
1. CA (California)
2. TX (Texas)
3. FL (Florida)
4. GA (Georgia)
5. IL (Illinois)
6. NY (New York)
7. NC (North Carolina)
8. VA (Virginia)
9. OH (Ohio)
10. PA (Pennsylvania)

#### 4.2 Measure Progress

After each enhancement:

```bash
# Quick visual check
python scripts/dashboard_coverage.py --cohort data/college_cohort_filtered.csv

# Compare to baseline
diff data/state_gaps_baseline.csv data/state_gaps_current.csv
```

#### 4.3 Set Realistic Goals

**Realistic Coverage Targets**:
- **Top Recruits** (Top 100 nationally): 80-90% coverage ✅
- **D1 Players from Top States** (CA, TX, FL, GA, IL): 70-80% coverage ✅
- **All D1 Players (US)**: 60-70% coverage ✅
- **International Players**: 30-40% coverage ⚠️ (limited data sources)

**Why Not 100%?**
- Some states have no public HS stats
- International players (FIBA data gaps)
- G League Ignite / prep schools (non-traditional paths)
- Privacy restrictions (some states)
- Historical data gaps (pre-2018)

---

## Common Issues and Solutions

### Issue 1: Low MaxPreps Matching

**Symptom**: `missing_maxpreps_data` > 60% for US states

**Causes**:
1. State name variant not normalized ("Florida" vs "FL")
2. Name spelling differences
3. School name differences
4. Player not in MaxPreps (non-varsity, international)

**Solutions**:
```python
# Already fixed in Enhancement 12.1
from src.datasources.us.maxpreps import MaxPrepsDataSource

# Test normalization
MaxPrepsDataSource.normalize_state("Florida")  # → "FL"
MaxPrepsDataSource.normalize_state("Fla")      # → "FL"
MaxPrepsDataSource.normalize_state("N.Y.")     # → "NY"
```

### Issue 2: No Recruiting Coverage

**Symptom**: `missing_recruiting_coverage` > 70%

**Causes**:
1. No recruiting CSVs imported
2. Player not ranked (lower-tier recruits)
3. Name mismatch in CSV

**Solutions**:
1. Import recruiting CSVs (see Phase 2.1)
2. Accept that not all players are ranked (focus on top recruits)
3. Improve name matching in identity resolution

### Issue 3: Low Advanced Stats Coverage

**Symptom**: `missing_advanced_stats` > 60%

**Causes**:
1. MaxPreps doesn't have advanced stats for that state/player
2. State doesn't track advanced stats publicly
3. Player's school doesn't report to MaxPreps

**Solutions**:
1. Implement state-specific datasource (see Phase 3)
2. Accept gaps for low-data states
3. Use imputation for missing advanced stats in ML models

---

## Progress Tracking

### Baseline Measurement (Before CSV/State Sources)

Date: _______
Players: _______
Avg Coverage: _______%
Top Priority States: _______

### After CSV Recruiting Import

Date: _______
Players: _______
Avg Coverage: _______% (+____%)
Top Priority States: _______

### After State Sources (specify states)

States Implemented: _______
Date: _______
Players: _______
Avg Coverage: _______% (+____%)
Remaining Gaps: _______

---

## Quick Reference Commands

```bash
# 1. Build cohort
python scripts/build_college_cohort.py \
  --source csv \
  --output data/college_cohort_filtered.csv

# 2. Visual dashboard
python scripts/dashboard_coverage.py \
  --cohort data/college_cohort_filtered.csv \
  --export data/state_gaps.csv

# 3. Detailed report
python scripts/report_coverage.py \
  --cohort data/college_cohort_filtered.csv \
  --state-gaps data/state_gaps_detail.csv

# 4. Test recruiting CSV
python -c "
import asyncio
from pathlib import Path
from src.datasources.recruiting import CSVRecruitingDataSource

async def test():
    csv_recruiting = CSVRecruitingDataSource(csv_dir=Path('data/recruiting'))
    ranks = await csv_recruiting.get_rankings(class_year=2025, limit=10)
    for r in ranks:
        print(f'{r.rank_national}. {r.player_name} - {r.stars}★')

asyncio.run(test())
"

# 5. Backfill historical data
python scripts/backfill_historical_snapshots.py
```

---

## Next Steps

1. **Today**: Run baseline measurement (Phase 1)
2. **This Week**: Import recruiting CSVs (Phase 2)
3. **This Month**: Implement 1-2 state sources (Phase 3)
4. **Ongoing**: Iterate based on dashboard feedback

**Remember**: 60-70% coverage on D1 US players is realistic and sufficient for high-quality forecasting. Focus on the players that matter most!
