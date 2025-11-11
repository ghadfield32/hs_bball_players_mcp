# Implementation Roadmap: Nationwide US + Global Pre-Euroleague Coverage
**Project**: hs_bball_players_mcp
**Goal**: Comprehensive basketball player stats from all US states + global pre-college leagues
**Current**: 10 active adapters (13 US states, 2 global sources)
**Target**: 25+ US states, 10+ global sources within 3 months

---

## Quick Reference: What's Done, What's Next

### ✅ COMPLETED (Phase 3.6)
- **US National Circuits** (3): Nike EYBL (boys), Nike Girls EYBL, Adidas 3SSB
- **US Multi-State** (2): SBLive (6 states), Bound (4 states)
- **US Single-State** (3): MN Hub, PSAL (NYC), WSN (Wisconsin)
- **Global** (2): FIBA Youth, FIBA LiveStats v7
- **Total Coverage**: 13 US states, 3 national circuits, global tournaments

### 🎯 IMMEDIATE PRIORITIES (Sprint 2)

**Sprint 2 Goals** (This Week):
1. RankOne adapter (TX, KY, IN, OH, TN) - schedules/fixtures layer
2. Research SBLive/Bound state expansion
3. Activate template adapters (ANGT, OSBA, PlayHQ)

**Sprint 3 Goals** (Next Week):
4. TexasHoops adapter (TX full stats)
5. OTE + Grind Session template activation
6. Event adapter framework

**Sprint 4 Goals** (Weeks 3-4):
7. NBBL adapter (Germany)
8. FEB adapter (Spain)
9. Southeast state hub research (FL, GA, NC, VA)

---

## Phase-by-Phase Implementation Plan

### PHASE 2: Platform Expansion (Sprint 2) - IN PROGRESS

**Objective**: Add 5-10 more US states via platform expansion + activate templates

#### Task 2.1: RankOne Adapter (Schedules/Fixtures Layer)
**Priority**: HIGH (enables entity resolution for 5 states)
**Effort**: Medium (3-4 hours)
**Coverage**: TX, KY, IN, OH, TN (schedules only, no player stats)

**Steps**:
1. Research RankOne district structure:
   - [ ] Visit rankone.com, enumerate districts for TX, KY, IN, OH, TN
   - [ ] Document API/URL patterns for schedules
   - [ ] Check robots.txt policy
2. Create adapter skeleton:
   - [ ] Copy template from Bound/SBLive multi-state pattern
   - [ ] Implement: `get_games()`, `get_team()` (schedules only)
   - [ ] NO stats methods (RankOne doesn't provide player stats)
3. Integration:
   - [ ] Add to aggregator (optional, for fixtures enrichment)
   - [ ] Create tests
   - [ ] Update sources.yaml status: planned → active

**Deliverables**:
- `src/datasources/us/rankone.py` (400-500 lines)
- `tests/test_datasources/test_rankone.py`
- Entity resolution layer for 5 states

#### Task 2.2: SBLive State Expansion Research
**Priority**: HIGH (could unlock 10+ more states)
**Effort**: Low (1 hour research)

**Steps**:
1. [ ] Visit sblive.com and enumerate ALL state subdomains
2. [ ] Test URLs: `https://www.sblive.com/{STATE}/basketball`
   - Known working: WA, OR, CA, AZ, ID, NV (6 states)
   - Test: AL, CO, FL, GA, IN, LA, MS, MT, NC, ND, NE, NJ, NM, OK, PA, SC, TN, TX, UT, VA, WY
3. [ ] Document which states have active basketball sections
4. [ ] Update sources.yaml with expanded state list
5. [ ] Update SBLiveDataSource.SUPPORTED_STATES array

**Potential Gain**: +10-15 states (if SBLive has expanded)

#### Task 2.3: Bound State Expansion Research
**Priority**: MEDIUM
**Effort**: Low (30 min research)

**Steps**:
1. [ ] Visit bound.com and test subdomains
2. [ ] Test URLs: `https://www.{STATE}.bound.com/basketball`
   - Known working: IA, SD, IL, MN (4 states)
   - Test: KS, MO, NE, WI, IN, OH, MI
3. [ ] Document active state subdomains
4. [ ] Update sources.yaml and BoundDataSource.SUPPORTED_STATES

**Potential Gain**: +3-6 states

#### Task 2.4: Activate ANGT Template (EuroLeague U18)
**Priority**: MEDIUM (global coverage)
**Effort**: Medium (2-3 hours)

**Steps**:
1. Research current URLs:
   - [ ] Visit euroleaguebasketball.net/next-generation
   - [ ] Document stats page URLs
   - [ ] Document player/team page patterns
   - [ ] Check if LiveStats integration exists
2. Update template:
   - [ ] Update URL constants in src/datasources/europe/angt.py
   - [ ] Test selectors against live site
   - [ ] Update scraping logic if structure changed
3. Activate:
   - [ ] Add to aggregator source_classes
   - [ ] Run integration tests
   - [ ] Update sources.yaml: template → active

**Deliverables**:
- Updated `src/datasources/europe/angt.py`
- Active EuroLeague U18 coverage

#### Task 2.5: Activate OSBA Template (Ontario Prep)
**Priority**: MEDIUM (Canada coverage)
**Effort**: Medium (2-3 hours)

**Steps**:
1. [ ] Visit osba.ca and document current structure
2. [ ] Update URLs in src/datasources/canada/osba.py
3. [ ] Test selectors and update if needed
4. [ ] Add to aggregator, run tests
5. [ ] Update sources.yaml: template → active

**Deliverables**:
- Updated `src/datasources/canada/osba.py`
- Active Ontario prep coverage

#### Task 2.6: Activate PlayHQ Template (Australia)
**Priority**: MEDIUM (Australia coverage)
**Effort**: Medium (2-3 hours)

**Steps**:
1. [ ] Visit playhq.com and document org structure
2. [ ] Identify U16/U18 championship URLs
3. [ ] Update URLs in src/datasources/australia/playhq.py
4. [ ] Test selectors and pagination logic
5. [ ] Add to aggregator, run tests
6. [ ] Update sources.yaml: template → active

**Deliverables**:
- Updated `src/datasources/australia/playhq.py`
- Active Australian youth coverage

---

### PHASE 3: Southeast Expansion (Sprint 3) - NEXT

**Objective**: Add 5-8 Southeast states (basketball hotbed region)

#### Task 3.1: TexasHoops Adapter (TX)
**Priority**: HIGHEST (Texas is largest state, massive talent pool)
**Effort**: High (6-8 hours)

**Steps**:
1. Research:
   - [ ] Visit texashoops.com
   - [ ] Check robots.txt (CRITICAL - respect ToS)
   - [ ] Review Terms of Service for scraping policy
   - [ ] Document stats page structure
   - [ ] Document player profile patterns
   - [ ] Test rate limits (be conservative)
2. Implementation:
   - [ ] Create src/datasources/us/texas_hoops.py
   - [ ] Follow SBLive/WSN pattern (single-state, comprehensive)
   - [ ] Implement all methods: search_players, get_player_season_stats, get_leaderboard, etc.
   - [ ] Add robust rate limiting (start at 15 req/min)
3. Testing & Integration:
   - [ ] Create comprehensive test suite
   - [ ] Add to aggregator
   - [ ] Update sources.yaml: research_needed → active

**Deliverables**:
- `src/datasources/us/texas_hoops.py` (800-1000 lines)
- `tests/test_datasources/test_texas_hoops.py`
- Texas coverage (largest state unlocked!)

**CRITICAL**: Only proceed if robots.txt and ToS allow scraping

#### Task 3.2: Florida State Hub Research
**Priority**: HIGH (large state, talent-rich)
**Effort**: Medium (research + implementation)

**Options to Research**:
1. [ ] SBLive expansion to FL (check if active)
2. [ ] FHSAA.org (Florida High School Athletic Association)
3. [ ] FloridaHSFootball.com (check if has basketball section)
4. [ ] Bound expansion to FL
5. [ ] Third-party FL stats sites

**Next Steps**:
- Research phase first (2-3 hours)
- If good source found, create adapter (6-8 hours)

#### Task 3.3: Georgia State Hub Research
**Priority**: HIGH (talent-rich, Atlanta metro)
**Effort**: Medium

**Options to Research**:
1. [ ] SBLive expansion to GA
2. [ ] GHSA.net (Georgia High School Association)
3. [ ] GPB Sports (Georgia Public Broadcasting basketball coverage)
4. [ ] Bound expansion to GA

#### Task 3.4: North Carolina State Hub Research
**Priority**: MEDIUM-HIGH

**Options**:
1. [ ] SBLive expansion to NC
2. [ ] NCHSAA.org (check stats availability)
3. [ ] Bound expansion to NC

#### Task 3.5: Virginia State Hub Research
**Priority**: MEDIUM

**Options**:
1. [ ] SBLive expansion to VA
2. [ ] VHSL.org + VirginiaPreps.com
3. [ ] Bound expansion to VA

---

### PHASE 4: Template Activation - Prep Circuits (Sprint 3)

#### Task 4.1: Activate OTE Template (Overtime Elite)
**Priority**: MEDIUM (elite prep league)
**Effort**: Medium (3-4 hours)

**Steps**:
1. [ ] Visit overtimeelite.com
2. [ ] Document current stats structure
3. [ ] Update URLs in src/datasources/us/ote.py
4. [ ] Test selectors, update scraping logic
5. [ ] Add to aggregator, test
6. [ ] Update sources.yaml: template → active

#### Task 4.2: Activate Grind Session Template
**Priority**: MEDIUM (elite prep tournaments)
**Effort**: Medium (3-4 hours)

**Steps**:
1. [ ] Visit thegrindsession.com
2. [ ] Document event/tournament structure
3. [ ] Update URLs in src/datasources/us/grind_session.py
4. [ ] Implement event-based scraping (may differ from league pattern)
5. [ ] Add to aggregator, test
6. [ ] Update sources.yaml: template → active

---

### PHASE 5: European Youth Leagues (Sprint 4)

#### Task 5.1: NBBL Adapter (Germany U19/U16)
**Priority**: HIGH (major European youth league)
**Effort**: High (6-8 hours)

**Steps**:
1. Research:
   - [ ] Visit nbbl-basketball.de
   - [ ] Check language options (German/English)
   - [ ] Document league structure (NBBL U19, JBBL U16)
   - [ ] Document stats page patterns
   - [ ] Check robots.txt
2. Implementation:
   - [ ] Create src/datasources/europe/nbbl.py
   - [ ] Handle bilingual content (German primary, English fallback)
   - [ ] Implement full stats methods
3. Testing & Integration:
   - [ ] Create tests
   - [ ] Add to aggregator
   - [ ] Update sources.yaml: planned → active

**Deliverables**:
- `src/datasources/europe/nbbl.py` (800-1000 lines)
- German youth league coverage

#### Task 5.2: FEB Adapter (Spain Junior)
**Priority**: HIGH (major European youth league)
**Effort**: High (6-8 hours)

**Steps**:
1. Research:
   - [ ] Visit competitions.feb.es
   - [ ] Document junior category structure (U14-U19)
   - [ ] Document stats API or scraping patterns
   - [ ] Check if JSON API available (Spanish leagues often have good APIs)
2. Implementation:
   - [ ] Create src/datasources/europe/feb.py
   - [ ] Handle Spanish content
   - [ ] Implement full stats methods
3. Testing & Integration:
   - [ ] Create tests
   - [ ] Add to aggregator
   - [ ] Update sources.yaml: planned → active

**Deliverables**:
- `src/datasources/europe/feb.py`
- Spanish youth league coverage

#### Task 5.3: MKL Research (Lithuania)
**Priority**: MEDIUM
**Effort**: Medium (4-6 hours research + implementation)

**Steps**:
1. [ ] Research Lithuanian basketball federation structure
2. [ ] Find official youth league site (likely lkl.lt or affiliated site)
3. [ ] Document stats availability
4. [ ] If viable, create adapter following NBBL/FEB pattern

#### Task 5.4: LNB Espoirs Research (France U21)
**Priority**: MEDIUM
**Effort**: Medium (4-6 hours research + implementation)

**Steps**:
1. [ ] Visit lnb.fr and find Espoirs section
2. [ ] Document U21 league structure
3. [ ] Check stats availability
4. [ ] If viable, create adapter

---

### PHASE 6: Event Adapters (Sprint 5)

#### Task 6.1: Event Adapter Framework
**Priority**: MEDIUM (enables quick event additions)
**Effort**: Medium (4-5 hours)

**Steps**:
1. Create reusable event adapter base class:
   - [ ] `src/datasources/events/base_event.py`
   - [ ] Handle one-off tournaments vs annual events
   - [ ] Support PDF parsing (for box scores)
   - [ ] Support HTML leaderboards
2. Create event adapter interface:
   - [ ] Different from league adapters (event-scoped, not season-scoped)
   - [ ] Methods: get_event_info(), get_event_participants(), get_event_stats(), get_event_games()

**Deliverables**:
- `src/datasources/events/base_event.py` (base class)
- Reusable framework for all showcase events

#### Task 6.2: NBPA Top 100 Adapter
**Priority**: MEDIUM (elite showcase)
**Effort**: Medium (3-4 hours)

**Steps**:
1. [ ] Visit top100camp.com
2. [ ] Document PDF box score structure
3. [ ] Implement PDF parser (use PyPDF2 or pdfplumber)
4. [ ] Extract player stats from PDFs
5. [ ] Create adapter extending BaseEvent

**Deliverables**:
- `src/datasources/events/nbpa_top100.py`
- PDF parsing capability

#### Task 6.3: Pangos All-American Adapter
**Priority**: MEDIUM
**Effort**: Low-Medium (2-3 hours)

**Steps**:
1. [ ] Visit pangosallamericancamp.com
2. [ ] Document HTML leaderboard structure
3. [ ] Create adapter extending BaseEvent
4. [ ] Scrape leaderboards

**Deliverables**:
- `src/datasources/events/pangos.py`

#### Task 6.4: Additional Event Adapters
**Priority**: LOW (nice-to-have)
**Effort**: 2-3 hours each

**Events to Add**:
- [ ] Nike Hoop Summit (hoopsummit.com)
- [ ] Jordan Brand Classic (jordanclassic.com)
- [ ] McDonald's All-American (mcdaag.com)

Each follows same pattern as NBPA/Pangos.

---

### PHASE 7: Northeast Expansion (Sprint 6)

#### Task 7.1: NEPSAC Adapter (New England Prep)
**Priority**: MEDIUM (covers 6 states)
**Effort**: High (6-8 hours research + implementation)

**Steps**:
1. Research:
   - [ ] Visit nepsac.org
   - [ ] Document prep school basketball structure
   - [ ] Check stats availability (may be limited)
   - [ ] Identify which divisions have stats
2. Implementation:
   - [ ] Create src/datasources/us/nepsac.py
   - [ ] May be schedules/scores focus if stats limited
   - [ ] Cover CT, MA, ME, NH, RI, VT prep schools

**Coverage Gain**: 6 Northeast states (prep school coverage)

#### Task 7.2: New Jersey State Hub
**Priority**: MEDIUM (large state, talent-rich)
**Effort**: Medium

**Options**:
- [ ] Check SBLive expansion to NJ
- [ ] NJSIAA.org (check stats availability)
- [ ] Third-party NJ stats sites

#### Task 7.3: Pennsylvania State Hub
**Priority**: MEDIUM (large state)
**Effort**: Medium

**Options**:
- [ ] Check SBLive expansion to PA
- [ ] PIAA.org (likely schedules only)
- [ ] Third-party PA stats sites

---

### PHASE 8: Engineering Enhancements (Ongoing)

These engineering tasks support all phases above:

#### Task 8.1: Identity Resolution System
**Priority**: HIGH (critical for deduplication)
**Effort**: High (8-10 hours)

**Steps**:
1. Design:
   - [ ] Define player_uid = (name, school, grad_year)
   - [ ] Fuzzy matching algorithm for name variations
   - [ ] In-memory cache for performance
2. Implementation:
   - [ ] Create src/services/identity_resolver.py
   - [ ] Add resolve_player_uid() method
   - [ ] Create manual override CSV (data/identity_overrides.csv)
3. Integration:
   - [ ] Wire through aggregator
   - [ ] Add player_uid to all Player objects
   - [ ] Update DuckDB schema to include player_uid

**Deliverables**:
- Identity resolution service
- Cross-source player deduplication

#### Task 8.2: School Dictionary (NCES Integration)
**Priority**: MEDIUM (improves US school name normalization)
**Effort**: High (10-12 hours)

**Steps**:
1. Data acquisition:
   - [ ] Download NCES public school directory (CSV)
   - [ ] Parse district + school codes
   - [ ] Create school lookup table
2. Implementation:
   - [ ] Create src/services/school_normalizer.py
   - [ ] Implement fuzzy matching for school names
   - [ ] NCES ID resolution
3. Integration:
   - [ ] Add nces_school_id to Player model (optional field)
   - [ ] Wire through US adapters
   - [ ] RankOne/SBLive/Bound entities resolve to same NCES ID

**Deliverables**:
- School normalization service
- Better entity resolution for US players

#### Task 8.3: Event Lineage Enhancement
**Priority**: LOW (nice-to-have for auditability)
**Effort**: Low (2-3 hours)

**Steps**:
1. [ ] Make fetched_at and source_url MANDATORY for all new adapters
2. [ ] Add last_updated_at timestamp
3. [ ] Store raw_data hash for change detection
4. [ ] Update all adapters to include lineage fields

#### Task 8.4: Historical Backfill CLI
**Priority**: MEDIUM (enables historical data collection)
**Effort**: Medium (4-6 hours)

**Steps**:
1. Design:
   - [ ] Season enumeration logic (backfill 2020-2024)
   - [ ] Progress tracking in DuckDB
2. Implementation:
   - [ ] Create src/cli/backfill.py
   - [ ] Command: `python -m src.cli backfill --source=sblive --seasons=2020-2024`
   - [ ] Parallel backfill with rate limiting
3. Testing:
   - [ ] Test backfill for one source
   - [ ] Verify data integrity in DuckDB

---

## Research Task Checklist

### Immediate Research (Next 48 Hours)

- [ ] **RankOne**: Verify district coverage for TX, KY, IN, OH, TN
- [ ] **SBLive**: Enumerate all state subdomains (visit sblive.com)
- [ ] **Bound**: Enumerate all state subdomains (visit bound.com)
- [ ] **TexasHoops**: Check robots.txt + ToS, evaluate structure
- [ ] **ANGT**: Document current URL structure at euroleaguebasketball.net/next-generation
- [ ] **OSBA**: Document structure at osba.ca
- [ ] **PlayHQ**: Document org structure at playhq.com

### Secondary Research (Next Week)

- [ ] **Southeast state hubs**: FL, GA, NC, VA - evaluate official + third-party sites
- [ ] **NBBL**: Visit nbbl-basketball.de, document structure
- [ ] **FEB**: Visit competitions.feb.es, check for JSON API
- [ ] **MKL**: Research Lithuanian basketball federation youth leagues
- [ ] **LNB Espoirs**: Research French U21 league structure

### Long-term Research (Next Month)

- [ ] **NEPSAC**: New England prep school stats availability
- [ ] **Midwest state hubs**: MI, MO, KS, NE research
- [ ] **Canadian provincial**: BC, AB, QC stats availability
- [ ] **Asian leagues**: Philippines (UAAP), Japan (JBA), South Korea (KBA)

---

## Success Metrics

### Sprint 2 Targets (This Week)
- [ ] 3+ new sources active (RankOne + 2 templates)
- [ ] SBLive/Bound expansion research complete
- [ ] 5-8 new US states identified for coverage

### Month 1 Targets
- [ ] 20+ US states with coverage
- [ ] 5+ European youth leagues active
- [ ] Event adapter framework complete
- [ ] Identity resolution system live

### Month 3 Targets
- [ ] 25+ US states with coverage (50% of states)
- [ ] 10+ global sources active
- [ ] 5+ showcase event adapters
- [ ] School dictionary (NCES) integration complete

---

## File Organization

### New Files to Create

**Adapters**:
- `src/datasources/us/rankone.py` (Sprint 2)
- `src/datasources/us/texas_hoops.py` (Sprint 3)
- `src/datasources/europe/nbbl.py` (Sprint 4)
- `src/datasources/europe/feb.py` (Sprint 4)
- `src/datasources/europe/mkl.py` (Future)
- `src/datasources/europe/lnb_espoirs.py` (Future)
- `src/datasources/us/nepsac.py` (Sprint 6)
- `src/datasources/events/base_event.py` (Sprint 5)
- `src/datasources/events/nbpa_top100.py` (Sprint 5)
- `src/datasources/events/pangos.py` (Sprint 5)

**Services**:
- `src/services/identity_resolver.py` (Ongoing)
- `src/services/school_normalizer.py` (Ongoing)
- `src/cli/backfill.py` (Ongoing)

**Tests**:
- Corresponding test file for each new adapter
- `tests/test_services/test_identity_resolver.py`
- `tests/test_services/test_school_normalizer.py`

**Data**:
- `data/identity_overrides.csv` (manual player ID overrides)
- `data/nces_schools.csv` (NCES school directory)

---

## Notes

- **MaxPreps**: Excluded from automation due to ToS violation
- **Conservative Rate Limiting**: Always start at 50% of observed limits
- **Robots.txt**: Check BEFORE implementing any new adapter
- **Terms of Service**: Review for all new sources
- **Incremental Rollout**: Test thoroughly before marking adapter as "active"
- **Documentation**: Update PROJECT_LOG.md after each sprint

---

**End of Roadmap**
**Last Updated**: 2025-11-11
**Next Review**: After Sprint 2 completion
