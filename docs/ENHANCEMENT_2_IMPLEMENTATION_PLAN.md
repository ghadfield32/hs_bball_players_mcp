# Enhancement 2: 247Sports Full Profile Scraping - Implementation Plan

**Enhancement**: 247Sports Full Profile Scraping
**Impact**: +15% data coverage (highest impact enhancement)
**Status**: Planning Phase
**Date**: 2025-11-15

---

## 📋 Systematic Analysis (Following Debug Methodology)

### Step 1: Expected Behavior vs Current State

**Expected Behavior**:
- `get_player_recruiting_profile(player_id)` should return a `RecruitingProfile` object containing:
  - Player rankings across all services (247Sports, Composite, ESPN, Rivals, On3)
  - List of college offers with schools, status, dates
  - Crystal Ball predictions with schools, confidence scores, experts
  - Player demographics (name, school, position, height, weight)

**Current State**:
- Method exists but returns `None` (placeholder implementation)
- Log warning: "get_player_recruiting_profile not yet implemented for 247Sports"
- Missing functionality: Profile page scraping, offers parsing, Crystal Ball parsing

**Discrepancy**:
- 0% implementation vs 100% needed
- No data extracted from player profile pages
- Missing 15% of total available recruiting metrics

### Step 2: Root Cause Analysis

**Why is this not implemented?**
1. **Complexity**: Player profile pages are more complex than rankings tables
2. **Dynamic Content**: 247Sports uses React - requires browser automation
3. **Anti-Bot Protection**: Player pages may have additional protection
4. **URL Structure**: Need to determine correct player profile URL format
5. **Parsing Complexity**: Multiple sections to parse (rankings, offers, predictions)

**Technical Challenges Identified**:
1. **URL Building**: How to construct player profile URL from player_id?
2. **Page Loading**: How to ensure React content is fully rendered?
3. **Offers Table**: How is the offers table structured?
4. **Crystal Ball**: How are predictions displayed and formatted?
5. **Data Extraction**: What selectors/patterns identify each data element?

### Step 3: Data Requirements

**What data do we need to extract?**

**From `RecruitingProfile` model** (`src/models/recruiting.py:335-380`):
```python
class RecruitingProfile(BaseModel):
    # Identity
    player_uid: str          # Universal player ID (can use player_id initially)
    player_name: str         # Player name

    # Rankings (from multiple services)
    rankings: List[RecruitingRank] = []
    best_national_rank: Optional[int] = None
    best_position_rank: Optional[int] = None
    best_state_rank: Optional[int] = None
    composite_stars: Optional[int] = None
    composite_rating: Optional[float] = None

    # Offers
    offers: List[CollegeOffer] = []
    total_offers: Optional[int] = None
    committed_to: Optional[str] = None
    commitment_date: Optional[datetime] = None

    # Predictions
    predictions: List[RecruitingPrediction] = []
    crystal_ball_leader: Optional[str] = None
    crystal_ball_confidence: Optional[float] = None
```

**From `CollegeOffer` model** (`src/models/recruiting.py:205-244`):
```python
class CollegeOffer(BaseModel):
    player_id: str
    player_name: str
    school: str
    conference: Optional[str] = None
    conference_level: Optional[ConferenceLevel] = None  # POWER_6, MID_MAJOR, LOW_MAJOR
    offer_status: OfferStatus  # OFFERED, VISITED, COMMITTED, SIGNED, DECOMMITTED
    offer_date: Optional[datetime] = None
    visit_date: Optional[datetime] = None
    commitment_date: Optional[datetime] = None
    recruiter_name: Optional[str] = None
    data_source: DataSource
```

**From `RecruitingPrediction` model** (`src/models/recruiting.py:247-285`):
```python
class RecruitingPrediction(BaseModel):
    player_id: str
    player_name: str
    school: str
    confidence: float  # 0.0-1.0 (or 0-10 for 247Sports format)
    expert_name: str
    prediction_date: datetime
    service: RecruitingService  # SPORTS_247, ESPN, RIVALS, ON3
    is_official: bool = False
    data_source: DataSource
```

---

## 🔍 Step 4: URL and Page Structure Research

### Assumptions (Need Verification)

**Player Profile URL Format** (Common patterns):
```
Option 1: https://247sports.com/player/{player_name}-{player_id}/
Option 2: https://247sports.com/Player/{player_name}-{player_id}/
Option 3: https://247sports.com/Season/2025-Basketball/Recruits/{player_name}-{player_id}/
```

**Player ID Format** (based on existing code):
- Current implementation: `247_{player_id}` or `247_{cleaned_name}`
- Example: `247_12345` or `247_john_doe`
- Need to extract numeric ID or full slug for URL building

**Page Sections Expected**:
1. **Player Info Header**: Name, position, height, weight, school, class year
2. **Rankings Section**: Multiple service rankings (247Sports, Composite, ESPN, Rivals, On3)
3. **Offers Table**: Schools that have offered, status, dates
4. **Crystal Ball Section**: Expert predictions with confidence percentages
5. **Commitment Section**: Committed school (if committed)

---

## 🛠️ Step 5: Implementation Strategy

### Phase 1: URL Building and Page Fetching (Debug First)

```python
def _build_player_profile_url(self, player_id: str) -> str:
    """
    Build 247Sports player profile URL from player_id.

    DEBUG APPROACH:
    1. Log input player_id format
    2. Try multiple URL patterns
    3. Log which pattern succeeds
    4. Return successful URL or raise error with all attempts

    Args:
        player_id: Player identifier (format: "247_12345" or "247_john_doe")

    Returns:
        Full player profile URL

    Raises:
        ValueError: If player_id format is invalid
    """
    # Extract ID from player_id (remove "247_" prefix)
    # Try multiple URL patterns (logged at each step)
    # Return first successful pattern
```

**Debug Points**:
- [ ] Log input `player_id` format
- [ ] Log extracted ID/slug
- [ ] Log each URL pattern attempted
- [ ] Log HTTP response status for each attempt
- [ ] Log final successful URL or failure reason

### Phase 2: Rankings Extraction (Reuse Existing Logic)

```python
def _parse_player_rankings(self, soup) -> List[RecruitingRank]:
    """
    Extract player rankings from profile page.

    DEBUG APPROACH:
    1. Log if rankings section found
    2. Log number of ranking services detected
    3. For each service, log extracted data
    4. Log any parsing errors with HTML context

    Returns:
        List of RecruitingRank objects (one per service)
    """
    # Find rankings table/section
    # For each service (247Sports, Composite, ESPN, Rivals, On3):
    #   - Extract rank, stars, rating
    #   - Log extracted values
    #   - Create RecruitingRank object
```

**Debug Points**:
- [ ] Log rankings section HTML structure
- [ ] Log number of services found
- [ ] For each service: log rank, stars, rating
- [ ] Log any missing/null values
- [ ] Log final count of rankings extracted

### Phase 3: Offers Table Parsing (New Implementation)

```python
def _parse_player_offers(self, soup, player_id: str, player_name: str) -> List[CollegeOffer]:
    """
    Extract college offers from player profile.

    DEBUG APPROACH:
    1. Log if offers table found
    2. Log table headers to understand structure
    3. Log number of offers found
    4. For each offer, log school, status, dates
    5. Log any parsing errors with row HTML

    Returns:
        List of CollegeOffer objects
    """
    # Find offers table
    # Extract table headers (understand column structure)
    # For each row:
    #   - Extract school, conference, status, dates
    #   - Determine conference level (POWER_6, MID_MAJOR, LOW_MAJOR)
    #   - Parse offer status (OFFERED, VISITED, COMMITTED, etc.)
    #   - Log all extracted values
    #   - Create CollegeOffer object
```

**Debug Points**:
- [ ] Log offers table HTML structure
- [ ] Log table headers/columns
- [ ] Log number of offers rows
- [ ] For each offer: log school, conference, status, dates
- [ ] Log conference level classification results
- [ ] Log status mapping results
- [ ] Log any unparseable rows with HTML

### Phase 4: Crystal Ball Predictions (New Implementation)

```python
def _parse_crystal_ball(self, soup, player_id: str, player_name: str) -> List[RecruitingPrediction]:
    """
    Extract Crystal Ball predictions from player profile.

    DEBUG APPROACH:
    1. Log if Crystal Ball section found
    2. Log number of predictions found
    3. For each prediction, log expert, school, confidence
    4. Log confidence score conversion (% to 0.0-1.0)
    5. Log any parsing errors

    Returns:
        List of RecruitingPrediction objects
    """
    # Find Crystal Ball section
    # Extract prediction count
    # For each prediction:
    #   - Extract expert name, school, confidence %
    #   - Convert confidence (e.g., "85%" -> 0.85)
    #   - Extract prediction date
    #   - Log all extracted values
    #   - Create RecruitingPrediction object
```

**Debug Points**:
- [ ] Log Crystal Ball section HTML structure
- [ ] Log number of predictions found
- [ ] For each prediction: log expert, school, confidence %
- [ ] Log confidence conversion (85% -> 0.85)
- [ ] Log prediction dates
- [ ] Log any unparseable predictions

### Phase 5: Profile Assembly

```python
async def get_player_recruiting_profile(self, player_id: str) -> Optional[RecruitingProfile]:
    """
    Get comprehensive recruiting profile for a player.

    DEBUG APPROACH:
    1. Log profile request with player_id
    2. Build URL and log result
    3. Fetch page and log response status
    4. Parse each section with debug logging
    5. Assemble profile and log field counts
    6. Log any errors with context
    7. Return profile or None with reason logged
    """
    # Build URL (logged)
    # Fetch page with browser client (logged)
    # Parse rankings (logged)
    # Parse offers (logged)
    # Parse predictions (logged)
    # Assemble RecruitingProfile
    # Log summary (ranks count, offers count, predictions count)
    # Return profile
```

**Debug Points**:
- [ ] Log profile request start
- [ ] Log URL building result
- [ ] Log page fetch status
- [ ] Log section parsing results (counts)
- [ ] Log profile assembly (field values)
- [ ] Log any errors/exceptions with full context
- [ ] Log final profile or None with reason

---

## 🧪 Step 6: Testing Strategy

### Unit Tests

**Test URL Building**:
```python
def test_build_player_profile_url_with_numeric_id():
    # Test: "247_12345" -> correct URL

def test_build_player_profile_url_with_slug():
    # Test: "247_john_doe" -> correct URL

def test_build_player_profile_url_invalid():
    # Test: Invalid format raises ValueError
```

**Test Parsing Functions** (with mock HTML):
```python
def test_parse_player_rankings_complete():
    # Mock HTML with all 5 services
    # Verify: 5 RecruitingRank objects returned

def test_parse_player_offers_multiple():
    # Mock HTML with 10 offers
    # Verify: 10 CollegeOffer objects with correct data

def test_parse_crystal_ball_predictions():
    # Mock HTML with 5 predictions
    # Verify: 5 RecruitingPrediction objects with confidence scores
```

### Integration Tests (Real API Calls)

```python
@pytest.mark.integration
@pytest.mark.skip(reason="ToS compliance - manual testing only")
async def test_get_player_recruiting_profile_real():
    # Use a known top recruit (e.g., #1 ranked player)
    # Verify profile completeness
    # Log all extracted data for manual verification
```

---

## 📝 Step 7: Implementation Checklist

### Pre-Implementation
- [ ] Document URL pattern assumptions
- [ ] Create mock HTML fixtures for testing
- [ ] Define debug logging points
- [ ] Create test plan

### Implementation (Iterative)
- [ ] Implement `_build_player_profile_url()` with debug logging
- [ ] Test URL building with various player_id formats
- [ ] Implement `_parse_player_rankings()` with debug logging
- [ ] Implement `_parse_player_offers()` with debug logging
- [ ] Implement `_parse_crystal_ball()` with debug logging
- [ ] Implement `get_player_recruiting_profile()` with debug logging
- [ ] Test each function individually with mock data
- [ ] Test full integration with manual scraping (ToS permitting)

### Post-Implementation
- [ ] Write unit tests for all functions
- [ ] Write integration test (skipped by default for ToS)
- [ ] Document known limitations
- [ ] Update PROJECT_LOG.md
- [ ] Commit changes with clear message

---

## ⚠️ Known Risks and Mitigations

### Risk 1: URL Pattern Incorrect
**Mitigation**: Try multiple URL patterns, log all attempts, fail gracefully with clear error message

### Risk 2: Page Structure Changed
**Mitigation**: Extensive debug logging, graceful fallback, easy to update selectors

### Risk 3: Anti-Bot Protection
**Mitigation**: Use browser automation (Playwright), conservative rate limiting, respect ToS

### Risk 4: Missing Data on Some Pages
**Mitigation**: Handle missing sections gracefully, return partial profile with warnings

### Risk 5: Date Format Variations
**Mitigation**: Multiple date parsing patterns, log unparseable dates, store as None if can't parse

---

## 🎯 Success Criteria

- [ ] Successfully builds player profile URL from player_id
- [ ] Fetches and parses player profile page without errors
- [ ] Extracts player rankings (at least Composite ranking)
- [ ] Extracts college offers (at least 1 offer if available)
- [ ] Extracts Crystal Ball predictions (if available)
- [ ] Returns valid `RecruitingProfile` object
- [ ] All debug logging points implemented
- [ ] Unit tests pass
- [ ] Integration test works manually (when permitted)

---

## 📊 Expected Impact

**Data Coverage Increase**: +15% (from 31% to 46%)

**New Metrics Extracted**:
1. College offers list (schools, conferences, status, dates)
2. Crystal Ball predictions (experts, schools, confidence scores)
3. Multi-service rankings (ESP, Rivals, On3 in addition to 247Sports)
4. Commitment tracking (school, date)
5. Total offers count

**Forecasting Value**: **HIGH**
- Power 6 offer count is #3 most important predictor (10% importance)
- Crystal Ball confidence is indicator of recruiting buzz
- Multiple service rankings provide validation/consensus

---

**Next Steps**: Begin implementation with Phase 1 (URL building and page fetching) after review and approval.
