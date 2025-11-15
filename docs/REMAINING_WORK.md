# Remaining Work - Priority Ranked

**Last Updated**: 2025-11-16
**Session**: claude/review-repository-structure-01LXMUgjibDpdU2jbqwToCLP

---

## Overview

This document tracks all remaining work needed to complete the HS Basketball Players MCP project. Organized by priority (P0 = Critical, P1 = High, P2 = Medium, P3 = Low).

**Current Status**:
- ✅ 4/71 datasources fully validated and operational
- ⏳ 67/71 datasources need validation or implementation
- ❌ 1/71 datasources blocked (PSAL - external dependency)
- 🏗️ Core infrastructure 100% complete

---

## P0: Critical Blockers

### 1. Fix Circular Import Issue
**Impact**: Blocks ALL pytest testing, validation scripts, and datasource testing

**Error**:
```
utils.__init__ → http_client → services.cache → services.__init__ → aggregator → datasources.base → utils
```

**Fix Needed**:
- Refactor import structure to break circular dependency
- Likely need to move some imports to function-level or use TYPE_CHECKING
- Estimated time: 2-4 hours

**Priority**: P0 - Must fix before further datasource validation

---

### 2. Validate MaxPreps
**Impact**: Would unlock all 51 US states immediately

**Current Status**: Code complete, never validated

**What To Test**:
- `search_players()` - Does it find players?
- `get_player_season_stats()` - Can it extract stats?
- State normalization - Does "Florida"→"FL" work?
- Historical data - Can it pull 2018-2023 seasons?

**Estimated Time**: 1-2 hours for validation + fixes

**Priority**: P0 - MaxPreps is THE critical US HS datasource

**Validation Command**:
```bash
python scripts/validate_datasources.py --source maxpreps --verbose
```

---

## P1: High Priority (Coverage Boost)

### 3. Implement Top 5 State Datasources
**Impact**: Top 5 states cover ~40% of US D1 players

**Missing States**:
1. **California (CIF)** - Largest state, ~15% of D1 players
2. **Texas (UIL)** - Second largest, ~12% of D1 players
3. **Florida (FHSAA)** - Already stubbed, needs implementation (~8%)
4. **Illinois (IHSA)** - Not created yet (~5%)
5. **New York (NYSPHSAA)** - Not created yet (~5%)

**Template**: `src/datasources/us/state/state_template.py`

**Implementation Steps (per state)**:
1. Copy state_template.py to new file (e.g., `california_cif.py`)
2. Find state association stats website
3. Implement `search_players()` and `get_player_season_stats()`
4. Wire into aggregator
5. Validate with real searches

**Estimated Time**: 4-6 hours per state (20-30 hours total)

**Priority**: P1 - Huge coverage impact

---

### 4. Implement 247Sports Scraping
**Impact**: +20-30% recruiting coverage

**Current Status**: STUB (`src/datasources/recruiting/sports_247.py`)

**What To Implement**:
- `get_rankings(class_year, state, position)` - Pull rankings pages
- `search_players(name, class_year)` - Find players
- `get_player_recruiting_profile(player_id)` - Full profile with offers

**Challenges**:
- Terms of Service prohibit scraping
- May need browser automation
- **Recommended**: Use CSV import instead for legal compliance

**Alternative**: Import 247 data via CSV Recruiting (already operational)

**Estimated Time**: 6-8 hours for scraping, OR 30 minutes for CSV import

**Priority**: P1 - Critical for recruiting coverage

**Recommendation**: Use CSV import (legal, faster, reliable)

---

### 5. Validate Grassroots Circuits
**Impact**: Elite circuit coverage (top 200-300 players per age group)

**Circuits To Validate**:
- ✅ **EYBL** - DONE (fixed 2025-11-16)
- ⏳ **UAA** - Needs validation
- ⏳ **3SSB** - Needs validation
- ⏳ **Grind Session** - Needs validation
- ⏳ **OTE** - Needs validation

**Validation Command**:
```bash
python scripts/validate_datasources.py --source uaa --verbose
python scripts/validate_datasources.py --source three_ssb --verbose
python scripts/validate_datasources.py --source grind_session --verbose
python scripts/validate_datasources.py --source ote --verbose
```

**Estimated Time**: 1-2 hours per circuit (debug + fix if needed)

**Priority**: P1 - Elite player coverage

---

## P2: Medium Priority (Data Quality)

### 6. Test Historical Data Retrieval
**Impact**: Enables training ML models on historical data

**What To Test**:
- Can each datasource pull stats from 2018, 2019, 2020, 2021, 2022, 2023?
- Are there gaps in historical coverage?
- Do URLs/selectors change for older seasons?

**Method**:
```python
for year in [2018, 2019, 2020, 2021, 2022, 2023]:
    stats = await datasource.get_player_season_stats(player_id, season=str(year))
    # Verify stats returned
```

**Datasources To Test**:
- MaxPreps (critical)
- EYBL
- UAA
- 3SSB
- MN Hub (✅ now has season fallback)
- State associations (varies)

**Estimated Time**: 3-5 hours

**Priority**: P2 - Important for ML, not critical for current coverage

---

### 7. Implement ESPN/On3 Recruiting
**Impact**: Diversify recruiting sources, reduce reliance on 247Sports

**Current Status**: STUBs

**Recommendation**: Skip - Use CSV import instead

**Reason**: All recruiting sites prohibit scraping. CSV import is:
- 100% legal
- Faster
- More reliable
- Easier to maintain

**Priority**: P2 - Low return vs effort

---

### 8. Create Coverage Dashboard Automation
**Impact**: Weekly monitoring of datasource health

**Already Created**: `scripts/monitor_datasource_health.py`

**What To Do**:
1. Set up weekly cron job / Task Scheduler
2. Configure email/Slack alerts for failures
3. Track trends over time (12-week history)

**Setup (Linux/Mac)**:
```cron
0 2 * * 1 cd /path/to/repo && python scripts/monitor_datasource_health.py
```

**Setup (Windows)**:
- Use Task Scheduler
- Trigger: Weekly on Monday at 2:00 AM
- Action: Run `python scripts/monitor_datasource_health.py`

**Estimated Time**: 1 hour

**Priority**: P2 - Prevents future breakage

---

## P3: Low Priority (International / Nice-to-Have)

### 9. Validate Europe Sources
**Impact**: European player coverage (smaller market)

**Sources To Validate**:
- ANGT (Adidas Next Gen)
- FIBA Youth
- NBBL Germany
- MKL Lithuania
- LNB Espoirs France
- FEB Spain

**Validation**: Same as grassroots circuits

**Estimated Time**: 6-10 hours total

**Priority**: P3 - International expansion

---

### 10. Validate Canada/Australia
**Impact**: Canadian and Australian coverage

**Sources**:
- OSBA Ontario
- NPA Canada
- PlayHQ Australia

**Estimated Time**: 2-4 hours

**Priority**: P3 - Small market

---

### 11. Implement Remaining State Associations
**Impact**: Complete US state coverage (beyond MaxPreps)

**Status**: 39/50 states have stub files, but most are templates

**Missing Major States** (beyond top 5):
- Georgia (GHSA) - Implemented but needs validation
- North Carolina (NCHSAA) - Stub
- Pennsylvania (PIAA) - Stub
- Ohio (OHSAA) - Stub
- Michigan (MHSAA) - Stub
- Virginia (VHSL) - Stub
- Indiana (IHSAA) - Stub

**Estimated Time**: 3-4 hours per state × 10-15 states = 30-60 hours

**Priority**: P3 - MaxPreps covers most of this

**Recommendation**: Only implement if MaxPreps coverage gaps found in key states

---

## Infrastructure Improvements

### 12. Update Validation Script for Competition-Based Sources
**Impact**: Properly test FIBA, ANGT, and other competition-based sources

**Current Issue**: Validation assumes `search_players()` works standalone, but some sources require competition_id

**Fix Needed**:
- Add `--competition-id` argument to validation script
- Detect competition-based sources and skip validation or use sample competition
- Update test framework

**Estimated Time**: 2-3 hours

**Priority**: P2 - Enables proper validation

---

### 13. Enhance Error Handling and Retry Logic
**Impact**: More resilient scraping

**Improvements Needed**:
- Exponential backoff for network failures
- Better timeout handling
- Graceful degradation (return partial data instead of failing completely)
- Retry on transient errors (502, 503, timeouts)

**Estimated Time**: 4-6 hours

**Priority**: P3 - Quality of life

---

### 14. Create MCP Server Integration
**Impact**: Expose datasources via Model Context Protocol

**What To Build**:
- MCP server wrapper around datasource aggregator
- Expose tools for:
  - `search_players(name, filters)`
  - `get_player_stats(player_id, season)`
  - `get_recruiting_profile(player_id)`
- Connect to Claude Desktop

**Estimated Time**: 6-10 hours

**Priority**: P3 - Nice to have for demo

---

## Summary by Time Investment

| Task | Priority | Time Est. | Impact |
|------|----------|-----------|--------|
| Fix circular import | P0 | 2-4 hrs | Unblocks all testing |
| Validate MaxPreps | P0 | 1-2 hrs | +51 states coverage |
| Implement CA state source | P1 | 4-6 hrs | +15% D1 coverage |
| Implement TX state source | P1 | 4-6 hrs | +12% D1 coverage |
| Implement FL state source | P1 | 4-6 hrs | +8% D1 coverage |
| Validate UAA/3SSB | P1 | 2-4 hrs | Elite player coverage |
| Test historical data | P2 | 3-5 hrs | ML training ready |
| Automate health monitoring | P2 | 1 hr | Prevent breakage |
| Validate Europe sources | P3 | 6-10 hrs | International coverage |
| Build MCP server | P3 | 6-10 hrs | Demo/integration |

**Critical Path** (P0 + P1): ~20-30 hours → 60-70% D1 coverage

**Full Implementation** (P0-P3): ~100-150 hours → 80-90% coverage

---

## Realistic Goals

### This Week (5-10 hours)
1. ✅ Fix circular import (P0)
2. ✅ Validate MaxPreps (P0)
3. ✅ Validate 2-3 grassroots circuits (P1)

**Result**: Core US coverage operational

### This Month (20-30 hours)
4. ✅ Implement CA, TX, FL state sources (P1)
5. ✅ Test historical data retrieval (P2)
6. ✅ Set up health monitoring automation (P2)

**Result**: 60-70% D1 coverage, historical data ready for ML

### Next Quarter (50-75 hours)
7. ✅ Validate all grassroots circuits (P1)
8. ✅ Implement IL, NY, GA, PA state sources (P1)
9. ✅ Validate Europe sources (P3)
10. ✅ Build MCP server integration (P3)

**Result**: 80-90% coverage, full international support, MCP demo ready

---

## Current Blockers

1. **Circular Import** - Blocks all pytest testing
2. **PSAL Backend Service** - Broken/deprecated SportDisplay.svc (external dependency, cannot fix)
3. **ToS Compliance** - MaxPreps, 247Sports, ESPN require legal review or CSV import alternative

**Actionable This Week**: Fix #1, use CSV import for #3

---

## Next Steps (Immediate)

1. **Fix circular import** - Top priority, unblocks everything
2. **Validate MaxPreps** - Quick win, huge coverage impact
3. **Run coverage dashboard** - Measure baseline with example cohort
4. **Implement CA state source** - Biggest single-state coverage boost

**Command to run after circular import fix**:
```bash
# Validate MaxPreps
python scripts/validate_datasources.py --source maxpreps --verbose

# Measure coverage with example cohort
python scripts/dashboard_coverage.py --cohort data/college_cohort_example.csv

# If good, proceed with state sources
```

---

**See also**:
- `docs/DATASOURCE_INVENTORY.md` - Full datasource documentation
- `docs/QUICKSTART.md` - 30-minute weekend measurement plan
- `docs/COVERAGE_WORKFLOW.md` - Complete coverage improvement workflow
- `PROJECT_LOG.md` - Session history and changes
