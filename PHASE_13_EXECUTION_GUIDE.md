# Phase 13 Execution Guide

**Phase**: Template Adapter Activation + Validation
**Priority**: High (completes pre-college/pre-EuroLeague coverage)
**Estimated Time**: 10-20 hours (2-4 hours per adapter)

---

## 📋 Phase 13 Objectives

1. ✅ Install dependencies and verify environment
2. ✅ Run categorical validation tests (verify 25 tests pass)
3. ✅ Activate 3 HIGH-priority template adapters
4. ⏳ Activate 2 MEDIUM-priority template adapters (optional)
5. ✅ Update documentation and PROJECT_LOG

---

## 🚀 Quick Start

### Step 1: Verify Dependencies

```bash
# Check if all dependencies are installed
python scripts/verify_dependencies.py

# If missing dependencies, install them
pip install -r requirements.txt
```

**Expected Output**: ✅ All dependencies installed!

---

### Step 2: Run Validation Tests

```bash
# Run all 25 categorical validation tests
python scripts/run_validation_tests.py

# Or use pytest directly
pytest tests/test_unified/test_categorical_validation.py -v
```

**Expected Output**: ✅ ALL TESTS PASSED (25/25)

**If Tests Fail**: Check the error messages for:
- Missing sources in CIRCUIT_KEYS
- Missing sources in SOURCE_TYPES
- Type mismatches (CIRCUIT vs ASSOCIATION vs EVENT)
- Duplicate circuit keys

---

### Step 3: Activate Template Adapters

**Recommended Order** (HIGH priority first):
1. ANGT (Europe U18 elite)
2. OSBA (Canada prep)
3. PlayHQ (Australia)
4. OTE (US prep) - optional
5. Grind Session (US events) - optional

**For each adapter**, use the activation helper:

```bash
# Show adapter information and checklist
python scripts/activate_template.py angt

# This will display:
# - Adapter details (name, region, priority)
# - 12-step activation checklist
# - Next steps
```

---

## 📝 Detailed Activation Process

### Example: Activating ANGT

#### 1. Get Adapter Information

```bash
python scripts/activate_template.py angt
```

**Output**:
```
==================================================================
TEMPLATE ADAPTER: ANGT
==================================================================

Full Name:    Adidas Next Generation Tournament
Region:       Europe
Priority:     HIGH
Description:  Europe U18 elite tournament

Base URL:     https://www.euroleaguebasketball.net/next-generation
Adapter File: src/datasources/europe/angt.py
Test File:    tests/test_datasources/test_angt.py

ACTIVATION CHECKLIST
------------------------------------------------------------------

   1. [ ] Visit https://www.euroleaguebasketball.net/next-generation
   2. [ ] Inspect HTML structure for stats tables
   3. [ ] Identify URL patterns (/competition, /players, /games)
   4. [ ] Note column names (Player, Team, Points, PIR)
   5. [ ] Check robots.txt permissions
   6. [ ] Update URLs in src/datasources/europe/angt.py (lines ~78-85)
   7. [ ] Update column mapping if needed
   8. [ ] Create test file: tests/test_datasources/test_angt.py
   9. [ ] Run tests: pytest tests/test_datasources/test_angt.py -v
  10. [ ] Uncomment in src/services/aggregator.py
  11. [ ] Update config/sources.yaml: template → active
  12. [ ] Update PROJECT_LOG.md with activation details
```

#### 2. Website Inspection

Visit the website and document:
- **Stats URL**: e.g., `https://www.euroleaguebasketball.net/next-generation/competition/2024-25/statistics`
- **Players URL**: e.g., `https://www.euroleaguebasketball.net/next-generation/competition/2024-25/players`
- **Column Names**: Player, Team, GP (games played), Points, PIR (Performance Index Rating)
- **Season Format**: 2024-25 (YYYY-YY)

#### 3. Update Adapter URLs

**File**: `src/datasources/europe/angt.py`

**BEFORE** (template placeholders):
```python
# TODO: Replace with actual ANGT URLs
self.competition_url = f"{self.base_url}/competition"  # UPDATE AFTER INSPECTION
self.stats_url = f"{self.base_url}/stats"  # UPDATE AFTER INSPECTION
self.players_url = f"{self.base_url}/players"  # UPDATE AFTER INSPECTION
```

**AFTER** (with actual URLs):
```python
# Actual ANGT URLs (verified 2025-11-12)
self.competition_url = f"{self.base_url}/competition/{self.current_season}"
self.stats_url = f"{self.base_url}/competition/{self.current_season}/statistics"
self.players_url = f"{self.base_url}/competition/{self.current_season}/players"
self.teams_url = f"{self.base_url}/competition/{self.current_season}/teams"
self.games_url = f"{self.base_url}/competition/{self.current_season}/games"
```

#### 4. Update Column Mapping (if needed)

**File**: `src/datasources/europe/angt.py` (in parsing methods)

```python
# Verify and update column names based on actual website
column_map = {
    "Player": "player_name",
    "Team": "team",
    "GP": "games_played",  # May need adjustment
    "Points": "points",
    "Rebounds": "rebounds",
    "Assists": "assists",
    "PIR": "pir",  # Performance Index Rating (EuroLeague metric)
}
```

#### 5. Create Test File

**File**: `tests/test_datasources/test_angt.py`

```python
"""
Tests for ANGT DataSource Adapter

Covers initialization, health checks, player search, stats, and leaderboards.
"""

import pytest
from src.datasources.europe.angt import ANGTDataSource


@pytest.fixture
async def angt():
    """Create ANGT datasource instance."""
    source = ANGTDataSource()
    yield source
    await source.close()


@pytest.mark.asyncio
async def test_angt_initialization(angt):
    """Test ANGT adapter initializes correctly."""
    assert angt.source_name == "ANGT (Next Generation)"
    assert angt.base_url == "https://www.euroleaguebasketball.net/next-generation"
    assert angt.region.value == "EUROPE"


@pytest.mark.asyncio
async def test_angt_health_check(angt):
    """Test ANGT health check."""
    is_healthy = await angt.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_angt_search_players(angt):
    """Test searching for players."""
    players = await angt.search_players(name="", limit=10)

    assert len(players) > 0, "Should return at least 1 player"
    assert players[0].player_id.startswith("angt_"), "Player ID should have angt_ prefix"
    assert players[0].full_name, "Player should have a name"


@pytest.mark.asyncio
async def test_angt_get_player_season_stats(angt):
    """Test getting player season stats."""
    # First, search for a player
    players = await angt.search_players(limit=1)

    if players:
        player_id = players[0].player_id
        stats = await angt.get_player_season_stats(player_id)

        if stats:  # Stats may not be available for all players
            assert stats.player_id == player_id
            assert stats.games_played is not None


@pytest.mark.asyncio
async def test_angt_get_leaderboard(angt):
    """Test getting leaderboard."""
    leaderboard = await angt.get_leaderboard(stat="points", limit=10)

    assert len(leaderboard) > 0, "Should return leaderboard entries"
    assert "player_name" in leaderboard[0]
    assert "stat_value" in leaderboard[0]


@pytest.mark.asyncio
async def test_angt_id_format(angt):
    """Test player ID format is consistent."""
    players = await angt.search_players(limit=5)

    for player in players:
        assert player.player_id.startswith("angt_"), f"Invalid ID format: {player.player_id}"


# Add more tests as needed
```

#### 6. Run Tests

```bash
# Run ANGT tests only
pytest tests/test_datasources/test_angt.py -v

# Expected output: All tests pass
```

#### 7. Uncomment in Aggregator

**File**: `src/services/aggregator.py`

**BEFORE**:
```python
# "angt": ANGTDataSource,  # TODO: Update URLs after inspection
```

**AFTER**:
```python
"angt": ANGTDataSource,  # Europe U18 elite tournament
```

#### 8. Update sources.yaml

**File**: `config/sources.yaml`

**BEFORE**:
```yaml
- id: angt
  name: "ANGT"
  status: template
```

**AFTER**:
```yaml
- id: angt
  name: "ANGT"
  status: active
```

#### 9. Update PROJECT_LOG.md

**File**: `PROJECT_LOG.md`

Add new section under "COMPLETED (Continued)":

```markdown
#### [2025-11-12 08:00] Phase 13.1: ANGT Template Activation
- ✅ Verified URLs at https://www.euroleaguebasketball.net/next-generation
- ✅ Updated adapter endpoints (/competition/2024-25/statistics)
- ✅ Verified column names (Player, Team, Points, PIR)
- ✅ Created test suite (12 tests) - all passing
- ✅ Uncommented in aggregator (30 → 31 active adapters)
- ✅ Updated sources.yaml status: template → active
- Impact: +1 active adapter, Europe U18 coverage complete
```

#### 10. Commit Changes

```bash
# Stage files
git add src/datasources/europe/angt.py \
        tests/test_datasources/test_angt.py \
        src/services/aggregator.py \
        config/sources.yaml \
        PROJECT_LOG.md

# Commit
git commit -m "Phase 13.1: Activate ANGT template adapter

- Updated URLs after website verification
- Created comprehensive test suite (12 tests)
- Uncommented in aggregator (30 → 31 active)
- Updated sources.yaml: template → active
- Europe U18 coverage complete"

# Push
git push
```

---

## 🔄 Repeat for Each Adapter

Follow the same 10-step process for:
- OSBA (Canada prep)
- PlayHQ (Australia)
- OTE (US prep) - optional
- Grind Session (US events) - optional

**Helper Command for Each**:
```bash
python scripts/activate_template.py osba
python scripts/activate_template.py playhq
python scripts/activate_template.py ote
python scripts/activate_template.py grind_session
```

---

## 📊 Progress Tracking

### Checklist

- [ ] Dependencies verified (25 test passed)
- [ ] Validation tests passing (25/25)
- [ ] ANGT activated (Europe U18)
- [ ] OSBA activated (Canada prep)
- [ ] PlayHQ activated (Australia)
- [ ] OTE activated (US prep) - optional
- [ ] Grind Session activated (US events) - optional
- [ ] PROJECT_LOG updated
- [ ] All changes committed and pushed

### Active Adapters Progression

- **Phase 12 Start**: 29 active adapters
- **After ANGT**: 30 active adapters (+1)
- **After OSBA**: 31 active adapters (+2)
- **After PlayHQ**: 32 active adapters (+3)
- **After OTE**: 33 active adapters (+4) - optional
- **After Grind Session**: 34 active adapters (+5) - optional

---

## 🛠️ Tools Created for Phase 13

### 1. Dependency Verifier
**File**: `scripts/verify_dependencies.py`
**Usage**: `python scripts/verify_dependencies.py`
**Purpose**: Verify all dependencies are installed

### 2. Template Activation Helper
**File**: `scripts/activate_template.py`
**Usage**: `python scripts/activate_template.py <adapter>`
**Purpose**: Show adapter info and activation checklist

### 3. Validation Test Runner
**File**: `scripts/run_validation_tests.py`
**Usage**: `python scripts/run_validation_tests.py`
**Purpose**: Run categorical validation tests

---

## ⚠️ Common Issues & Solutions

### Issue: pytest not found
**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Website requires JavaScript
**Solution**: Enable browser automation in adapter:
```python
self.requires_browser = True
```

### Issue: Different column names
**Solution**: Update column mapping in parsing methods

### Issue: Rate limiting (429 errors)
**Solution**: Reduce rate limit in sources.yaml:
```yaml
rate_limit:
  requests_per_minute: 15  # Reduce if needed
```

### Issue: Geo-restricted content
**Solution**: Document in sources.yaml notes, may require VPN/proxy

---

## 📈 Success Metrics

### Phase 13 Complete When:
1. ✅ All 25 validation tests passing
2. ✅ Minimum 3 template adapters activated (ANGT, OSBA, PlayHQ)
3. ✅ All activated adapters have passing tests
4. ✅ Aggregator includes all activated adapters
5. ✅ sources.yaml updated for all activated adapters
6. ✅ PROJECT_LOG documents all activations

### Optional Success (Stretch Goals):
7. ⏳ All 5 template adapters activated
8. ⏳ Auto-export daemon deployed
9. ⏳ Research initiated on 2+ high-priority sources

---

## 📞 Next Actions After Phase 13

1. **Phase 14**: Research & Implement High-Priority Sources
   - NIBC (elite prep league)
   - WCAC (DC-area prep)
   - Basketball England (EABL/WEABL)

2. **Phase 15**: Engineering Enhancements
   - School dictionary (NCES integration)
   - Player dimension build
   - ML categorical encoding validation

3. **Production Deployment**:
   - Deploy auto-export daemon
   - Set up monitoring
   - Configure backups

---

## 📚 Reference Documentation

- **Template Activation Guide**: `docs/TEMPLATE_ADAPTER_ACTIVATION.md`
- **Phase 12 Verification**: `PHASE_12_VERIFICATION.md`
- **Project Log**: `PROJECT_LOG.md`
- **Sources Registry**: `config/sources.yaml`

---

**Last Updated**: 2025-11-12
**Status**: Phase 13 tools created, ready for execution
**Estimated Completion**: 10-20 hours (2-4 hours per adapter)
