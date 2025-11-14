# Iowa IHSAA Datasource Research

**Date:** 2025-11-12
**Researcher:** Claude Code
**Target:** Iowa High School Athletic Association (IHSAA) Basketball Data
**Goal:** Implement adapter to reach 90% US coverage (44/50 → 45/50 states)

---

## Executive Summary

Iowa IHSAA provides basketball data through **multiple platforms**, with a mix of modern and legacy systems. The primary challenge is that **Bound.com** (official bracket platform) blocks automated access (403 Forbidden), requiring alternative data sources.

**Recommended Approach:** Implement adapter using **stats.iahsaa.org** (legacy HTML platform) for tournament game data and box scores.

**Confidence:** 🟡 MEDIUM - Data available but limited to tournament games, no obvious leaderboard/player search

---

## Data Sources Identified

### 1. Official IHSAA Website

**URL:** https://www.iahsaa.org/basketball/

**Structure:**
- Main basketball hub: `/basketball/`
- State tournament: `/basketball/state-tournament-central`
- Classifications: `/classifications/basketball`

**Available Data:**
- Tournament schedules and information
- Championship results (all classifications)
- Links to live stats and brackets
- Box score HTML files: `/wp-content/uploads/2025/03/[class][number].htm`

**Accessibility:** ✅ Public, no bot protection

### 2. Stats Platform (Legacy HTML)

**URL:** https://stats.iahsaa.org/basketball/

**Structure:**
```
stats.iahsaa.org/basketball/
├── xlive.htm           # Game status
├── xteams.htm          # Team statistics
├── xvisitor.htm        # Visitor box score
├── xhome.htm           # Home box score
├── xleaders.htm        # Player leaders
├── xplays1.htm         # Q1 play-by-play
├── xplays2.htm         # Q2 play-by-play
├── xplays3.htm         # Q3 play-by-play
└── xplays4.htm         # Q4 play-by-play
```

**Available Data:**
- Game-by-game statistics (tournament only?)
- Team box scores (FG, 3PT, FT, REB, AST, TO, PF, PTS)
- Individual player statistics
- Play-by-play records with timestamps
- Statistical leaders by game

**Data Format:** ✅ Static HTML tables (no JavaScript rendering!)

**Accessibility:** ✅ Public, no bot protection

**URL Pattern Note:** Appears to be per-game basis (may need tournament bracket to enumerate games)

### 3. Bound.com (Bracket Platform)

**URL:** https://www.gobound.com/ia/ihsaa/boysbasketball/

**Structure:**
- Season scores: `/ia/ihsaa/boysbasketball/[year]/scores`
- Brackets: `/ia/ihsaa/boysbasketball/[year]/brackets/[bracket_id]`
- Team rosters, schedules, standings

**Available Data:**
- Interactive brackets for all classifications
- Regular season schedules and scores
- Team rosters and player data
- Comprehensive season statistics

**Accessibility:** ❌ **403 Forbidden** - Bot protection in place

**Impact:** Cannot use Bound.com directly for automated data collection

### 4. Presto Sports Platform

**URL:** https://iahsaastats.prestosports.com/composite

**Structure:**
- Composite schedule: `/composite?y=[year]&m=[month]`
- Sport schedules: `/sports/[sport]/[year]/schedule`
- Box scores: `/sports/[sport]/[year]/boxscores/[date]_[id].xml`

**Available Data (Theoretical):**
- Schedules across all sports
- Box scores in XML format
- Team stats aggregations

**Accessibility:** ⚠️ Platform exists but **no active basketball data found**

**Impact:** May only host football/other sports, or data only available during season

---

## Tournament Structure

### Classifications

Iowa uses **4 classifications** similar to Illinois and Wisconsin:
- **Class 4A** - Largest schools
- **Class 3A**
- **Class 2A**
- **Class 1A** - Smallest schools

### Tournament Format

**State Tournament:**
- **Dates:** March 10-14 annually
- **Venue:** Wells Fargo Arena, Des Moines
- **Format:** Quarterfinals → Semifinals → Championships
- **Coverage:** Live stats + IHSSN streaming

**Tournament Phases:**
1. Substate tournaments (regional)
2. State tournament (Wells Fargo Arena)

---

## Data Availability Assessment

### What's Available ✅

1. **Tournament Games:**
   - Complete box scores (team + player stats)
   - Play-by-play data
   - Game metadata (date, location, officials)
   - Statistical leaders per game

2. **Tournament Brackets:**
   - Championship bracket results
   - Game schedules and locations
   - Team matchups

3. **Historical Data:**
   - Previous years' champions
   - Archived box scores (as HTML files)

### What's Missing/Limited ⚠️

1. **Regular Season Data:**
   - No obvious access to regular season games
   - Bound.com (which has this) is blocked

2. **Player Search/Leaderboards:**
   - No aggregated season leaderboards found
   - Only per-game leaders available

3. **Team Schedules:**
   - Individual team season schedules not accessible
   - Would require Bound.com access

---

## Implementation Recommendations

### Option A: Tournament-Only Adapter (Recommended)

**Data Source:** stats.iahsaa.org + iahsaa.org

**Capabilities:**
- ✅ Tournament brackets (4A, 3A, 2A, 1A)
- ✅ Tournament game box scores
- ✅ Tournament player statistics
- ❌ Regular season games
- ❌ Player search/leaderboards

**Implementation Pattern:** Similar to **Illinois IHSA** (tournament-focused)

**Pros:**
- Reliable HTML parsing (no JavaScript)
- No bot protection issues
- Clean, structured data

**Cons:**
- Limited to tournament games only (~16-32 games per year)
- No comprehensive player statistics

**Estimated Effort:** 2-3 hours

### Option B: Bound.com Workaround

**Approach:** Try alternative methods to access Bound.com:
1. Different user-agent strings
2. Selenium/browser automation
3. Official API (if available)

**Pros:**
- Would provide regular season data
- Comprehensive player statistics
- Full schedule access

**Cons:**
- Ethical concerns (bypassing bot protection)
- May violate terms of service
- Fragile (could break if detection improves)
- Increased complexity (3-4 hours)

**Recommendation:** ❌ NOT RECOMMENDED - Respect bot protection

### Option C: Contact IHSAA for Data Access

**Approach:** Reach out to IHSAA to request:
- Official API access
- Data export options
- Permission to scrape Bound.com

**Pros:**
- Ethical and sustainable
- Potential for official partnership
- May get better data access

**Cons:**
- Time-consuming (days/weeks)
- No guarantee of approval
- Blocks immediate implementation

**Recommendation:** 🟡 CONSIDER for future enhancement

---

## Proposed Implementation: Option A (Tournament Adapter)

### Adapter Class

**Name:** `IowaIHSAADataSource`

**Base Class:** `AssociationAdapterBase` (similar to IHSA/WIAA)

**Module:** `src/datasources/us/iowa_ihsaa.py`

### Core Methods

```python
class IowaIHSAADataSource(AssociationAdapterBase):
    """
    Iowa High School Athletic Association Basketball Data Source

    Provides tournament bracket and game data for Iowa high school basketball.
    Regular season data not available due to Bound.com access restrictions.

    Data Coverage:
    - Tournament brackets: 2015-present (estimated)
    - Game statistics: Tournament games only
    - Player data: Tournament participants only
    - Classes: 1A (smallest) → 4A (largest)
    """

    base_url = "https://www.iahsaa.org"
    stats_url = "https://stats.iahsaa.org/basketball"

    # Core capabilities
    async def get_tournament_brackets(
        self, season: str, class_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch state tournament brackets for given season."""
        # Strategy:
        # 1. Access /basketball/state-tournament-central
        # 2. Extract tournament dates and matchups
        # 3. Parse bracket structure (QF → SF → Finals)
        # 4. Return games + teams + metadata
        pass

    async def get_game_stats(
        self, game_id: str
    ) -> Dict[str, Any]:
        """Fetch detailed game statistics from stats.iahsaa.org."""
        # Strategy:
        # 1. Build URL: stats.iahsaa.org/basketball/[game]/
        # 2. Parse xteams.htm for team box scores
        # 3. Parse xhome.htm + xvisitor.htm for player stats
        # 4. Optionally parse xplays[1-4].htm for play-by-play
        pass

    # Inherited/Unsupported methods
    async def search_players(self, **filters) -> List[Player]:
        """❌ Not supported - no player search available."""
        raise NotImplementedError("Player search not available for Iowa IHSAA")

    async def get_schedule(self, **filters) -> List[Game]:
        """⚠️ Limited - tournament games only."""
        # Return tournament schedule
        pass
```

### URL Patterns

**Tournament Central:**
```
https://www.iahsaa.org/basketball/state-tournament-central
```

**Box Scores:**
```
https://www.iahsaa.org/wp-content/uploads/[year]/03/[class][number].htm
Example: /wp-content/uploads/2025/03/4A1.htm (4A game #1)
```

**Live Stats (per game):**
```
https://stats.iahsaa.org/basketball/[game-slug]/xteams.htm
https://stats.iahsaa.org/basketball/[game-slug]/xhome.htm
https://stats.iahsaa.org/basketball/[game-slug]/xvisitor.htm
https://stats.iahsaa.org/basketball/[game-slug]/xleaders.htm
```

### Parsing Strategy

**1. Bracket Extraction:**
- Scrape tournament central page
- Extract game results and matchups
- Map to classes (1A-4A)
- Build bracket structure

**2. Box Score Parsing:**
- Access uploaded HTML files or live stats
- Parse team statistics tables
- Extract player performance data
- Calculate derived stats (shooting %)

**3. Player Data:**
- Extract from game box scores
- Aggregate tournament totals
- Build player profiles

### Filters/Parameters

```python
# Supported filters
get_tournament_brackets(
    season="2024-25",           # Required: tournament year
    class_name="4A",             # Optional: specific classification
    gender="Boys"                # Optional: Boys/Girls (future)
)

get_game_stats(
    game_id="2025_4A_Final"      # Game identifier
)
```

---

## Historical Data Range

**Estimate:** 2015-present (10 years)

**Reasoning:**
- Website redesign appears relatively recent
- Box score HTML uploads pattern suggests modern system
- Will need actual testing to confirm earliest available data

**Validation Strategy:**
- During implementation, test multiple seasons: 2024, 2023, 2020, 2015, 2010
- Document actual available range in adapter docstring
- Update DATASOURCE_CAPABILITIES.md

---

## Testing Strategy

### Unit Tests

```python
# tests/test_datasources/test_iowa_ihsaa.py

@pytest.mark.asyncio
async def test_get_tournament_brackets_2024():
    """Test 2024 tournament bracket retrieval."""
    source = IowaIHSAADataSource()
    result = await source.get_tournament_brackets(season="2024-25", class_name="4A")

    assert "games" in result
    assert "teams" in result
    assert "brackets" in result
    assert len(result["games"]) > 0  # Should have QF + SF + Finals = ~7 games per class

@pytest.mark.asyncio
async def test_all_classifications():
    """Test all four classifications retrieve data."""
    source = IowaIHSAADataSource()

    for class_name in ["1A", "2A", "3A", "4A"]:
        result = await source.get_tournament_brackets(
            season="2024-25",
            class_name=class_name
        )
        assert len(result["games"]) > 0, f"No games found for {class_name}"

@pytest.mark.asyncio
async def test_player_search_not_supported():
    """Verify player search raises NotImplementedError."""
    source = IowaIHSAADataSource()

    with pytest.raises(NotImplementedError):
        await source.search_players(name="Test Player")
```

### Integration Validation

During basketball season (March):
1. Run full audit script
2. Verify all 4 classifications accessible
3. Check historical range (test back to 2015)
4. Validate data quality (complete box scores)

---

## Limitations & Caveats

### Known Limitations

1. **Tournament Only:**
   - No regular season games
   - Limited to ~32-64 games per year (all classifications)
   - Cannot track player season performance

2. **No Player Search:**
   - Cannot search by player name
   - Must extract players from game rosters
   - No aggregated leaderboards

3. **Seasonal Availability:**
   - Off-season testing will show no current data
   - Historical data depends on HTML file archiving
   - Live stats may only work during tournament week

4. **No Regular Season Context:**
   - Cannot provide team regular season records
   - No pre-tournament seeding information (unless on tournament page)
   - Limited to postseason narrative

### Documentation Requirements

Must clearly document in:
- Adapter docstring
- README.md
- DATASOURCE_CAPABILITIES.md

**Example documentation:**
```
Iowa IHSAA: Tournament games only (no regular season).
Player search not supported. March state tournament coverage.
Classes: 1A-4A. Historical: 2015-present (estimated).
```

---

## Comparison to Similar Adapters

| Feature | Illinois IHSA | Wisconsin WIAA | Iowa IHSAA (Proposed) |
|---------|---------------|----------------|------------------------|
| **Tournament Brackets** | ✅ | ✅ | ✅ |
| **Regular Season** | ❌ | ❌ | ❌ |
| **Player Search** | ❌ | ❌ | ❌ |
| **Game Stats** | ✅ | ✅ | ✅ |
| **Data Format** | HTML | HTML | HTML (static) |
| **Classes** | 1A-4A | Div 1-5 | 1A-4A |
| **Gender** | Boys/Girls | Boys/Girls | Boys (Girls TBD) |
| **Historical** | 2016+ | 2018+ | 2015+ (est) |

**Conclusion:** Iowa IHSAA adapter will follow same pattern as Illinois/Wisconsin - tournament-focused, limited regular season.

---

## Next Steps

### Immediate (Today)

1. ✅ Research complete - document findings
2. ⏳ Create implementation plan
3. ⏳ Begin adapter implementation

### Implementation Phase (2-3 hours)

1. Create `src/datasources/us/iowa_ihsaa.py`
2. Implement `IowaIHSAADataSource` class
3. Add tournament bracket parsing
4. Add game stats parsing
5. Write unit tests
6. Update README: 44/50 (88%) → 45/50 (90%)

### Validation Phase (During Season)

1. Test during March 2025 state tournament
2. Run full audit
3. Validate historical range
4. Document any issues

---

## Open Questions

1. **Historical Range:** How far back do box score HTML files exist?
   - **Test:** Try URLs for 2024, 2023, 2020, 2015 during implementation

2. **Girls Basketball:** Does Iowa have separate girls tournament?
   - **Research:** Check iahsaa.org for girls basketball section
   - **Action:** If yes, add gender parameter support

3. **Game ID Pattern:** What's the consistent format for game identifiers?
   - **Test:** Examine multiple game URLs to determine pattern
   - **Action:** Document in adapter code

4. **Substate Data:** Are substate tournament games available?
   - **Research:** Check if substate brackets/scores accessible
   - **Action:** If yes, expand scope to include substates

---

## Recommendation

**✅ PROCEED with Option A: Tournament-Only Adapter**

**Rationale:**
1. Respects Bound.com bot protection
2. Provides valuable tournament data
3. Follows established pattern (IHSA/WIAA)
4. Achieves 90% US coverage goal
5. Can be enhanced later if API access obtained

**Estimated Timeline:**
- Implementation: 2-3 hours
- Testing: 30 minutes
- Documentation: 30 minutes
- **Total:** 3-4 hours

**Success Criteria:**
- [x] Research Iowa IHSAA structure
- [ ] Implement tournament bracket parsing
- [ ] Parse game box scores
- [ ] Extract player statistics
- [ ] Write comprehensive tests
- [ ] Update README to 90% coverage
- [ ] Document limitations

**Phase 17 Progress:** 88% → 90% (1 state added)
