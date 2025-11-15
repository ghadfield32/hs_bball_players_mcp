# Implementation Plan: MaxPreps, 247Sports, State Testing, ML Forecasting

**Created**: 2025-11-14
**Status**: Planning Phase
**Estimated Total Time**: 400-600 hours

---

## Overview

This plan outlines the implementation of four major features to enhance the high school basketball player forecasting system:

1. **MaxPreps Scraper** - Universal 50-state stats coverage
2. **247Sports Recruiting Scraper** - College recruiting rankings and predictions
3. **State Association Testing** - Validate 35 skeleton adapters
4. **ML Forecasting Models** - Predict college destinations

---

## Feature 1: MaxPreps Scraper (Priority 1)

### Goals
- Fill 31-state gap in stats coverage
- Provide universal backup for all 50 states
- Extract player stats, team data, schedules

### Technical Approach

**Integration Points:**
- Extends `BaseDataSource` (like SBLive)
- Uses `BrowserClient` for React rendering (similar to EYBL)
- Implements all abstract methods from base adapter
- Uses existing `Player`, `Team`, `Game`, `Stats` models

**URL Patterns:**
```
Base: https://www.maxpreps.com
Stats: /basketball/stat-leaders/
State: /[state abbrev]/basketball/
Player: /athlete/[player-name]/[player-id]
Team: /school/[team-name]/[team-id]/basketball/
```

**Data Available:**
- Player season stats (PPG, RPG, APG, FG%, 3P%, FT%, etc.)
- Player game logs
- Team schedules and scores
- State rankings and leaders
- Grad year, height, weight, position

**Implementation Steps:**
1. Create `src/datasources/us/maxpreps.py`
2. Add DataSourceType.MAXPREPS to models/source.py
3. Add DataSourceRegion entries for all states
4. Implement state-specific URL building
5. Parse player stat tables (HTML structure analysis needed)
6. Parse team schedules
7. Add rate limiting config (conservative: 15 req/min)
8. Add ToS warning in docstrings
9. Create comprehensive tests
10. Update config.py with maxpreps settings

**Efficiency Considerations:**
- Reuse BrowserClient singleton (already implemented)
- Aggressive caching (2-hour TTL for stats pages)
- Batch player lookups where possible
- Avoid redundant network calls

**Estimated Time:** 40-80 hours

**Dependencies:**
- Playwright (already installed)
- BrowserClient (already implemented)
- HTML parsing utils (already implemented)

**Risk:** Terms of Service violation (CBS Sports prohibits scraping)
- **Mitigation**: Add clear warnings, suggest commercial licensing
- **Alternative**: Partner with MaxPreps for API access

---

## Feature 2: 247Sports Recruiting Scraper (Priority 2)

### Goals
- Add recruiting rankings (Top 200+)
- Track college commitments and offers
- Enable forecasting of college destinations
- Provide recruiting context for player evaluation

### Technical Approach

**NEW Models Needed:**
```python
# src/models/recruiting.py

class RecruitingRank(BaseModel):
    """Player recruiting ranking from a service"""
    player_id: str
    player_name: str
    rank_national: Optional[int]  # Overall ranking
    rank_position: Optional[int]   # Position ranking
    rank_state: Optional[int]      # State ranking
    stars: Optional[int]            # Star rating (3-5)
    rating: Optional[float]         # Numerical rating
    service: str                    # "247sports", "espn", "rivals", "on3"
    class_year: int                 # Graduation year
    position: Optional[Position]
    height: Optional[str]
    weight: Optional[int]
    school: Optional[str]
    city: Optional[str]
    state: Optional[str]
    data_source: DataSource

class CollegeOffer(BaseModel):
    """College offer for a player"""
    player_id: str
    player_name: str
    college_name: str
    offer_date: Optional[datetime]
    offer_status: str  # "offered", "committed", "decommitted"
    data_source: DataSource

class RecruitingPrediction(BaseModel):
    """Crystal Ball or similar prediction"""
    player_id: str
    player_name: str
    college_predicted: str
    confidence: Optional[float]  # 0.0 to 1.0
    predictor: str               # Expert name or service
    prediction_date: datetime
    data_source: DataSource
```

**Integration Points:**
- NEW adapter type (not extending BaseDataSource - different interface)
- Create `BaseRecruitingSource` abstract class
- Uses BrowserClient for React pages
- NEW database tables in DuckDB for recruiting data

**URL Patterns:**
```
247Sports:
  Base: https://247sports.com
  Rankings: /season/[year]-basketball/compositerecruitrankings/
  Player: /player/[name]-[id]/

ESPN:
  Base: https://www.espn.com
  Rankings: /mens-college-basketball/recruiting/rankings/_/class/[year]

On3/Rivals:
  Base: https://www.on3.com/rivals
  Rankings: /rankings/player/basketball/[year]/
```

**Implementation Steps:**
1. Create `src/models/recruiting.py` with new models
2. Create `src/datasources/recruiting/` directory
3. Create `src/datasources/recruiting/base_recruiting.py` abstract class
4. Implement `src/datasources/recruiting/247sports.py`
5. Implement `src/datasources/recruiting/espn.py` (optional Phase 2)
6. Implement `src/datasources/recruiting/on3.py` (optional Phase 2)
7. Add DuckDB tables for recruiting data
8. Create aggregator for multi-service rankings
9. Add API endpoints for recruiting data
10. Create comprehensive tests

**DuckDB Schema:**
```sql
CREATE TABLE recruiting_ranks (
    player_uid VARCHAR PRIMARY KEY,
    player_name VARCHAR,
    rank_national INTEGER,
    rank_position INTEGER,
    rank_state INTEGER,
    stars INTEGER,
    rating DOUBLE,
    service VARCHAR,
    class_year INTEGER,
    position VARCHAR,
    height VARCHAR,
    weight INTEGER,
    school VARCHAR,
    state VARCHAR,
    retrieved_at TIMESTAMP
);

CREATE TABLE college_offers (
    id VARCHAR PRIMARY KEY,
    player_uid VARCHAR,
    player_name VARCHAR,
    college_name VARCHAR,
    offer_date TIMESTAMP,
    offer_status VARCHAR,
    retrieved_at TIMESTAMP
);

CREATE TABLE recruiting_predictions (
    id VARCHAR PRIMARY KEY,
    player_uid VARCHAR,
    college_predicted VARCHAR,
    confidence DOUBLE,
    predictor VARCHAR,
    prediction_date TIMESTAMP,
    retrieved_at TIMESTAMP
);
```

**Efficiency Considerations:**
- Scrape rankings pages (bulk data)
- Cache rankings for 24 hours (changes infrequently)
- Batch player profile lookups
- Use identity service to link recruiting data to stats data

**Estimated Time:** 60-100 hours

**Dependencies:**
- BrowserClient (already implemented)
- Identity service (already implemented)
- DuckDB (already implemented)

**Risk:** ToS violation, high scraping maintenance
- **Mitigation**: Respectful scraping, clear warnings
- **Alternative**: Use existing Apify scraper or partner with services

---

## Feature 3: State Association Testing Framework (Priority 3)

### Goals
- Test all 35 skeleton state association adapters
- Identify which states provide actual player stats (vs. only brackets)
- Document data availability per state
- Fix/enhance working adapters

### Technical Approach

**Test Framework:**
```python
# tests/test_state_associations.py

class TestStateAssociations:
    """Comprehensive test suite for state association adapters"""

    @pytest.mark.parametrize("state_adapter_class", [
        AlabamaAhsaaDataSource,
        AlaskaAsaaDataSource,
        # ... all 35 state adapters
    ])
    async def test_adapter_health_check(self, state_adapter_class):
        """Test if state website is accessible"""
        pass

    @pytest.mark.parametrize("state_adapter_class", [
        # ... all 35
    ])
    async def test_adapter_data_extraction(self, state_adapter_class):
        """Test if adapter can extract any data"""
        pass

    # ... more tests
```

**Documentation Template:**
```markdown
# State Association Data Availability Report

## [State Name] - [Association Acronym]

**Website**: [URL]
**Status**: ✅ Working / ⚠️ Partial / ❌ Not Working
**Last Tested**: [Date]

### Data Available:
- [ ] Player season stats
- [ ] Player game stats
- [ ] Team schedules
- [ ] Tournament brackets
- [ ] Team standings
- [ ] Historical data

### Notes:
- [Observations about data quality, format, etc.]

### Recommended Action:
- [Keep as-is / Enhance / Disable / Replace with MaxPreps]
```

**Implementation Steps:**
1. Create `tests/test_state_associations.py`
2. Create `scripts/test_all_state_associations.py` batch runner
3. Create `docs/state_association_report.md` template
4. Run tests on all 35 adapters
5. Document findings for each state
6. Fix adapters with minor issues
7. Disable non-working adapters
8. Update README with state coverage matrix
9. Prioritize high-value states (TX, MI, PA, etc.)

**Test Categories:**
1. **Health Check**: Can we reach the website?
2. **Data Extraction**: Can we find any structured data?
3. **Player Stats**: Do they publish player statistics?
4. **Schedule/Bracket**: Do they publish schedules/brackets?
5. **Data Quality**: Is the data complete and accurate?

**Efficiency Considerations:**
- Run tests in parallel (asyncio.gather)
- Cache test results (avoid re-testing same site)
- Skip slow tests unless explicitly requested
- Use representative sample (not full season scrape)

**Estimated Time:** 100-200 hours
- 2-3 hours per state (website analysis + testing + documentation)
- 35 states × 3 hours = 105 hours base
- Additional time for fixes and enhancements

**Dependencies:**
- Existing state association adapters (already implemented)
- Test infrastructure (already implemented)

---

## Feature 4: ML Forecasting Models (Priority 4)

### Goals
- Predict college level (D1, D2, D3, JUCO, NAIA)
- Predict college destination (if enough data)
- Identify overlooked talent
- Provide confidence scores

### Technical Approach

**NEW Service: ML Forecasting**
```python
# src/services/ml_forecasting.py

class CollegeLevel(str, Enum):
    """NCAA division levels"""
    D1_HIGH_MAJOR = "d1_high_major"    # Power 6 conferences
    D1_MID_MAJOR = "d1_mid_major"      # Other D1
    D1_LOW_MAJOR = "d1_low_major"      # Low D1
    D2 = "d2"
    D3 = "d3"
    NAIA = "naia"
    JUCO = "juco"
    UNKNOWN = "unknown"

class PlayerForecast(BaseModel):
    """ML prediction for a player"""
    player_uid: str
    player_name: str

    # College level prediction
    predicted_level: CollegeLevel
    level_confidence: float  # 0.0 to 1.0
    level_probabilities: Dict[CollegeLevel, float]  # All level probabilities

    # College destination prediction (if available)
    predicted_colleges: Optional[List[str]]  # Top 3 likely colleges
    college_confidence: Optional[float]

    # Feature importance
    top_features: List[Dict[str, float]]  # Which stats drove prediction

    # Model metadata
    model_version: str
    predicted_at: datetime
    data_completeness: float  # % of features available

class MLForecastingService:
    """ML-based forecasting for player college destinations"""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize with trained model or train new one"""
        pass

    async def predict_college_level(
        self,
        player_uid: str
    ) -> PlayerForecast:
        """Predict college level for a player"""
        pass

    async def train_model(
        self,
        training_data: List[Dict],
        target_column: str = "college_level"
    ) -> Dict[str, Any]:
        """Train model on historical data"""
        pass

    def get_feature_importance(self) -> List[Dict[str, float]]:
        """Get feature importance from trained model"""
        pass
```

**Features for Model:**
```python
# Performance Stats (from game data)
- PPG (points per game)
- RPG (rebounds per game)
- APG (assists per game)
- SPG (steals per game)
- BPG (blocks per game)
- FG% (field goal percentage)
- 3P% (three-point percentage)
- FT% (free throw percentage)
- Games played
- Minutes per game
- True shooting %
- Usage rate
- Assist-to-turnover ratio
- Player efficiency rating

# Physical Attributes
- Height (inches)
- Weight (lbs)
- Position (encoded)

# Academic/Timeline
- Grad year (year relative to current)
- Age

# Competition Level
- Plays AAU (binary: EYBL/3SSB/UAA)
- AAU stats (if applicable)
- State ranking (if available)

# Recruiting Data (if available)
- 247Sports ranking
- Composite ranking
- Star rating
- Number of D1 offers
- High major offers (binary)

# Contextual
- State (encoded - basketball talent density)
- School (encoded - program strength)
- Data completeness score
```

**Model Selection:**
```python
# Classification: College Level
# Algorithms to test:
1. Random Forest (good baseline, feature importance)
2. XGBoost (likely best performance)
3. LightGBM (faster, similar performance)
4. Neural Network (if enough data, >10k players)

# Regression: College Ranking
# (Predict numerical ranking of college program)

# Multi-output: Level + College
```

**Training Data Sources:**
1. **Historical Recruiting Data**:
   - Scrape past 5-10 years of 247Sports rankings
   - Match with where players actually went
   - Create ground truth dataset

2. **Current College Rosters**:
   - Scrape current D1/D2/D3 rosters
   - Find their high school stats (if available)
   - Label with college level

3. **Transfer Portal Data**:
   - Players who transferred (data quality indicator)

**Implementation Steps:**
1. Create `src/models/forecasting.py` with ML-specific models
2. Create `src/services/ml_forecasting.py` service
3. Create `scripts/collect_training_data.py` to build dataset
4. Create `scripts/train_forecasting_model.py` training pipeline
5. Implement feature engineering pipeline
6. Train and evaluate multiple models
7. Select best model and save
8. Create prediction API endpoints
9. Add model versioning and retraining pipeline
10. Create comprehensive tests

**Evaluation Metrics:**
- Accuracy (overall)
- Precision/Recall per class (D1, D2, D3, etc.)
- AUC-ROC curve
- Confusion matrix
- Feature importance analysis

**Efficiency Considerations:**
- Pre-compute features and cache
- Use model inference caching (same input = cached result)
- Batch predictions where possible
- Use lightweight models (Random Forest, not deep NN)
- Feature selection to reduce dimensionality

**Estimated Time:** 100-200 hours
- Data collection: 40-60 hours
- Feature engineering: 20-30 hours
- Model training/tuning: 30-50 hours
- API integration: 20-30 hours
- Testing/validation: 20-30 hours

**Dependencies:**
- scikit-learn (new)
- xgboost or lightgbm (new)
- pandas (likely already installed)
- numpy (likely already installed)
- Historical recruiting data (need to collect)

---

## Implementation Order & Phasing

### Phase 1: Immediate Value (Weeks 1-4)
**Priority**: MaxPreps + Recruiting Models
1. Create recruiting data models (Week 1)
2. Implement MaxPreps adapter (Weeks 1-2)
3. Test MaxPreps on 10 high-priority states (Week 2)
4. Create 247Sports adapter (Weeks 3-4)

**Deliverable**: 50-state stats coverage + recruiting rankings data

### Phase 2: Validation & Quality (Weeks 5-8)
**Priority**: State Association Testing
1. Create test framework (Week 5)
2. Run tests on all 35 states (Weeks 6-7)
3. Document findings and prioritize fixes (Week 7)
4. Fix high-value state adapters (Week 8)

**Deliverable**: Validated state coverage, documented data availability

### Phase 3: Intelligence Layer (Weeks 9-16)
**Priority**: ML Forecasting
1. Collect historical training data (Weeks 9-10)
2. Feature engineering and data preparation (Weeks 11-12)
3. Model training and evaluation (Weeks 13-14)
4. API integration and testing (Weeks 15-16)

**Deliverable**: Working ML model predicting college level

### Phase 4: Refinement (Weeks 17+)
**Priority**: Improvements and Scale
1. Expand MaxPreps coverage (all 50 states)
2. Add ESPN/On3 recruiting scrapers
3. Improve ML model with more data
4. Add college destination prediction

---

## Risk Mitigation

### Legal/ToS Risks
**Risk**: MaxPreps and recruiting sites prohibit scraping
**Mitigation**:
- Add clear ToS warnings in docstrings
- Implement respectful scraping (rate limiting, caching)
- Suggest commercial licensing as primary option
- Document legal alternatives

### Technical Risks
**Risk**: Website structure changes break scrapers
**Mitigation**:
- Comprehensive error handling
- Monitoring and alerts for scraper failures
- Version control for HTML structure
- Fallback to alternative sources

### Data Quality Risks
**Risk**: Scraped data is incomplete or inaccurate
**Mitigation**:
- Extensive validation (Pydantic models)
- Data quality flags (COMPLETE, PARTIAL, SUSPECT)
- Manual spot-checking of results
- Cross-reference multiple sources

### Performance Risks
**Risk**: Scraping is too slow or resource-intensive
**Mitigation**:
- Browser instance pooling (already implemented)
- Aggressive caching (already implemented)
- Parallel requests where possible
- Optimize for batch operations

---

## Success Criteria

### MaxPreps Scraper
- ✅ Successfully scrapes 50 states
- ✅ Extracts player stats with >90% accuracy
- ✅ Runs within rate limits
- ✅ Comprehensive test coverage

### 247Sports Scraper
- ✅ Scrapes Top 200 rankings
- ✅ Tracks commitments and offers
- ✅ Updates recruiting data daily
- ✅ Links to player stats via identity service

### State Association Testing
- ✅ All 35 adapters tested and documented
- ✅ Working adapters identified and validated
- ✅ Non-working adapters disabled or replaced
- ✅ Coverage report published

### ML Forecasting
- ✅ Model accuracy >75% for college level prediction
- ✅ Feature importance analysis available
- ✅ API endpoints functional
- ✅ Confidence scores provided

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize features** based on business value
3. **Allocate resources** (developer time, infrastructure)
4. **Begin Phase 1** implementation (MaxPreps + Recruiting models)
5. **Set up monitoring** for scraper health and data quality

---

**End of Implementation Plan**
