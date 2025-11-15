# Coverage Enhancement Plan - Steps 2-8 Implementation

**Date**: 2025-11-15
**Goal**: Reach 100% measured coverage on college-outcome cohort
**Status**: Step 1 (Coverage Metrics) ✅ Complete, Steps 2-8 in progress

---

## Current State Analysis

### ✅ What Exists:
1. **Coverage Metrics** (`src/services/coverage_metrics.py`):
   - CoverageFlags dataclass with tier-based scoring
   - compute_coverage_score() with weighted metrics
   - extract_coverage_flags_from_profile()
   - Integrated into ForecastingDataAggregator (Phase 5)

2. **MaxPreps DataSource** (`src/datasources/us/maxpreps.py`):
   - `search_players_with_stats()` method ✅ EXISTS
   - Returns (Player, PlayerSeasonStats) tuples
   - Includes advanced stats (TS%, eFG%, A/TO)
   - **NOT CURRENTLY USED IN FORECASTING** ❌

3. **Identity Resolution** (`src/services/identity.py`):
   - Basic: name + school + grad_year only
   - No birth_date, height, weight, team matching
   - No confidence scores
   - **NEEDS ENHANCEMENT** ⚠️

4. **DuckDB Storage** (`src/services/duckdb_storage.py`):
   - Tables: players, teams, player_season_stats, games, recruiting_ranks, college_offers
   - **MISSING**: historical_snapshots, player_vectors tables ❌

5. **ForecastingDataAggregator** (`src/services/forecasting.py`):
   - Phase 1: Bio data (247Sports only)
   - Phase 2: Stats aggregation (generic)
   - Phase 3: Recruiting data (247Sports)
   - Phase 4: Forecasting score calculation
   - Phase 5: Coverage measurement ✅ NEW
   - **NOT USING MaxPreps** ❌
   - **NOT TRACKING MISSING REASONS** ❌

---

## Implementation Plan

### **Step 2: Wire MaxPreps Advanced Stats into Forecasting** [PRIORITY 1]

**Impact**: +15-20% coverage for US HS players
**Complexity**: LOW (MaxPreps method exists, just needs integration)
**Files to modify**: `src/services/forecasting.py`

**Changes**:
1. Add Phase 2.5: MaxPreps Stats (between current Phase 2 and Phase 3)
2. Call `maxpreps.search_players_with_stats(state=state, name=player_name)`
3. Extract advanced stats: TS%, eFG%, A/TO, per-40 stats
4. Record missing reason if MaxPreps fails: `missing_maxpreps_data = True`
5. Update coverage flags to track MaxPreps usage

**Integration Points**:
- Insert after line 238 (after bio data extraction)
- Before line 247 (stats aggregation)
- Use existing `state` parameter from profile

**Validation**:
- Test with Cooper Flagg (ME), AJ Dybantsa (UT)
- Verify advanced stats populated
- Confirm coverage_summary reflects MaxPreps data

---

### **Step 7: Treat Missingness as Features** [PRIORITY 2]

**Impact**: +5-10% ML model accuracy (missing indicators as features)
**Complexity**: LOW (add fields to profile)
**Files to modify**: `src/services/forecasting.py`, `src/services/coverage_metrics.py`

**Changes**:
1. Add `missing_reasons` dict to profile:
   ```python
   "missing_reasons": {
       "missing_247_profile": False,
       "missing_maxpreps_data": False,
       "missing_multi_season_data": False,
       "missing_recruiting_coverage": False,
       "missing_birth_date": False,
       "missing_physical_measurements": False,
       "missing_international_data": False,
   }
   ```
2. Update coverage_metrics to populate from profile
3. Add binary indicators for ML features:
   ```python
   "feature_flags": {
       "has_recruiting_data": True,
       "has_advanced_stats": True,
       "has_progression_data": True,
   }
   ```

**Integration Points**:
- Add to profile initialization (line 90-130)
- Update in each phase when data is missing
- Extract in coverage_metrics.extract_coverage_flags_from_profile()

---

### **Step 5: Tighten Identity Resolution** [PRIORITY 3]

**Impact**: +10-15% coverage (better player deduplication)
**Complexity**: MEDIUM (enhance matching algorithm)
**Files to modify**: `src/services/identity.py`

**Changes**:
1. **Enhanced matching keys**:
   ```python
   def resolve_player_uid_enhanced(
       name: str,
       school: str,
       grad_year: Optional[int] = None,
       birth_date: Optional[str] = None,
       height: Optional[int] = None,
       weight: Optional[int] = None,
       state: Optional[str] = None,
       country: Optional[str] = None,
   ) -> Tuple[str, float]:  # Returns (uid, confidence)
   ```

2. **Confidence scoring**:
   - Perfect match (name + birth_date + school): 1.0
   - Strong match (name + grad_year + height + weight): 0.9
   - Good match (name + school + grad_year): 0.8
   - Weak match (name + grad_year): 0.6
   - Fuzzy match (name similarity >0.85 + school): 0.5

3. **Multi-attribute hashing**:
   ```python
   def _create_player_hash(player_data: Dict) -> str:
       # Use multiple attributes for uniqueness
       key_parts = [
           _normalize_name(player_data.get("name", "")),
           player_data.get("birth_date", ""),
           _normalize_school(player_data.get("school", "")),
           str(player_data.get("grad_year", "")),
           str(player_data.get("height", "")),
           player_data.get("country", ""),
       ]
       return "::".join(p for p in key_parts if p)
   ```

4. **Duplicate detection**:
   - Log potential duplicates when confidence < 0.8
   - Return list of candidate matches for manual review
   - Track merge history

**Integration Points**:
- Update `deduplicate_players()` to use enhanced matching
- Add confidence scores to Player model (optional field)
- Update forecasting to log low-confidence merges

---

### **Step 6: Create DuckDB Historical Tables** [PRIORITY 4]

**Impact**: Enables multi-season tracking (+15% coverage)
**Complexity**: MEDIUM (schema design + backfill)
**Files to modify**: `src/services/duckdb_storage.py`, new script `scripts/backfill_historical_snapshots.py`

**Changes**:
1. **Add historical_snapshots table**:
   ```sql
   CREATE TABLE IF NOT EXISTS historical_snapshots (
       snapshot_id INTEGER PRIMARY KEY,
       player_uid TEXT NOT NULL,
       snapshot_date DATE NOT NULL,
       season TEXT,  -- "2023-24"
       grad_year INTEGER,

       -- Bio snapshot
       height INTEGER,
       weight INTEGER,
       position TEXT,
       birth_date DATE,

       -- Recruiting snapshot
       composite_247_rating REAL,
       stars_247 INTEGER,
       power_6_offer_count INTEGER,
       total_offer_count INTEGER,

       -- Performance snapshot
       ppg REAL,
       rpg REAL,
       apg REAL,
       ts_pct REAL,
       efg_pct REAL,
       ato_ratio REAL,

       -- Context
       school_name TEXT,
       state TEXT,
       league TEXT,

       FOREIGN KEY (player_uid) REFERENCES players(player_uid)
   )
   ```

2. **Add player_vectors table**:
   ```sql
   CREATE TABLE IF NOT EXISTS player_vectors (
       vector_id INTEGER PRIMARY KEY,
       player_uid TEXT NOT NULL,
       season TEXT NOT NULL,

       -- 12-dimensional normalized vector for similarity
       ppg_per40_norm REAL,
       rpg_per40_norm REAL,
       apg_per40_norm REAL,
       spg_per40_norm REAL,
       bpg_per40_norm REAL,
       ts_pct_norm REAL,
       efg_pct_norm REAL,
       ato_ratio_norm REAL,
       height_norm REAL,
       weight_norm REAL,
       age_for_grade_norm REAL,
       mpg_norm REAL,

       -- Metadata
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

       FOREIGN KEY (player_uid) REFERENCES players(player_uid)
   )
   ```

3. **Backfill script** (`scripts/backfill_historical_snapshots.py`):
   - Read existing player_season_stats table
   - Create snapshot for each player/season combination
   - Normalize stats for player_vectors
   - Populate both tables

**Integration Points**:
- Add table creation to DuckDBStorage.__init__()
- Create insert methods: insert_historical_snapshot(), insert_player_vector()
- Wire into ForecastingDataAggregator to save snapshots

---

### **Step 3: Build College-Outcome Cohort Loader** [PRIORITY 5]

**Impact**: Enables real coverage measurement on target cohort
**Complexity**: MEDIUM (requires college/pro data)
**Files to create**: `scripts/build_college_cohort.py`, `data/college_cohort_d1_2014_2023.csv`

**Changes**:
1. **College cohort definition**:
   - D1 players who played 2014-2023
   - Include: name, HS name, grad year, birth date, college, draft status
   - Source: Scrape from college rosters or use existing datasets

2. **Cohort loader**:
   ```python
   async def load_college_outcome_cohort(
       min_year: int = 2014,
       max_year: int = 2023,
       division: str = "D1"
   ) -> List[Dict]:
       # Load from CSV or database
       # Return list of player records
   ```

3. **Coverage measurement on cohort**:
   - Run report_coverage.py on this specific cohort
   - Measure actual coverage %
   - Identify gaps by segment (US HS vs International)

**Integration Points**:
- Use in report_coverage.py as primary cohort
- Track coverage progression over time
- Set as benchmark: "X% of D1 cohort has full recruiting data"

---

### **Step 4: Add ESPN/On3/Rivals Sources (Stubs)** [PRIORITY 6]

**Impact**: +20-25% coverage (additional recruiting sources)
**Complexity**: HIGH (new scrapers)
**Files to create**: `src/datasources/recruiting/espn.py`, `on3.py`, `rivals.py`

**Changes**:
1. Create stub datasources:
   ```python
   class ESPNRecruitingDataSource(BaseDataSource):
       source_type = DataSourceType.ESPN
       source_name = "ESPN Recruiting"
       base_url = "https://www.espn.com/college-sports/basketball/recruiting"

       async def search_players(self, name: str, class_year: int):
           # TODO: Implement ESPN scraper
           raise NotImplementedError("ESPN recruiting scraper not yet implemented")
   ```

2. Document API requirements:
   - ESPN: Check ToS, may require API key
   - On3: VIP subscription required for full data
   - Rivals: Yahoo Sports network, check legal

3. Register in source_registry:
   - Add to RECRUITING_SOURCES list
   - Enable/disable via config

**Integration Points**:
- Call from ForecastingDataAggregator Phase 3 (recruiting)
- Merge with 247Sports data
- Track which source provided each data point

**Note**: These are STUBS for now - full implementation requires legal review and ToS compliance

---

### **Step 8: Enable Real-Data Tests** [PRIORITY 7]

**Impact**: Validation of all enhancements
**Complexity**: LOW (mostly test infrastructure)
**Files to modify**: `scripts/report_coverage.py`, new `tests/test_coverage_real_data.py`

**Changes**:
1. **Fix environment dependencies**:
   ```bash
   # Install missing packages
   pip install pytest beautifulsoup4 pytest-asyncio
   ```

2. **Real-data test suite**:
   ```python
   @pytest.mark.asyncio
   async def test_coverage_top_recruits():
       # Test top 10 2025 recruits
       players = ["Cooper Flagg", "AJ Dybantsa", "Cameron Boozer"]

       for player in players:
           profile = await get_forecasting_data_for_player(player, 2025)
           coverage = profile["coverage_summary"]

           assert coverage["overall_score"] > 70  # Should have GOOD coverage
           assert coverage["tier1_critical"] > 80  # Should have recruiting data
   ```

3. **Run report_coverage.py**:
   - Test with sample players
   - Generate actual coverage report
   - Validate recommendations

**Integration Points**:
- pytest fixtures for test data
- Mock browser client if needed
- Cache test results to avoid re-scraping

---

## Priority Order (Implementation Sequence)

1. ✅ **Step 1**: Coverage Metrics Framework (COMPLETE)
2. 🔄 **Step 2**: Wire MaxPreps into Forecasting (15-20% coverage gain, LOW complexity)
3. 🔄 **Step 7**: Missingness as Features (5-10% ML gain, LOW complexity)
4. 🔄 **Step 5**: Identity Resolution (10-15% coverage gain, MEDIUM complexity)
5. 🔄 **Step 6**: DuckDB Historical Tables (15% coverage gain, MEDIUM complexity)
6. ⏳ **Step 3**: College Cohort Loader (enables real measurement, MEDIUM complexity)
7. ⏳ **Step 4**: ESPN/On3/Rivals Stubs (20-25% coverage gain, HIGH complexity - stubs only)
8. ⏳ **Step 8**: Real-Data Tests (validation, LOW complexity)

**Estimated Total Implementation Time**: 8-12 hours
**Estimated Coverage Gain**: +65-85% (from current 73% design to near 100% measured)

---

## Success Metrics

### After Step 2 (MaxPreps):
- ✅ MaxPreps stats appear in forecasting profiles for US players
- ✅ `has_maxpreps_stats` flag = True for 80%+ of US HS players
- ✅ `best_ts_pct`, `best_efg_pct`, `best_ato_ratio` populated from MaxPreps

### After Step 7 (Missingness):
- ✅ All profiles have `missing_reasons` dict
- ✅ Coverage metrics include missing counts
- ✅ Feature flags present for ML models

### After Step 5 (Identity):
- ✅ Duplicate players reduced by 30%+
- ✅ Confidence scores logged for all merges
- ✅ Low-confidence matches (<0.8) flagged for review

### After Step 6 (DuckDB):
- ✅ historical_snapshots table populated with 10,000+ snapshots
- ✅ player_vectors table ready for similarity searches
- ✅ Multi-season data tracked in DuckDB

### After Step 3 (Cohort):
- ✅ D1 cohort (2014-2023) loaded with 5,000+ players
- ✅ Real coverage measured on cohort: 75-85%
- ✅ Gap analysis by segment (US HS: 85%, International: 60%)

### Final (After Step 8):
- ✅ All tests passing (pytest)
- ✅ report_coverage.py runs successfully
- ✅ Coverage dashboard shows real numbers
- ✅ 85-95% measured coverage on college-outcome cohort

---

## Next Actions

1. Implement Step 2 (MaxPreps integration) - ~1 hour
2. Implement Step 7 (Missingness tracking) - ~45 minutes
3. Implement Step 5 (Identity resolution) - ~2 hours
4. Implement Step 6 (DuckDB tables) - ~2 hours
5. Implement Step 3 (College cohort) - ~1.5 hours
6. Create Step 4 stubs (ESPN/On3/Rivals) - ~30 minutes
7. Fix Step 8 (Real-data tests) - ~1 hour
8. Full validation and commit - ~1 hour

**Total**: ~10 hours of implementation

---

**Document Status**: Planning Complete ✅
**Next**: Begin implementation of Step 2 (MaxPreps integration)
