# Basketball Data Coverage Analysis & Gap Report
**Generated**: 2025-11-11
**Project**: hs_bball_players_mcp
**Purpose**: Comprehensive audit of US state coverage + global pre-Euroleague leagues

---

## Executive Summary

**Current Active Adapters**: 10 (3 national circuits, 2 multi-state, 3 single-state, 2 global)
**US States Covered**: 13 of 50 (26% coverage)
**US States Missing**: 37 + DC (74% gap)
**Global Pre-College**: 2 active (FIBA Youth, FIBA LiveStats), 5 planned (ANGT, NBBL, FEB, OSBA, PlayHQ)

---

## PART 1: UNITED STATES COVERAGE

### 1.1 Currently Covered States (13 total)

| State | Platform(s) | Status | Data Quality | Notes |
|-------|-------------|--------|--------------|-------|
| **AZ** | SBLive | Active | High | Box scores, player pages |
| **CA** | SBLive | Active | High | CIF sections, comprehensive |
| **IA** | Bound | Active | High | Flagship state, excellent coverage |
| **ID** | SBLive | Active | High | Full stats |
| **IL** | Bound | Active | High | Player pages, box scores |
| **MN** | MN Hub, Bound | Active | High | Best free HS stats in US |
| **NV** | SBLive | Active | High | Full coverage |
| **NY** | PSAL | Active | Medium | NYC public schools only |
| **OR** | SBLive | Active | High | OSAA partnership |
| **SD** | Bound | Active | High | Complete coverage |
| **WA** | SBLive | Active | High | WIAA partnership, comprehensive |
| **WI** | WSN | Active | High | Deep stats, similar to MN Hub |
| **National** | EYBL, EYBL Girls, 3SSB | Active | High | Grassroots circuits |

### 1.2 Missing States by Region (37 + DC)

#### Northeast (10 states) - HIGH PRIORITY
**Missing**: CT, DE, MA, MD, ME, NH, NJ, PA, RI, VT

**Recommended Platforms**:
1. **MaxPreps** (ToS violation - EXCLUDE)
2. **SBLive/ScoreStream** - Check if expanded to: **NJ, PA, MD**
3. **State Association Sites**:
   - **PA**: PIAA.org (schedules only, no stats)
   - **NJ**: NJSIAA.org (limited stats)
   - **MA**: MIAA.net (tournaments, limited stats)
   - **MD**: MPSSAA.org (schedules)
   - **CT**: CIAC.org (schedules, tournaments)
4. **Northeast Prep Leagues**:
   - **NEPSAC** (New England Prep): nepsac.org - Elite prep schools
   - **ISL** (Independent School League): bostonglobe.com/sports/high-schools/isl

**Action Items**:
- [ ] Research SBLive expansion to NJ/PA/MD
- [ ] Create NEPSAC adapter for prep schools (CT, MA, NH, VT, ME, RI)
- [ ] Evaluate state association APIs for CT, NJ, PA, MD, MA

#### Southeast (11 states) - HIGH PRIORITY (Basketball hotbed)
**Missing**: AL, AR, FL, GA, KY, LA, MS, NC, SC, TN, VA, WV

**Recommended Platforms**:
1. **SBLive/ScoreStream** - Check expansion to: **FL, GA, NC, VA, TN**
2. **Bound** - May have expanded to: **KY (already in registry!), TN, VA**
3. **RankOne** - Already covers: **KY, TN (in registry)** - schedules only
4. **State-Specific Hubs**:
   - **FL**: FHSAA.org + FloridaHSFootball.com (check basketball section)
   - **GA**: GHSA.net + GPB Sports (Georgia Public Broadcasting)
   - **NC**: NCHSAA.org + MaxPreps (ToS issue)
   - **VA**: VHSL.org + VirginiaPreps.com
   - **TX**: UIL.org + TexasHoops.com
   - **TN**: TSSAA.org
   - **AL**: AHSAA.com
   - **SC**: SCHSL.org
   - **KY**: KHSAA.org
   - **LA**: LHSAA.org
   - **MS**: MHSAA.com

**Action Items**:
- [ ] Research SBLive/Bound expansion to FL, GA, NC, VA, TN, SC
- [ ] Create state hub adapters for FL (FHSAA/FloridaHSFootball)
- [ ] Create state hub adapters for GA (GPB Sports)
- [ ] Create state hub adapters for NC (NCHSAA if stats available)
- [ ] Create state hub adapters for VA (VirginiaPreps)
- [ ] Verify RankOne coverage for KY, TN (already in registry)

#### Midwest (6 states)
**Missing**: IN, KS, MI, MO, ND, NE, OH
**Covered**: IA, IL, MN, SD, WI

**Recommended Platforms**:
1. **RankOne** - Already covers: **IN, OH (in registry!)** - schedules only
2. **Bound** - May have expanded to: **NE, KS, MO**
3. **SBLive** - Check expansion
4. **State-Specific Hubs**:
   - **MI**: MHSAA.com + DetroitPAL.org
   - **OH**: OHSAA.org + Stark County stats sites
   - **IN**: IHSAA.org
   - **MO**: MSHSAA.org
   - **KS**: KSHSAA.org
   - **NE**: NSAA.org
   - **ND**: NDHSAA.com

**Action Items**:
- [ ] Verify RankOne coverage for IN, OH
- [ ] Research Bound expansion to NE, KS, MO
- [ ] Create MI adapter (MHSAA + DetroitPAL)
- [ ] Evaluate state association sites for stats availability

#### Southwest (5 states) - HIGH PRIORITY (Texas!)
**Missing**: CO, NM, OK, TX, UT
**Covered**: AZ

**Recommended Platforms**:
1. **RankOne** - Already covers: **TX (in registry!)** - schedules only
2. **SBLive** - May cover: **CO, UT**
3. **Texas-Specific**:
   - **TexasHoops.com** - Comprehensive coverage (check robots.txt)
   - **UIL.org** - Schedules, tournaments
   - **MaxPreps** (ToS violation - exclude)
4. **State Hubs**:
   - **CO**: CHSAA.org + ColoradoPreps.com
   - **UT**: UHSAA.org
   - **NM**: NMAA.org
   - **OK**: OSSAA.com

**Action Items**:
- [ ] Create TexasHoops adapter (HIGH PRIORITY - largest state)
- [ ] Verify RankOne TX coverage
- [ ] Research SBLive expansion to CO, UT
- [ ] Evaluate ColoradoPreps.com for CO coverage

#### West (5 states)
**Missing**: AK, HI, MT, WY
**Covered**: WA, OR, CA, ID, NV

**Recommended Platforms**:
1. **State Association Sites**:
   - **AK**: ASAA.org (limited coverage expected)
   - **HI**: HHSAA.org + OIA (Oahu Interscholastic Association)
   - **MT**: MHSA.org
   - **WY**: WHSAA.org
2. **SBLive** - Check if covers MT, WY

**Priority**: LOW (smaller populations, limited coverage expected)

**Action Items**:
- [ ] Research HI coverage (OIA may have stats)
- [ ] Low priority: AK, MT, WY (population-based decision)

---

## PART 2: PLATFORM EXPANSION OPPORTUNITIES

### 2.1 SBLive Expansion Research Needed

**Currently Covered**: WA, OR, CA, AZ, ID, NV (6 states)

**Potential Additional States** (based on SBLive's typical coverage):
- [ ] Check: **AL, CO, FL, GA, IN, LA, MS, MT, NC, ND, NE, NJ, NM, OK, PA, SC, TN, TX, UT, VA, WY**

**Action**: Visit sblive.com and enumerate all state subdomains

### 2.2 Bound Expansion Research Needed

**Currently Covered**: IA, SD, IL, MN (4 states)

**Potential Additional States**:
- [ ] Check: **KS, MO, NE, WI** (Midwest expansion)
- [ ] Check: **IN, OH, MI** (Great Lakes region)

**Action**: Visit bound.com and check state subdomain availability

### 2.3 RankOne Verification

**In Registry**: TX, KY, IN, OH, TN (5 states)

**Capabilities**: Schedules/results only, NO player stats

**Action**:
- [ ] Verify district coverage for all 5 states
- [ ] Use as "glue layer" for entity resolution (team names, schedules)
- [ ] Do NOT use for player stats (not available)

---

## PART 3: GLOBAL PRE-COLLEGE COVERAGE

### 3.1 Currently Active (2)

| Source | Region | Coverage | Status | Notes |
|--------|--------|----------|--------|-------|
| **FIBA Youth** | Global | U16/U17/U18 World Champs | Active | Official FIBA competitions |
| **FIBA LiveStats** | Global | Any FIBA LiveStats v7 tournament | Active | JSON API, works globally |

### 3.2 Europe - Planned (5 sources)

#### High Priority

1. **ANGT (Adidas Next Generation Tournament)**
   - **Status**: Template (needs URL updates)
   - **Coverage**: EuroLeague U18 elite tournament
   - **Data**: Full box scores, PIR stats, player profiles
   - **Action**: Update URLs in template, activate adapter

2. **NBBL (Germany)**
   - **Status**: Planned
   - **Coverage**: NBBL U19 + JBBL U16 (German youth leagues)
   - **URL**: nbbl-basketball.de
   - **Data**: Official stats portals (German/English)
   - **Action**: Create adapter following SBLive/Bound patterns

3. **FEB Competiciones (Spain)**
   - **Status**: Planned
   - **Coverage**: Spanish junior categories (U14-U19)
   - **URL**: competitions.feb.es
   - **Data**: Per-game and season stats
   - **Action**: Create adapter with Spanish league structure

#### Medium Priority

4. **MKL (Lithuania)**
   - **Status**: Not in registry - NEEDS RESEARCH
   - **Coverage**: Lithuanian youth leagues
   - **URL**: Research needed (likely lkl.lt or krepsinis.net)
   - **Action**: Research official Lithuanian basketball federation youth leagues

5. **LNB Espoirs (France)**
   - **Status**: Not in registry - NEEDS RESEARCH
   - **Coverage**: French U21 league
   - **URL**: Research needed (likely lnb.fr/espoirs)
   - **Action**: Research LNB (Ligue Nationale de Basket) youth structure

#### Additional European Opportunities

6. **BallinEurope Youth Coverage**
   - Multi-country aggregator - check for stats availability

7. **RealGM International**
   - Check youth tournament coverage

8. **Country-Specific Youth Leagues**:
   - **Italy**: FIP youth leagues (federbasket.it)
   - **Greece**: Greek youth leagues (basket.gr)
   - **Serbia**: KSS youth leagues (kss.rs)
   - **Turkey**: TBF youth leagues (tbf.org.tr)

**Action Items**:
- [ ] Research MKL (Lithuania) official sources
- [ ] Research LNB Espoirs (France) official sources
- [ ] Activate ANGT template (update URLs)
- [ ] Create NBBL adapter (Germany)
- [ ] Create FEB adapter (Spain)
- [ ] Survey Italian, Greek, Serbian, Turkish youth leagues for stats availability

### 3.3 Canada - Planned (2 sources)

1. **OSBA (Ontario Scholastic Basketball Association)**
   - **Status**: Template (needs URL updates)
   - **Coverage**: U17/U19/Prep divisions (Ontario)
   - **URL**: osba.ca
   - **Data**: Box scores, season stats
   - **Action**: Update URLs in template, activate adapter

2. **NPA (National Preparatory Association)**
   - **Status**: Planned
   - **Coverage**: Canadian prep league
   - **URL**: npaleague.com
   - **Data**: Scores-first (stats vary year-to-year)
   - **Action**: Create scores/schedules adapter (stats optional)

#### Additional Canadian Opportunities

3. **OBL (Ontario Basketball League)**
   - U17/U19 provincial league
   - Research: ontariobasketball.ca

4. **Provincial Associations**:
   - **BC**: Basketball BC (basketballbc.ca)
   - **AB**: Basketball Alberta (basketballalberta.ca)
   - **QC**: Basketball Québec (basketball.qc.ca)

**Action Items**:
- [ ] Activate OSBA template (update URLs)
- [ ] Create NPA adapter (schedules focus)
- [ ] Research provincial associations for stats availability

### 3.4 Australia - Planned (1 source)

1. **PlayHQ**
   - **Status**: Template (needs URL updates)
   - **Coverage**: National platform (U16/U18 Championships, state leagues)
   - **URL**: playhq.com
   - **Data**: Player pages, season stats, box scores
   - **Action**: Update URLs in template, activate adapter

#### Additional Australian Opportunities

2. **Basketball Australia Official**
   - U17 Nationals, U19 Nationals
   - Research: basketball.net.au

3. **State Associations**:
   - **VIC**: Basketball Victoria
   - **NSW**: Basketball NSW
   - **QLD**: Basketball Queensland

**Action Items**:
- [ ] Activate PlayHQ template (update URLs)
- [ ] Research Basketball Australia national championships

### 3.5 Asia-Pacific - Needs Research

**Potential Sources**:
1. **FIBA Asia Youth Championships** - Use FIBA LiveStats adapter
2. **Philippines**: UAAP/NCAA junior leagues
3. **Japan**: JBA youth leagues
4. **South Korea**: KBA youth leagues
5. **China**: CBA youth development leagues (likely restricted)
6. **New Zealand**: Basketball NZ youth leagues

**Priority**: LOW initially, focus on US/Europe/Canada/Australia first

---

## PART 4: ONE-OFF EVENT ADAPTERS

### 4.1 Currently Planned (3 in registry)

1. **NBPA Top 100 Camp**
   - **URL**: top100camp.com
   - **Data**: PDF box scores, leaderboards
   - **Action**: Create PDF parser adapter

2. **Pangos All-American Camp**
   - **URL**: pangosallamericancamp.com
   - **Data**: HTML leaderboards
   - **Action**: Create HTML scraper adapter

3. **Section 7** - Not in registry
   - **Action**: Research and add to registry

### 4.2 Additional High-Value Events

4. **Nike Hoop Summit**
   - International vs USA showcase
   - Research: hoopsummit.com

5. **Jordan Brand Classic**
   - Elite all-star game
   - Research: jordanclassic.com

6. **McDonald's All-American Game**
   - Top HS seniors
   - Research: mcdaag.com

7. **NBPA Top 100 Camp**
   - Already in registry, needs implementation

**Action Items**:
- [ ] Create event adapter template (reusable for all one-off events)
- [ ] Implement NBPA Top 100 PDF parser
- [ ] Implement Pangos HTML scraper
- [ ] Research Section 7, Hoop Summit, Jordan Classic, McDonald's AA

---

## PART 5: IMPLEMENTATION PRIORITY MATRIX

### Phase 1: High-ROI Multi-State Platforms (Sprint 1) - PARTIALLY COMPLETE

**Status**: SBLive, Bound, WSN adapters ACTIVE (need sources.yaml status update)

**Remaining**:
1. [ ] **RankOne adapter** (TX, KY, IN, OH, TN) - Schedules only, entity resolution layer
2. [ ] Update sources.yaml status: sblive, bound, wsn → "active"

### Phase 2: Southeast Expansion (Sprint 2) - HIGHEST PRIORITY

**Why**: Basketball hotbed, 11 missing states, large talent pool

1. [ ] **Research SBLive/Bound expansion** to FL, GA, NC, VA, TN, SC, KY
2. [ ] **Create TexasHoops adapter** (TX coverage - largest state)
3. [ ] **Create state hub adapters**: FL, GA, NC, VA
4. [ ] **Verify RankOne** coverage for KY, TN

### Phase 3: Template Activation (Sprint 3)

**Why**: Already coded, just need URL updates

1. [ ] **ANGT** - Update URLs, activate (Europe U18 elite)
2. [ ] **OSBA** - Update URLs, activate (Ontario)
3. [ ] **PlayHQ** - Update URLs, activate (Australia)
4. [ ] **OTE** - Update URLs, activate (US prep)
5. [ ] **Grind Session** - Update URLs, activate (US prep)

### Phase 4: European Youth Leagues (Sprint 4)

1. [ ] **NBBL adapter** (Germany U19/U16)
2. [ ] **FEB adapter** (Spain juniors)
3. [ ] **Research & add**: MKL (Lithuania), LNB Espoirs (France)

### Phase 5: Event Adapters (Sprint 5)

1. [ ] **Event adapter template** (reusable)
2. [ ] **NBPA Top 100** PDF parser
3. [ ] **Pangos** HTML scraper
4. [ ] **Nike Hoop Summit, Jordan Classic, McDonald's AA**

### Phase 6: Northeast Expansion (Sprint 6)

1. [ ] **NEPSAC adapter** (New England prep schools)
2. [ ] **State hubs**: NJ, PA, MA, MD, CT

### Phase 7: Remaining Gaps (Sprint 7+)

1. [ ] Midwest: MI, MO, KS, NE, ND
2. [ ] Southwest: CO, UT, NM, OK
3. [ ] West: HI (OIA), AK, MT, WY (low priority)

---

## PART 6: ENGINEERING UPGRADES NEEDED

### 6.1 Source Registry Enhancement ✅ COMPLETE

- [x] Created sources.yaml with 26+ sources
- [x] Created source_registry.py service
- [ ] **Update sources.yaml**: Change sblive, bound, wsn, fiba_livestats → "active"

### 6.2 Identity Resolution System

**Status**: Drafted, needs integration

**Requirements**:
- player_uid = (name, school, grad_year)
- Fuzzy matching for name variations
- In-memory cache for performance
- Manual override table for known duplicates

**Action**:
- [ ] Wire identity resolution through aggregator
- [ ] Add player_uid to all Player objects
- [ ] Create manual override CSV (data/identity_overrides.csv)

### 6.3 School Dictionary (NCES Integration)

**Purpose**: Normalize US school names across sources

**Requirements**:
- NCES school ID mapping (district + school codes)
- RankOne, SBLive, Bound entities should resolve to same NCES ID
- Fallback: fuzzy matching when NCES ID unavailable

**Action**:
- [ ] Download NCES public school directory
- [ ] Create school normalization service
- [ ] Add nces_school_id to Player model (optional field)

### 6.4 Event Lineage (Auditability)

**Status**: Partial (fetched_at, source_url exist)

**Action**:
- [ ] Make fetched_at and source_url MANDATORY for all new adapters
- [ ] Add last_updated_at for data refresh tracking
- [ ] Store raw_data hash for change detection

### 6.5 Adapter Testing & Enablement

**Current**: 10 active adapters with tests

**Needed**:
- [ ] Implement selectors for 5 templates (OTE, Grind Session, ANGT, OSBA, PlayHQ)
- [ ] Create tests for each new adapter
- [ ] API smoke tests for all endpoints

### 6.6 Historical Backfill & Persistence

**Status**: DuckDB + Parquet implemented, upserts working

**Action**:
- [ ] Season enumeration logic (backfill 2020-2024)
- [ ] Backfill CLI command: `python -m src.cli backfill --source=sblive --seasons=2020-2024`
- [ ] Progress tracking in DuckDB

---

## PART 7: SPECIFIC RESEARCH TASKS

### Immediate Research (Next 48 Hours)

1. [ ] **SBLive state enumeration**: Visit sblive.com, list all state subdomains
2. [ ] **Bound state enumeration**: Visit bound.com, list all state subdomains
3. [ ] **RankOne verification**: Log in to rankone.com, verify TX/KY/IN/OH/TN district coverage
4. [ ] **TexasHoops.com**: Check robots.txt, evaluate stats structure, ToS review
5. [ ] **ANGT URLs**: Visit euroleaguebasketball.net/next-generation, document current URL structure
6. [ ] **OSBA URLs**: Visit osba.ca, document stats/schedule endpoints
7. [ ] **PlayHQ URLs**: Visit playhq.com, document org structure and API patterns

### Secondary Research (Next Week)

1. [ ] **Southeast state hubs**: FL, GA, NC, VA - evaluate official and third-party stats sites
2. [ ] **NBBL**: Visit nbbl-basketball.de, document stats structure (German/English)
3. [ ] **FEB**: Visit competitions.feb.es, document API or scraping structure
4. [ ] **MKL (Lithuania)**: Research official Lithuanian basketball youth leagues
5. [ ] **LNB Espoirs (France)**: Research French U21 league structure

### Long-term Research (Next Month)

1. [ ] **NEPSAC**: New England prep school stats availability
2. [ ] **Midwest state hubs**: MI, MO, KS, NE research
3. [ ] **Canadian provincial associations**: BC, AB, QC stats availability
4. [ ] **Asian leagues**: Philippines (UAAP), Japan (JBA), South Korea (KBA)

---

## PART 8: CONCRETE NEXT STEPS (Ordered by Priority)

### Immediate (Today/Tomorrow)

1. [ ] **Update sources.yaml status**: sblive, bound, wsn, fiba_livestats → "active"
2. [ ] **Research SBLive expansion**: Enumerate all state subdomains
3. [ ] **Research Bound expansion**: Enumerate all state subdomains
4. [ ] **Create RankOne adapter** (schedules/fixtures only, 5 states)

### Short-term (This Week)

5. [ ] **Research TexasHoops.com** (evaluate for TX coverage)
6. [ ] **Update ANGT template** (URL research + activation)
7. [ ] **Update OSBA template** (URL research + activation)
8. [ ] **Update PlayHQ template** (URL research + activation)
9. [ ] **Create NBBL adapter** (Germany)
10. [ ] **Create FEB adapter** (Spain)

### Medium-term (Next 2 Weeks)

11. [ ] **Southeast state hub research** (FL, GA, NC, VA)
12. [ ] **Create event adapter template** (reusable)
13. [ ] **Implement NBPA Top 100** (PDF parser)
14. [ ] **Implement Pangos** (HTML scraper)
15. [ ] **Wire identity resolution** through aggregator

### Long-term (Next Month)

16. [ ] **NEPSAC adapter** (New England prep)
17. [ ] **Midwest expansion** (MI, MO, KS, NE)
18. [ ] **School dictionary** (NCES integration)
19. [ ] **Historical backfill CLI** (season enumeration)
20. [ ] **Canadian provincial adapters**

---

## PART 9: COVERAGE GOALS

### Minimum Viable Coverage (MVP)

- [x] **US**: 3+ states with high-quality stats (DONE: 13 states)
- [x] **US Circuits**: 2+ national circuits (DONE: 3 circuits)
- [x] **Global**: FIBA coverage (DONE: 2 FIBA sources)
- [ ] **Europe**: 2+ youth leagues (PLANNED: ANGT, NBBL)
- [ ] **Canada**: 1+ source (PLANNED: OSBA)
- [ ] **Australia**: 1+ source (PLANNED: PlayHQ)

### Target Coverage (Next 3 Months)

- [ ] **US**: 25+ states (50% coverage)
- [ ] **US Circuits**: 5+ circuits (add UAA, OTE active)
- [ ] **Europe**: 5+ youth leagues (ANGT, NBBL, FEB, MKL, LNB)
- [ ] **Canada**: 3+ sources (OSBA, NPA, provincial)
- [ ] **Australia**: 2+ sources (PlayHQ, Basketball Australia)
- [ ] **Events**: 5+ showcase events (NBPA, Pangos, Hoop Summit, Jordan, McDonald's)

### Aspirational Coverage (6-12 Months)

- [ ] **US**: 45+ states (90% coverage)
- [ ] **Europe**: 10+ countries with youth league coverage
- [ ] **Asia-Pacific**: 3+ countries (Philippines, Japan, South Korea)
- [ ] **South America**: Research basketball hotbeds (Brazil, Argentina)
- [ ] **Africa**: Research basketball growth markets (Nigeria, Senegal)

---

## APPENDIX A: Platform Capabilities Matrix

| Platform | States/Coverage | Stats | Box Scores | Player Pages | Schedules | Standings |
|----------|----------------|-------|------------|--------------|-----------|-----------|
| **SBLive** | 6+ states | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Bound** | 4+ states | ✅ | ✅ | ✅ | ✅ | ✅ |
| **WSN** | WI only | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MN Hub** | MN only | ✅ | ❌ | ✅ | ✅ | ❌ |
| **PSAL** | NYC only | ✅ | ❌ | ❌ | ✅ | ✅ |
| **RankOne** | 5 states | ❌ | ❌ | ❌ | ✅ | ❌ |
| **EYBL** | National | ✅ | ❌ | ❌ | ✅ | ✅ |
| **3SSB** | National | ✅ | ❌ | ❌ | ✅ | ✅ |
| **FIBA** | Global | ✅ | ✅ | ❌ | ✅ | ✅ |
| **ANGT** | Europe U18 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **NBBL** | Germany | ✅ | ✅ | ✅ | ✅ | ✅ |
| **FEB** | Spain | ✅ | ✅ | ✅ | ✅ | ✅ |
| **OSBA** | Ontario | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PlayHQ** | Australia | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## APPENDIX B: State Coverage Heatmap

```
COVERAGE STATUS:
✅ Full Coverage (stats + box scores)
🟡 Partial Coverage (schedules/fixtures only)
❌ No Coverage

Northeast:
CT ❌  DE ❌  MA ❌  MD ❌  ME ❌  NH ❌  NJ ❌  NY 🟡  PA ❌  RI ❌  VT ❌

Southeast:
AL ❌  AR ❌  FL ❌  GA ❌  KY 🟡  LA ❌  MS ❌  NC ❌  SC ❌  TN 🟡  VA ❌  WV ❌

Midwest:
IA ✅  IL ✅  IN 🟡  KS ❌  MI ❌  MN ✅  MO ❌  ND ❌  NE ❌  OH 🟡  SD ✅  WI ✅

Southwest:
AZ ✅  CO ❌  NM ❌  OK ❌  TX 🟡  UT ❌

West:
AK ❌  CA ✅  HI ❌  ID ✅  MT ❌  NV ✅  OR ✅  WA ✅  WY ❌

National Circuits:
EYBL ✅  EYBL Girls ✅  3SSB ✅  UAA 🟡  OTE 🟡  Grind Session 🟡
```

---

**End of Coverage Analysis**
**Total Research Tasks Identified**: 50+
**Total Implementation Tasks Identified**: 40+
**Next Update**: After SBLive/Bound enumeration research
