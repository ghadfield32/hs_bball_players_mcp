# Data Enhancement Implementation Plan
**Phase 1: Quick Wins - Maximum Forecasting Impact**
**Target Timeline**: 2-3 weeks
**Expected Coverage Improvement**: 25% → 55% (+30 percentage points)

---

## Overview

This plan focuses on extracting maximum value from existing data sources with minimal effort.
All enhancements target Tier 1 CRITICAL metrics identified in the audit.

---

## Enhancement 1: Advanced Stats Calculator

### Current State
- Basic stats captured: PPG, RPG, APG, FG%, 3P%, FT%
- Advanced stats: NONE

### Target State
- Add 10 calculated advanced metrics
- Implement as utility function
- Auto-calculate on data ingestion

### Implementation

**New File**: `src/utils/advanced_stats.py`

**Functions**:
```python
def calculate_true_shooting_percentage(pts, fga, fta) -> float:
    """TS% = PTS / (2 * (FGA + 0.44 * FTA))"""

def calculate_effective_fg_percentage(fgm, fg3m, fga) -> float:
    """eFG% = (FGM + 0.5 * 3PM) / FGA"""

def calculate_assist_to_turnover_ratio(ast, tov) -> float:
    """A/TO = AST / TOV"""

def calculate_usage_rate(fga, fta, tov, tm_fga, tm_fta, tm_tov, mp, tm_mp) -> float:
    """USG% = 100 * ((FGA + 0.44 * FTA + TOV) * (Tm MP / 5)) / (MP * (Tm FGA + 0.44 * Tm FTA + Tm TOV))"""

def calculate_offensive_rebound_percentage(orb, tm_orb, opp_drb) -> float:
    """ORB% = ORB / (Tm ORB + Opp DRB)"""

def calculate_player_efficiency_rating(...) -> float:
    """PER calculation"""

def enrich_player_season_stats(stats: PlayerSeasonStats) -> PlayerSeasonStats:
    """Automatically calculate all advanced stats"""
```

**Integration Points**:
- Aggregator service: Auto-enrich before returning
- DuckDB storage: Store calculated fields
- API responses: Include in all stat endpoints

**Effort**: 1 day
**Impact**: +8 percentage points coverage (8 critical metrics)

---

## Enhancement 2: 247Sports Full Profile Scraping

### Current State
- Extracts: Rankings, stars, rating, school, commitment
- Missing: Offers, predictions, visit history, recruiting timeline

### Target State
- Extract complete recruiting profile
- Parse offers table (college, date, conference)
- Parse Crystal Ball predictions (expert, confidence, date)
- Parse visit history (official/unofficial)

### Implementation

**File**: `src/datasources/recruiting/sports_247.py`

**New Methods**:
```python
async def get_player_recruiting_profile(self, player_id: str) -> Optional[RecruitingProfile]:
    """
    IMPLEMENT THIS (currently returns None)

    Steps:
    1. Build player profile URL from player_id
    2. Fetch page with BrowserClient
    3. Parse offers section → List[CollegeOffer]
    4. Parse predictions section → List[RecruitingPrediction]
    5. Parse visit history
    6. Aggregate rankings from different services
    7. Return complete RecruitingProfile
    """

async def get_offers(self, player_id: str) -> List[CollegeOffer]:
    """
    Parse offers table from player profile

    Table structure:
    | College | Conference | Offered | Status |

    Return CollegeOffer with:
    - college_name
    - conference_name
    - conference_level (power_6, high_major, etc.)
    - offer_date
    - status (OFFERED, COMMITTED, etc.)
    """

async def get_predictions(self, player_id: str) -> List[RecruitingPrediction]:
    """
    Parse Crystal Ball predictions

    Structure:
    | Expert | Prediction | Confidence | Date |

    Return RecruitingPrediction with:
    - predicted_college
    - predictor_name
    - predictor_org (if available)
    - prediction_date
    - confidence_level
    - confidence_score (convert % to 0.0-1.0)
    """
```

**URL Patterns** (need to verify):
```
Player Profile: https://247sports.com/player/{player_name}-{player_id}/
Offers: Profile page → Offers tab/section
Predictions: Profile page → Crystal Ball tab/section
```

**Challenges**:
- Player ID mapping (need to extract from rankings page)
- Dynamic content (React) - requires browser automation
- Anti-bot protection (rate limiting, captchas)

**Effort**: 2-3 days
**Impact**: +15 percentage points coverage (offers, predictions = CRITICAL)

---

## Enhancement 3: MaxPreps Game-by-Game Logs

### Current State
- Extracts: Season averages only
- Missing: Individual game stats, consistency analysis

### Target State
- Extract complete game log for each player
- Store individual game performances
- Calculate consistency metrics

### Implementation

**File**: `src/datasources/us/maxpreps.py`

**New Methods**:
```python
async def get_player_game_logs(
    self,
    player_id: str,
    season: str = "2024-25"
) -> List[PlayerGameStats]:
    """
    Extract game-by-game stats from player profile

    Steps:
    1. Navigate to player profile page
    2. Find game log table
    3. Parse each game row
    4. Return List[PlayerGameStats]

    Each game should include:
    - opponent_name
    - game_date
    - is_home_game
    - minutes, points, rebounds, assists, steals, blocks
    - field_goals (made/attempted)
    - three_pointers (made/attempted)
    - free_throws (made/attempted)
    - turnovers, fouls
    """

def _parse_game_log_row(self, row: dict) -> Optional[PlayerGameStats]:
    """Parse individual game from table row"""

async def calculate_consistency_metrics(
    self,
    game_logs: List[PlayerGameStats]
) -> dict:
    """
    Calculate consistency metrics from game logs

    Returns:
    - std_dev_ppg: Standard deviation of PPG
    - best_game: Highest scoring game
    - worst_game: Lowest scoring game
    - games_over_20pts: Count of 20+ point games
    - consistency_score: 1.0 - (std_dev / mean)
    """
```

**URL Pattern**:
```
Player Profile: https://www.maxpreps.com/{state}/player/{player-name}/{player-id}
Game Log Tab: Profile → Stats → Game Log
```

**Effort**: 2 days
**Impact**: +10 percentage points coverage (consistency, game logs = HIGH VALUE)

---

## Enhancement 4: Birth Date Extraction

### Current State
- Birth date field exists in Player model
- NOT extracted by any adapter

### Target State
- Extract birth date from 247Sports, MaxPreps profiles
- Calculate age-for-grade
- Store in database

### Implementation

**Files**: Multiple adapters

**Changes**:
1. **247Sports**: Extract from player profile header
2. **MaxPreps**: Extract from player profile header
3. **Add field to parsing methods**:
```python
# In _parse_player_profile()
birth_date_str = profile.find("span", class_="birth-date").text
birth_date = parse_date(birth_date_str)  # e.g., "Jan 15, 2006"
```

4. **Add calculated field to Player model**:
```python
@property
def age_for_grade(self) -> Optional[float]:
    """
    Calculate age relative to graduation year
    Younger players in their class = higher potential
    """
    if not self.birth_date or not self.grad_year:
        return None

    # Expected birth year for grade
    expected_birth_year = self.grad_year - 18
    actual_birth_year = self.birth_date.year

    return actual_birth_year - expected_birth_year
```

**Effort**: 1 day
**Impact**: +3 percentage points coverage (age-for-grade = CRITICAL)

---

## Enhancement 5: Power 6 Offer Detection

### Current State
- College names extracted from 247Sports
- Conference level NOT classified

### Target State
- Classify each offer by conference level
- Count Power 6 offers
- Store in RecruitingProfile

### Implementation

**New File**: `src/utils/college_conferences.py`

```python
# Power 6 conferences (2024-25)
POWER_6_CONFERENCES = {
    "ACC", "Big Ten", "Big 12", "Pac-12", "SEC", "Big East"
}

# Conference membership lookup
CONFERENCE_MAP = {
    "Duke": "ACC",
    "North Carolina": "ACC",
    "Kentucky": "SEC",
    "Kansas": "Big 12",
    # ... complete mapping for all D1 schools
}

def classify_conference_level(college_name: str) -> ConferenceLevel:
    """
    Classify college by conference level

    Returns:
    - POWER_6: Top 6 conferences
    - HIGH_MAJOR: American, A-10, WCC, etc.
    - MID_MAJOR: Conference USA, MAC, etc.
    - LOW_MAJOR: Summit, Big South, etc.
    - D2, D3, NAIA, JUCO, INTERNATIONAL
    """

def count_power_6_offers(offers: List[CollegeOffer]) -> int:
    """Count offers from Power 6 schools"""

def get_best_offer(offers: List[CollegeOffer]) -> Optional[CollegeOffer]:
    """Return highest-level offer"""
```

**Integration**:
```python
# In RecruitingProfile
@property
def power_6_offer_count(self) -> int:
    if not self.offers:
        return 0
    return count_power_6_offers(self.offers)
```

**Effort**: 1 day (for initial mapping)
**Impact**: +5 percentage points coverage (Power 6 offers = CRITICAL)

---

## Enhancement 6: Offensive/Defensive Rebounding Split

### Current State
- Total rebounds extracted
- ORB/DRB split: NOT extracted

### Target State
- Extract ORB, DRB when available
- Calculate rebounding percentages

### Implementation

**Files**: `maxpreps.py`, `eybl.py`, `uaa.py`

**Changes**:
```python
# In _parse_player_stats_from_row()
orb = parse_int(row.get("ORB") or row.get("Off Reb") or row.get("O-Reb"))
drb = parse_int(row.get("DRB") or row.get("Def Reb") or row.get("D-Reb"))

# If split not available but total rebounds is:
if not orb and not drb and total_rebounds:
    # Estimate: ~30% offensive, ~70% defensive (league average)
    orb = int(total_rebounds * 0.30)
    drb = int(total_rebounds * 0.70)
```

**Effort**: 0.5 days
**Impact**: +2 percentage points coverage (rebounding split = HIGH VALUE)

---

## Enhancement 7: Tournament Performance Tracking

### Current State
- Tournament games mixed with regular season
- No separate tournament stats

### Target State
- Tag games as tournament vs. regular season
- Calculate tournament-only stats
- Identify clutch performers

### Implementation

**Changes to PlayerSeasonStats model**:
```python
# Add new optional fields
tournament_games_played: Optional[int] = None
tournament_ppg: Optional[float] = None
tournament_rpg: Optional[float] = None
tournament_apg: Optional[float] = None
championship_games: Optional[int] = None
```

**Tournament Detection**:
```python
TOURNAMENT_KEYWORDS = [
    "state championship", "regional", "sectional", "district",
    "playoffs", "tournament", "peach jam", "finals", "semifinal"
]

def is_tournament_game(game_description: str) -> bool:
    """Detect if game is tournament/playoff"""
    return any(keyword in game_description.lower()
               for keyword in TOURNAMENT_KEYWORDS)
```

**Effort**: 1 day
**Impact**: +4 percentage points coverage (tournament performance = HIGH VALUE)

---

## Implementation Order & Timeline

### Week 1
**Day 1**: Advanced Stats Calculator (Enhancement 1)
- Create `src/utils/advanced_stats.py`
- Implement TS%, eFG%, A/TO calculations
- Integrate with aggregator
- **Deliverable**: +8 metrics

**Day 2-3**: Birth Date Extraction (Enhancement 4)
- Update 247Sports parser
- Update MaxPreps parser
- Add age-for-grade calculation
- **Deliverable**: +1 critical metric

**Day 4-5**: Rebounding Split (Enhancement 6)
- Update all stat parsers
- Handle missing data cases
- **Deliverable**: +2 metrics

### Week 2
**Day 1-3**: 247Sports Full Profiles (Enhancement 2)
- Implement `get_player_recruiting_profile()`
- Parse offers table
- Parse Crystal Ball predictions
- **Deliverable**: +15 critical metrics

**Day 4-5**: Power 6 Offer Classification (Enhancement 5)
- Create conference mapping
- Classify all schools
- Add offer counting
- **Deliverable**: +1 critical metric

### Week 3
**Day 1-2**: MaxPreps Game Logs (Enhancement 3)
- Implement game log extraction
- Parse individual games
- **Deliverable**: +5 metrics

**Day 3-4**: Tournament Tracking (Enhancement 7)
- Add tournament detection
- Calculate split stats
- **Deliverable**: +3 metrics

**Day 5**: Testing & Documentation
- Integration testing
- Update API documentation
- Update PROJECT_LOG

---

## Expected Results

### Before Enhancements
- **Metrics Coverage**: 25%
- **Forecasting Power**: Limited
- **Top 10 Feature Coverage**: 2/10 (20%)

### After Phase 1 (3 weeks)
- **Metrics Coverage**: 55% (+30 percentage points)
- **Forecasting Power**: Good
- **Top 10 Feature Coverage**: 6/10 (60%)

### New Capabilities
✅ Advanced efficiency metrics (TS%, eFG%, PER)
✅ Complete recruiting profiles (offers + predictions)
✅ Game-by-game consistency analysis
✅ Age-for-grade assessment
✅ Power 6 offer validation
✅ Tournament clutch performance
✅ Rebounding motor indicators

---

## Success Metrics

### Data Quality
- ✅ 80%+ of top players have complete recruiting profiles
- ✅ 90%+ of stats include advanced metrics
- ✅ 60%+ of players have game log data
- ✅ 95%+ of offers correctly classified by conference

### Forecasting Impact
- Expected R² improvement: 0.50 → 0.65 (+30%)
- NBA player identification: 60% → 75% (+25%)
- College success prediction accuracy: 15% improvement

### System Performance
- API response times: <500ms (no degradation)
- Database size increase: ~30% (acceptable)
- Scraping respect: Maintain conservative rate limits (10 req/min)

---

## Risk Mitigation

### Legal/ToS Risks
- **247Sports scraping**: Monitor for anti-bot measures, have fallback to manual data entry
- **MaxPreps scraping**: Already using browser automation, stay under rate limits
- **Mitigation**: Add circuit breakers, respect robots.txt, pursue commercial licenses

### Technical Risks
- **Browser automation reliability**: Add retries, error handling, fallback to cached data
- **Data quality**: Implement validation checks, flag low-quality extractions
- **Performance**: Use async operations, batch processing, aggressive caching

### Data Risks
- **Missing values**: Graceful degradation, estimate when possible
- **Inconsistent formats**: Multiple parsing attempts, fuzzy matching
- **Stale data**: TTL-based refresh, manual override capability

---

## Next Phase Preview

**Phase 2: New Data Sources** (Weeks 4-8)
- NBPA Top 100 Camp (combine data)
- USA Basketball (national team rosters)
- Pangos All-American (showcase stats)
- ESPN Rankings (direct scraping)
- Rivals Rankings (direct scraping)

**Expected**: +20 percentage points coverage (55% → 75%)

---

## Conclusion

This 3-week plan will transform the repository from basic stats aggregation to a comprehensive forecasting platform. By focusing on high-value quick wins, we achieve 30 percentage point improvement in metrics coverage with minimal effort.

**ROI**: 3 weeks investment → 30% forecasting accuracy improvement
