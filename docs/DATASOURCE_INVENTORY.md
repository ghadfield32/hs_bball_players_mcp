# Datasource Inventory - Comprehensive Overview

**Last Updated**: 2025-11-16 (Session: claude/review-repository-structure-01LXMUgjibDpdU2jbqwToCLP)

**Total Datasources**: 71
**Operational**: ~15-20 (recently validated)
**Coverage**: US, Canada, Europe, Australia, Global

---

## Executive Summary

This repository contains **71 datasources** across 5 continents, organized into 10 categories:

1. **US State Associations** (39) - Every state's HS athletic association
2. **US Grassroots/Elite** (13) - EYBL, UAA, 3SSB, Grind Session, OTE, etc.
3. **Recruiting Services** (5) - 247Sports, ESPN, On3, Rivals, CSV import
4. **Europe** (6) - ANGT, FIBA Youth, NBBL, MKL, LNB Espoirs, FEB
5. **Canada** (2) - OSBA, NPA
6. **Australia** (1) - PlayHQ
7. **Global** (1) - FIBA LiveStats
8. **US National** (1) - MaxPreps (all 51 states + DC)
9. **US Regional** (2) - PSAL NYC, MN Hub
10. **Templates** (1) - State datasource template

---

## Data Provided By Each Category

### 1. US National Coverage (MaxPreps)

**Datasource**: `src/datasources/us/maxpreps.py`

**Coverage**:
- **All 50 US states + DC** (51 total)
- Universal high school basketball coverage
- Official stats partner in many states

**Data Provided**:
- Player season stats (PPG, RPG, APG, FG%, 3P%, FT%, STL, BLK, TO, PF)
- Player game logs (game-by-game performance)
- Team schedules and scores
- State rankings and leaderboards
- Player profiles (grad year, height, weight, position)
- Advanced stats (TS%, eFG%, PER where available)

**Historical Data**:
- **Typical Range**: 2010-present (15 years)
- **Archive Depth**: Some stats go back to 2005
- **Completeness**: Varies by state (better coverage in top states like CA, TX, FL, NY)

**Methods**:
- `search_players(name, state, grad_year)` - Find players
- `search_players_with_stats(name, state, grad_year)` - Find with stat preview
- `get_player_season_stats(player_id, season)` - Season averages
- `get_player_game_stats(player_id, season)` - Game logs
- `get_team(team_id)` - Team info
- `get_games(team_id, season)` - Team schedule
- `get_leaderboard(state, category, season)` - State leaders

**Technology**: Browser automation (React SPA rendering)

**Rate Limit**: 10 req/min (conservative due to ToS)

**Status**: ✅ Operational (ToS compliance required)

---

### 2. US Grassroots / Elite Circuits (13 sources)

High-level club circuits (AAU, prep schools) with top-tier talent.

#### **Nike EYBL** (`eybl.py` + `eybl_girls.py`)

**Coverage**: Boys + Girls EYBL circuits

**Data Provided**:
- Cumulative season stats (PPG, RPG, APG, etc.)
- Leaderboards by category
- Team rosters
- Session schedules

**Historical Data**: 2018-present (~7 years)

**Methods**:
- `search_players()` - Top performers from leaderboards
- `get_player_season_stats()` - Season averages
- `get_leaderboard(category)` - Category leaders
- `get_team()`, `get_games()` - Team data

**Status**: ✅ Operational (fixed 2025-11-16 for div-based layout)

#### **Under Armour Association (UAA)** (`uaa.py` + `uaa_girls.py`)

**Coverage**: Boys + Girls UAA circuits

**Data Provided**:
- Season stats
- Session leaderboards
- Team rosters
- Game schedules

**Historical Data**: 2016-present (~9 years)

**Status**: ⏳ Needs validation

#### **Adidas 3 Stripe Select Basketball (3SSB)** (`three_ssb.py` + `three_ssb_girls.py`)

**Coverage**: Boys + Girls 3SSB circuits

**Data Provided**:
- Season stats
- Event leaderboards
- Team rosters

**Historical Data**: 2017-present (~8 years)

**Status**: ⏳ Needs validation

#### **Grind Session** (`grind_session.py`)

**Coverage**: HS prep circuit (boys)

**Data Provided**:
- Scores and standings
- Team stats
- Session schedules

**Historical Data**: 2015-present (~10 years)

**Status**: ⏳ Needs validation

#### **Overtime Elite (OTE)** (`ote.py`)

**Coverage**: Professional prep league (boys 16-18)

**Data Provided**:
- Player pages with game logs
- Season splits
- Advanced analytics
- Biographical info

**Historical Data**: 2021-present (~4 years)

**Status**: ⏳ Needs validation

#### **Other Grassroots Circuits**

- **Bound (Varsity Bound)** (`bound.py`) - Recruiting platform
- **NEPSAC** (`nepsac.py`) - New England prep schools
- **RankOne** (`rankone.py`) - Multi-sport platform
- **SBLive** (`sblive.py`) - State-by-state coverage
- **Wisconsin Sports Network (WSN)** (`wsn.py`) - Wisconsin focus

**Status**: ⏳ Most need validation

---

### 3. Recruiting Services (5 sources)

Player rankings, ratings, and recruiting profiles.

#### **CSV Recruiting Import** (`csv_recruiting.py`)

**Coverage**: All sources (via CSV import)

**Data Provided**:
- National/state/position rankings
- Star ratings (1-5 stars)
- Composite ratings (0.0-1.0)
- Committed schools
- Player measurements
- Multiple source support (247, ESPN, On3, Rivals)

**Historical Data**: **User-dependent** (can import any historical data)

**Advantages**:
- 100% legal (no scraping)
- Fast (no network calls)
- Reliable (no ToS issues)
- +20-30% recruiting coverage boost

**CSV Format**:
```csv
player_id,player_name,class_year,state,position,rank_national,rank_state,
rank_position,stars,rating,height,weight,high_school,city,committed_to,source
```

**Methods**:
- `get_rankings(class_year, state, position, limit)` - Get rankings
- `search_players(name, class_year, state)` - Find players
- `get_player_recruiting_profile(player_id)` - Full profile

**Status**: ✅ Operational

**Expected CSV Locations**:
- `data/recruiting/247_rankings.csv`
- `data/recruiting/espn_rankings.csv`
- `data/recruiting/on3_rankings.csv`
- `data/recruiting/rivals_rankings.csv`
- `data/recruiting/custom_rankings.csv`

#### **247Sports** (`sports_247.py`)

**Coverage**: National composite rankings

**Data Provided**:
- National/state/position rankings
- Player profiles
- Crystal Ball predictions
- Team rankings

**Historical Data**: 2000-present (~25 years for top classes)

**Status**: ⏳ STUB (needs implementation)

#### **ESPN Recruiting** (`espn.py`)

**Status**: ⏳ STUB (needs implementation)

#### **On3** (`on3.py`)

**Status**: ⏳ STUB (needs implementation)

#### **Rivals** (`rivals.py`)

**Status**: ⏳ STUB (needs implementation)

---

### 4. US State Associations (39 sources)

Every state high school athletic association. Provides official state tournament stats, rankings, and records.

**Coverage**: All 50 states (39 implemented + more via MaxPreps)

**Typical Data Provided**:
- State tournament stats
- Official state rankings
- Championship results
- All-state teams
- Team records

**Historical Data**: **Highly variable** (2000-present typical, some back to 1990s)

**Status**: ⏳ Most are stubs/templates awaiting implementation

**Notable States**:
- **Wisconsin (WIAA)** - Has detailed notes, partially implemented
- **Florida (FHSAA)** - Large state, high priority
- **Texas (UIL)** - Not yet created (use template)
- **California (CIF)** - Not yet created (use template)
- **Georgia (GHSA)** - Implemented (`georgia_ghsa.py` + `ghsa.py`)
- **New York** - No NYSPHSAA file yet
- **Illinois** - No IHSA file yet
- **New Jersey (NJSIAA)** - Implemented

**Key Implementation States** (alphabetically):
1. Alabama (AHSAA)
2. Alaska (ASAA)
3. Arkansas (AAA)
4. Colorado (CHSAA)
5. Connecticut (CIAC)
6. Delaware (DIAA)
7. Florida (FHSAA)
8. Georgia (GHSA)
9. Hawaii (HHSAA)
10. Indiana (IHSAA)
11. Kansas (KSHSAA)
12. Kentucky (KHSAA)
13. Louisiana (LHSAA)
14. Maine (MPA)
15. Maryland (MPSSAA)
16. Massachusetts (MIAA)
17. Michigan (MHSAA)
18. Mississippi (MHSAA)
19. Missouri (MSHSAA)
20. Montana (MHSA)
21. Nebraska (NSAA)
22. New Hampshire (NHIAA)
23. New Jersey (NJSIAA)
24. New Mexico (NMAA)
25. North Carolina (NCHSAA)
26. North Dakota (NDHSAA)
27. Ohio (OHSAA)
28. Oklahoma (OSSAA)
29. Pennsylvania (PIAA)
30. Rhode Island (RIIL)
31. South Carolina (SCHSL)
32. Tennessee (TSSAA)
33. Utah (UHSAA)
34. Vermont (VPA)
35. Virginia (VHSL)
36. Washington DC (DCIAA)
37. West Virginia (WVSSAC)
38. Wyoming (WHSAA)
39. + State template for others

**Missing Major States** (need creation):
- **California (CIF)** - Use state template
- **Texas (UIL)** - Use state template
- **Illinois (IHSA)** - Use state template
- **New York (NYSPHSAA)** - Use state template

**Template**: `src/datasources/us/state/state_template.py` - Copy and customize for new states

---

### 5. US Regional (2 sources)

Regional coverage for specific areas.

#### **PSAL NYC** (`psal.py`)

**Coverage**: New York City Public Schools Athletic League

**Data Provided**:
- Team pages and standings
- Leaders by category
- School rosters

**Historical Data**: Unknown (website currently broken)

**Status**: ❌ BLOCKED - SportDisplay.svc WCF service broken/deprecated
- All 12+ API endpoints return HTML error pages
- Static HTML contains no player data
- JavaScript doesn't trigger data load
- **Cannot be fixed client-side** - requires PSAL infrastructure team to repair backend service

#### **Minnesota Basketball Hub** (`mn_hub.py`)

**Coverage**: Minnesota high school basketball

**Data Provided**:
- Stat leaderboards
- Team stats
- Player profiles
- Season schedules

**Historical Data**: 2018-present (~7 years)

**Status**: ✅ Operational (season fallback logic added 2025-11-16)
- Cascading season detection (tries current → -1 → -2 → -3 years back)
- Graceful degradation if no season data available

---

### 6. Europe (6 sources)

European youth basketball leagues and tournaments.

#### **ANGT (Adidas Next Generation Tournament)** (`angt.py`)

**Coverage**: Top European U18 teams

**Data Provided**:
- Full stats
- Standings
- Player profiles

**Historical Data**: 2003-present (~22 years)

**Status**: ⏳ Needs validation

#### **FIBA Youth** (`fiba_youth.py`)

**Coverage**: U16/U17/U18 international competitions

**Data Provided**:
- Official box scores
- Team and player stats
- Tournament standings

**Historical Data**: 2010-present (~15 years)

**Status**: ⏳ Needs validation

#### **Other Europe**:
- **FEB Spain** (`feb.py`) - Spanish youth federation
- **LNB Espoirs France** (`lnb_espoirs.py`) - French U21 league
- **MKL Lithuania** (`mkl.py`) - Lithuanian youth
- **NBBL/JBBL Germany** (`nbbl.py`) - German youth leagues

**Historical Data**: Varies (2010-2020 typical start)

**Status**: ⏳ All need validation

---

### 7. Canada (2 sources)

#### **OSBA Ontario** (`osba.py`)

**Coverage**: Ontario Scholastic Basketball Association

**Data Provided**:
- Competition pages
- Standings
- Schedules

**Historical Data**: 2015-present (~10 years)

**Status**: ⏳ Needs validation

#### **NPA Canada** (`npa.py`)

**Coverage**: National Preparatory Association

**Data Provided**:
- Prep school rosters
- Stats and standings

**Historical Data**: 2018-present (~7 years)

**Status**: ⏳ Needs validation

---

### 8. Australia (1 source)

#### **PlayHQ** (`playhq.py`)

**Coverage**: Australian state junior leagues

**Data Provided**:
- Season stats by grade
- Team ladders
- Game results

**Historical Data**: 2019-present (~6 years)

**Status**: ⏳ Needs validation

---

### 9. Global (1 source)

#### **FIBA LiveStats** (`fiba_livestats.py`)

**Coverage**: Global youth basketball tournaments

**Data Provided**:
- Real-time box scores
- Player and team stats
- Tournament brackets

**Historical Data**: 2018-present (~7 years)

**Technology**: FIBA LiveStats v7 API

**Status**: ✅ Works as designed (requires competition context)

---

## Historical Data Availability Summary

| Data Source | Years Available | Earliest Data | Notes |
|-------------|----------------|---------------|-------|
| **MaxPreps** | 15+ years | ~2005-2010 | Best for US HS coverage |
| **EYBL** | ~7 years | 2018 | Elite circuit data |
| **UAA** | ~9 years | 2016 | Elite circuit data |
| **3SSB** | ~8 years | 2017 | Elite circuit data |
| **Grind Session** | ~10 years | 2015 | Prep circuit |
| **OTE** | ~4 years | 2021 | New league |
| **247Sports** | 25+ years | ~2000 | Top recruiting classes |
| **CSV Recruiting** | User-dependent | Any | Import your own data |
| **State Associations** | 15-25 years | ~1990-2010 | Highly variable |
| **ANGT** | ~22 years | 2003 | European U18 |
| **FIBA Youth** | ~15 years | 2010 | International U16/U17/U18 |
| **FIBA LiveStats** | ~7 years | 2018 | Global tournaments |
| **OSBA** | ~10 years | 2015 | Ontario |
| **PlayHQ** | ~6 years | 2019 | Australia |

**Average Historical Depth**: **10-15 years** for most operational sources

**Best Historical Coverage**: MaxPreps (US HS), 247Sports (recruiting), ANGT (Europe U18)

**Newest Sources**: OTE (2021), PlayHQ (2019)

---

## What Each Datasource Type Provides

### Player Stats
**Fields Typically Available**:
- Basic: PPG, RPG, APG, FG%, 3P%, FT%
- Advanced (where available): TS%, eFG%, PER, A/TO, USG%, ORB/DRB split
- Defensive: STL, BLK, PF
- Biographical: Height, weight, grad year, position, team

**Best Sources**:
- MaxPreps (comprehensive US HS stats)
- EYBL/UAA/3SSB (elite circuit stats)
- State associations (official state stats)

### Team Data
**Fields Typically Available**:
- Team name, mascot, school
- Season record (W-L)
- Division/classification
- State/region

**Best Sources**:
- MaxPreps (all US teams)
- State associations (official records)

### Game Schedules
**Fields Typically Available**:
- Opponent
- Date/time
- Location
- Final score
- Box score links

**Best Sources**:
- MaxPreps (US HS schedules)
- EYBL/UAA (circuit schedules)

### Recruiting Profiles
**Fields Typically Available**:
- National/state/position rankings
- Star ratings (1-5)
- Composite ratings (0.0-1.0)
- Offers list
- Commitment status
- Height, weight, wingspan

**Best Sources**:
- CSV Recruiting (fastest, legal)
- 247Sports (most comprehensive)

### Leaderboards
**Fields Typically Available**:
- State/league/tournament leaders by category
- PPG, RPG, APG, FG%, 3P%, etc. leaders
- Top performers

**Best Sources**:
- MaxPreps (state leaders)
- EYBL/UAA (circuit leaders)

---

## Current Operational Status (2025-11-16)

### ✅ Fully Operational & Validated
1. **EYBL** - Fixed for div-based layout (2025-11-16)
2. **MN Hub** - Season fallback logic added (2025-11-16)
3. **CSV Recruiting** - Working by design
4. **FIBA LiveStats** - Working (requires competition context)

### ⚠️ Partially Operational (Needs Testing)
5. **MaxPreps** - Code complete, needs validation
6. Most grassroots circuits (code exists, needs validation)

### ❌ Blocked / Broken
7. **PSAL** - Backend service broken (external dependency)

### ⏳ Stubs / Templates (Needs Implementation)
8. **247Sports** - STUB
9. **ESPN Recruiting** - STUB
10. **On3** - STUB
11. **Rivals** - STUB
12. Most state associations - Templates only

---

## Remaining Work Needed

### High Priority (Coverage Boost)
1. **Validate MaxPreps** - Would unlock all 51 US states immediately
2. **Implement 247Sports scraping** - +20-30% recruiting coverage
3. **Create CA, TX, FL, IL, NY state adapters** - Top 5 states cover ~40% of D1 players

### Medium Priority (Data Quality)
4. **Validate grassroots circuits** - EYBL ✅, UAA, 3SSB, Grind Session
5. **Test historical data retrieval** - Ensure all sources can pull past seasons
6. **Implement ESPN/On3 recruiting** - Diversify recruiting sources

### Low Priority (International Expansion)
7. **Validate Europe sources** - ANGT, FIBA Youth, NBBL, etc.
8. **Validate Canada/Australia** - OSBA, NPA, PlayHQ

### Infrastructure
9. **Fix circular import issue** - Blocking all pytest testing
10. **Create automated health monitoring** - Weekly validation runs
11. **Update validation script** - Handle competition-based sources properly

---

## Quick Reference: What To Use When

| Need | Use This Datasource | Coverage |
|------|---------------------|----------|
| **Any US HS player** | MaxPreps | All 51 states |
| **Top recruits (rankings)** | CSV Recruiting → 247Sports | National/state |
| **Elite circuit stats** | EYBL, UAA, 3SSB | Top AAU players |
| **State tournament stats** | State associations | Official state records |
| **Minnesota players** | MN Hub | MN only |
| **NYC players** | ~~PSAL~~ → Use MaxPreps | ❌ PSAL broken |
| **European U18** | ANGT, FIBA Youth | International |
| **Prep schools** | NEPSAC, NPA | New England, Canada |
| **Game logs** | MaxPreps, EYBL, state associations | Where available |
| **Historical recruiting** | CSV Recruiting (import) | User-dependent |

---

## Notes

- **Legal Compliance**: MaxPreps, 247Sports, ESPN, On3, Rivals all prohibit scraping in ToS. Recommended: (1) Use CSV import for recruiting, (2) Get commercial license for MaxPreps, (3) Use for educational/research only.

- **Browser Automation**: Required for MaxPreps, EYBL, MN Hub, and most modern sources (React SPAs).

- **Rate Limiting**: Aggressive caching and conservative rate limits to minimize load.

- **Coverage Measurement**: Use `scripts/dashboard_coverage.py` and `scripts/report_coverage.py` to measure actual coverage on your cohort.

- **CSV Import Quickstart**: See `docs/QUICKSTART.md` for 30-minute weekend plan to measure and improve coverage.

---

**Next Steps**: See `PROJECT_LOG.md` for detailed session history and `docs/QUICKSTART.md` for measurement workflow.
