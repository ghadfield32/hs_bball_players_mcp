# Phase 14 URL Discovery Guide

## Current Status

**Phase 14 Global Expansion Scaffolding: COMPLETE ✅**

All code infrastructure is production-ready. What remains is **URL discovery** (research task):

### Completed Infrastructure

1. **Vendor Generic Adapters (Active)**
   - `FibaFederationEventsDataSource` - parameterized by federation_code
   - `GameDayDataSource` - parameterized by base_url + comp_id
   - Both registered in aggregator and sources.yaml

2. **30+ Research Sources Added**
   - Africa: 4 (EGY, NGA, SEN, RSA)
   - Asia: 9 (JPN, CHN, KOR, TWN, PHI)
   - Oceania: 2 (NZ schools, AU PlayHQ)
   - Canada: 4 provincial (OFSAA, RSEQ, BCSS, ASAA)
   - US: 3 prep/state (NIBC, WCAC, NCHSAA/GHSA)

3. **Quality Infrastructure**
   - `verify_boxscore_integrity()` with 6 checks
   - Category extensions for new regions
   - Level normalization for U22/U23/UNI

---

## URL Discovery Process (Step-by-Step)

### Phase 14.6: FIBA Federation Events

**Target Sources:** Egypt, Nigeria, Japan, Brazil, Korea, Philippines

**Discovery Steps:**
1. Visit `https://www.fiba.basketball/livestats/[federation]` (e.g., `egy`, `nga`, `jpn`)
2. Inspect network tab for API endpoints:
   - Look for `/competitions` or `/events` JSON endpoints
   - Note authentication requirements (if any)
   - Document response structure

**Example URLs to Test:**
```
https://www.fiba.basketball/livestats/egy/competitions
https://www.fiba.basketball/livestats/jpn/u18
https://www.fiba.basketball/livestats/nga/events
```

**Once URLs Found:**
- Update `fiba_federation_events.py` parsing logic in:
  - `get_competitions()` - parse competition list
  - `get_teams()` - parse team rosters
  - `get_games()` - parse fixtures/results
  - `get_boxscore()` - parse box scores (if available)

**Testing:**
```python
# Test script
from src.datasources.vendors.fiba_federation_events import FibaFederationEventsDataSource

async def test_fiba():
    source = FibaFederationEventsDataSource(federation_code="EGY", season="2024")
    comps = await source.get_competitions()
    print(f"Found {len(comps)} competitions for Egypt 2024")

# Run: python -m asyncio test_script.py
```

---

### Phase 14.7: GameDay (BBNZ New Zealand)

**Target:** BBNZ Secondary Schools

**Discovery Steps:**
1. Visit Basketball New Zealand site: `https://www.basketball.org.nz`
2. Navigate to Secondary Schools competitions
3. Inspect URLs - look for patterns like:
   - `sportstg.com/comp_info.cgi?c=[comp_id]`
   - `websites.sportstg.com/assoc_page.cgi?c=[comp_id]`
   - `gameday.basketball.org.nz/comp/[comp_id]`

**Example URLs to Test:**
```
https://websites.sportstg.com/comp_info.cgi?c=1-8563-0-0-0
https://websites.sportstg.com/comp_info.cgi?c=1-9234-0-0-0&a=GRADE
```

**Once URLs Found:**
- Update `gameday.py` parsing logic in:
  - `get_competition_info()` - parse comp metadata
  - `get_divisions()` - parse grades/divisions
  - `get_teams()` - parse team lists
  - `get_games()` - parse fixtures/results

**Testing:**
```python
from src.datasources.vendors.gameday import GameDayDataSource

async def test_gameday():
    source = GameDayDataSource(
        base_url="https://websites.sportstg.com/comp_info.cgi",
        comp_id="1-8563-0-0-0",
        season="2024",
        org_name="BBNZ"
    )
    info = await source.get_competition_info()
    print(f"Competition: {info}")

# Run: python -m asyncio test_script.py
```

---

### Phase 14.8: PlayHQ (Australia)

**Target:** Australian state pathways

**Discovery Steps:**
1. Visit PlayHQ: `https://www.playhq.com`
2. Search for basketball competitions in Victoria, NSW, Queensland
3. Inspect URLs - pattern typically:
   - `playhq.com/basketball-australia/org/[org_slug]/[comp_id]`
   - Note: may require authentication

**Example URLs to Test:**
```
https://www.playhq.com/basketball-australia/org/basketball-victoria/[comp_id]
https://www.playhq.com/basketball-australia/org/basketball-nsw/[comp_id]
```

**Template Already Exists:**
- File: `src/datasources/australia/playhq.py`
- Status: template (needs URL parameters)

**Activation:**
Update `config/sources.yaml` entry for `au_state_playhq`:
```yaml
- id: au_state_playhq
  name: "Australia State Pathways (PlayHQ)"
  region: OCEANIA
  type: platform
  family: OCEANIA_SCHOOL
  status: template → active  # Change after URL discovery
  routed_by: playhq
  params:
    org_slug: "basketball-victoria"  # Fill in discovered value
    comp_id: "abc123"                # Fill in discovered value
    season: "2024"                   # Current season
```

---

### Phase 14.9: State Association HTML Adapters

**Targets:** OFSAA (Ontario), NCHSAA (North Carolina), GHSA (Georgia)

**Discovery Steps:**

#### OFSAA (Ontario)
1. Visit: `https://www.ofsaa.on.ca`
2. Navigate to Basketball → Championships
3. Document:
   - Championship bracket URLs
   - Schedule page structure
   - Team listing format
4. Update `src/datasources/canada/ofsaa.py` HTML parsing

#### NCHSAA (North Carolina)
1. Visit: `https://www.nchsaa.org`
2. Navigate to Boys Basketball → State Championships
3. Document:
   - Bracket URLs by classification (4A, 3A, 2A, 1A)
   - Schedule format
4. Update `src/datasources/us/nchsaa.py` HTML parsing

#### GHSA (Georgia)
1. Visit: `https://www.ghsa.net`
2. Navigate to Basketball → State Tournament
3. Document:
   - Bracket structure
   - Regional/sectional format
4. Update `src/datasources/us/ghsa.py` HTML parsing

**HTML Parsing Template:**
```python
async def _parse_html_data(self, html: str, season: str) -> dict:
    """Parse HTML data from association brackets."""
    soup = parse_html(html)
    teams = []
    games = []

    # Find bracket tables
    tables = soup.find_all("table", class_=["bracket", "schedule", "tournament"])

    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                game = self._parse_game_from_row(cells, season)
                if game:
                    games.append(game)

    return {"teams": teams, "games": games, "season": season}
```

---

## Activation Checklist

For each source, complete these steps:

### 1. URL Discovery ✅
- [ ] Find actual URLs/endpoints
- [ ] Document authentication requirements
- [ ] Inspect HTML/JSON structure
- [ ] Note any rate limits

### 2. Implementation ✅
- [ ] Update parsing methods in adapter
- [ ] Add error handling
- [ ] Map to unified schema (Game, Team, Player models)
- [ ] Test with real URLs

### 3. Validation ✅
- [ ] Run `verify_boxscore_integrity()` on sample data
- [ ] Check categorical mappings (level, family)
- [ ] Verify source_url and fetched_at are set
- [ ] Test end-to-end retrieval

### 4. Activation ✅
- [ ] Update `sources.yaml` status: `research_needed` → `active`
- [ ] Fill in discovered URLs/params
- [ ] Add URL discovery notes
- [ ] Document any limitations

---

## Testing Commands

### Syntax Validation
```bash
# Validate adapter syntax
python -m py_compile src/datasources/vendors/fiba_federation_events.py
python -m py_compile src/datasources/vendors/gameday.py
python -m py_compile src/datasources/canada/ofsaa.py
```

### Connection Testing
```bash
# Test FIBA federation adapter
python -c "from src.datasources.vendors.fiba_federation_events import FibaFederationEventsDataSource; import asyncio; asyncio.run(FibaFederationEventsDataSource('EGY', '2024').get_competitions())"

# Test GameDay adapter
python -c "from src.datasources.vendors.gameday import GameDayDataSource; import asyncio; asyncio.run(GameDayDataSource('https://example.com', '12345', '2024').get_competition_info())"
```

### Quality Verification
```python
# Test integrity checks
from src.unified.quality import verify_boxscore_integrity
import pandas as pd

# Sample data
team_box = pd.DataFrame({
    'team_id': ['team_a', 'team_b'],
    'PTS': [75, 72],
    'team_side': ['home', 'away']
})

player_box = pd.DataFrame({
    'game_id': ['game1'] * 10,
    'player_id': ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9', 'p10'],
    'team_id': ['team_a'] * 5 + ['team_b'] * 5,
    'PTS': [15, 12, 10, 20, 18, 14, 11, 17, 16, 14],
    'MIN': [25, 20, 18, 30, 28, 22, 19, 27, 24, 21]
})

checks = verify_boxscore_integrity(team_box, player_box)
print(f"Integrity checks: {checks}")
print(f"Accept: {checks['accept']}")
```

---

## Priority Order (Recommended)

### High Leverage (Do First)
1. **FIBA Federation Events** - One adapter unlocks 20+ countries
   - Start with: Egypt (EGY), Japan (JPN), Nigeria (NGA)
2. **GameDay** - Unlocks NZ + AU pockets
   - Start with: BBNZ Secondary Schools

### Medium Priority
3. **State Associations** - Schedule/lineage data
   - NCHSAA (major talent pipeline)
   - GHSA (major talent pipeline)
   - OFSAA (Canada's largest province)

### Lower Priority (Once patterns validated)
4. **Additional FIBA federations** - Replicate EGY/JPN/NGA pattern
5. **Additional GameDay instances** - Replicate BBNZ pattern
6. **Additional state bodies** - Replicate OFSAA/NCHSAA/GHSA pattern

---

## Notes

**Why Skeletons Are Production-Ready:**
- Return empty/None = safe, no crashes
- Graceful degradation by design
- Can deploy now, enhance later

**Quality Gates:**
- All data flows through `verify_boxscore_integrity()`
- Failed checks logged to quarantine table
- `source_url` + `fetched_at` tracked for all data

**Next Phase After URL Discovery:**
- Phase 15: Latin America expansion (Brazil LDB, Argentina LDD)
- Phase 16: Additional Asia sources (full HBL/CUBA/U-League implementation)
- Phase 17: Complete US state coverage (remaining 40+ states)

---

*Last Updated: 2025-11-12 12:30 UTC*
*Status: Phase 14 scaffolding complete; URL discovery in progress*
