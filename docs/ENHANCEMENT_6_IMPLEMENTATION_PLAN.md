# Enhancement 6: Offensive/Defensive Rebounding Split - Implementation Plan

**Enhancement**: ORB/DRB Split (+2% Coverage)
**Status**: Implementation in Progress
**Date**: 2025-11-15
**Estimated Time**: 0.5 days (4 hours)

---

## Step 1: Existing Code Analysis

### Current State - Models ✅

**GOOD NEWS**: Models already have ORB/DRB fields defined!

**BaseStats** (`src/models/stats.py:38-44`):
```python
# Rebounds
offensive_rebounds: Optional[int] = Field(default=None, ge=0, description="Offensive rebounds")
defensive_rebounds: Optional[int] = Field(default=None, ge=0, description="Defensive rebounds")
total_rebounds: Optional[int] = Field(default=None, ge=0, description="Total rebounds")
```

These fields are TOTALS (not per-game) and are inherited by both:
- `PlayerGameStats` (game-by-game stats)
- `PlayerSeasonStats` (season aggregates)

**PlayerSeasonStats** (`src/models/stats.py:192`):
```python
rebounds_per_game: Optional[float] = Field(default=None, ge=0, description="Rebounds per game")
```

**GAP IDENTIFIED**: Missing `offensive_rebounds_per_game` and `defensive_rebounds_per_game` fields

### Current State - Datasources

**✅ NPA (Canada)** - Extracting but with WRONG field names:
- Extracts: `offensive_rebounds_per_game`, `defensive_rebounds_per_game`
- Bug: These don't match model fields (should be totals, not per-game in BaseStats)
- Source columns: `ORPG`/`ORB` and `DRPG`/`DRB`

**❌ EYBL, UAA, 3SSB** - Only extracting total rebounds:
- Extracts: `rebounds_per_game` only
- Missing: ORB/DRB split (may be available in source data)

**❌ MaxPreps Enhanced Parser** - Explicitly sets to None:
- Line 364-365: `offensive_rebounds=None, defensive_rebounds=None`
- Comment: "Not typically provided"

**❌ All other datasources** - Not extracting ORB/DRB

---

## Step 2: Efficiency Analysis

### What We Can Leverage

1. **Models already defined** - No schema changes needed for totals
2. **NPA already extracts data** - Just need to fix field mapping
3. **BaseStats inheritance** - All stats models get ORB/DRB fields automatically
4. **Computed fields pattern** - Can add per-game calculations

### Optimization Opportunities

1. **Add per-game fields** to PlayerSeasonStats (consistent with existing pattern)
2. **Reuse parsing utilities** - `parse_int()`, `parse_float()` already exist
3. **Column name patterns** - Standard abbreviations: ORB/ORPG, DRB/DRPG, OREB/DREB
4. **Estimation fallback** - When unavailable, can estimate from total (typically 25% ORB, 75% DRB)

---

## Step 3: Efficient Code Design

### Minimal Changes Needed

**Priority 1: Model Enhancement (1 change)**
- Add 2 fields to `PlayerSeasonStats`: `offensive_rebounds_per_game`, `defensive_rebounds_per_game`

**Priority 2: Fix Existing Bug (1 change)**
- Fix NPA datasource to use correct field names

**Priority 3: Extract Where Available (3-5 changes)**
- EYBL, EYBL Girls, UAA, UAA Girls, 3SSB, 3SSB Girls
- Check if ORB/DRB columns exist in their data
- Extract if available using standard column name pattern

**Priority 4: Estimation Helper (Optional, for Phase 2)**
- Create utility function to estimate ORB/DRB from total when split unavailable
- Use league averages: ~25% offensive, ~75% defensive

---

## Step 4: Integration Plan

### Change 1: Enhance PlayerSeasonStats Model

**File**: `src/models/stats.py`
**Line**: After line 192 (after `rebounds_per_game`)

**Add**:
```python
offensive_rebounds_per_game: Optional[float] = Field(
    default=None, ge=0, description="Offensive rebounds per game"
)
defensive_rebounds_per_game: Optional[float] = Field(
    default=None, ge=0, description="Defensive rebounds per game"
)
```

**Why**: Consistent with existing pattern of having both totals (from BaseStats) and per-game values

**Dependencies**: None - pure addition

### Change 2: Fix NPA Datasource Field Mapping

**File**: `src/datasources/canada/npa.py`
**Function**: `_parse_player_stats_from_row()` around line 334-356

**Current (BUGGY)**:
```python
offensive_reb = parse_float(row.get("ORPG") or row.get("ORB"))
defensive_reb = parse_float(row.get("DRPG") or row.get("DRB"))

stats = {
    "offensive_rebounds_per_game": offensive_reb,  # WRONG - no such field
    "defensive_rebounds_per_game": defensive_reb,  # WRONG - no such field
}
```

**Fix**:
```python
# Extract ORB/DRB (check if totals or per-game based on column name)
orb_per_game = parse_float(row.get("ORPG"))
drb_per_game = parse_float(row.get("DRPG"))
orb_total = parse_float(row.get("ORB")) if not orb_per_game else None
drb_total = parse_float(row.get("DRB")) if not drb_per_game else None

# Calculate totals from per-game if needed
games = parse_int(row.get("GP") or row.get("G") or row.get("Games"))
if orb_per_game and games:
    orb_total = orb_per_game * games
if drb_per_game and games:
    drb_total = drb_per_game * games

stats = {
    # Totals (BaseStats fields)
    "offensive_rebounds": orb_total,
    "defensive_rebounds": drb_total,

    # Per-game (PlayerSeasonStats fields - after we add them)
    "offensive_rebounds_per_game": orb_per_game or (orb_total / games if orb_total and games else None),
    "defensive_rebounds_per_game": drb_per_game or (drb_total / games if drb_total and games else None),
}
```

### Change 3: Add ORB/DRB to EYBL Datasource

**File**: `src/datasources/us/eybl.py`
**Function**: `_parse_player_stats_from_row()` around line 300

**Add** (after total rebounds extraction):
```python
# Total rebounds (existing)
total_rebs = parse_float(row.get("RPG") or row.get("REB"))

# ORB/DRB split (new - check if available)
orb = parse_float(row.get("ORPG") or row.get("ORB"))
drb = parse_float(row.get("DRPG") or row.get("DRB"))

# Add to stats dict
stats = {
    "rebounds_per_game": total_rebs,
    "offensive_rebounds_per_game": orb,  # New
    "defensive_rebounds_per_game": drb,  # New
}
```

**Repeat for**: EYBL Girls, UAA, UAA Girls, 3SSB, 3SSB Girls (same pattern)

### Change 4: Create Estimation Helper (Optional - Phase 2)

**File**: `src/utils/advanced_stats.py`
**Add new function**:

```python
def estimate_orb_drb_split(
    total_rebounds: Optional[float],
    games_played: Optional[int] = None,
    orb_percentage: float = 0.25
) -> tuple[Optional[float], Optional[float]]:
    """
    Estimate ORB/DRB split from total rebounds when split unavailable.

    Uses league average percentages (typically ~25% ORB, ~75% DRB).

    Args:
        total_rebounds: Total rebounds (season total or per-game)
        games_played: Games played (if total_rebounds is season total)
        orb_percentage: Offensive rebound percentage (default 0.25)

    Returns:
        Tuple of (estimated_orb, estimated_drb)
    """
    if total_rebounds is None:
        return (None, None)

    estimated_orb = total_rebounds * orb_percentage
    estimated_drb = total_rebounds * (1 - orb_percentage)

    return (round(estimated_orb, 1), round(estimated_drb, 1))
```

**Usage**: Can be called in datasources when ORB/DRB not available but total rebounds is

---

## Step 5: Implementation Steps (Incremental)

### Step 5a: Add Per-Game Fields to Model ✅ READY
1. Edit `src/models/stats.py`
2. Add 2 new fields after line 192
3. Update example in Config to include new fields
4. No breaking changes - all fields are Optional

### Step 5b: Fix NPA Datasource ✅ READY
1. Edit `src/datasources/canada/npa.py`
2. Fix field mapping (line 355-356)
3. Handle both total and per-game column names
4. Calculate missing values from available data

### Step 5c: Update EYBL Adapters 🔄 CONDITIONAL
1. Check if EYBL data includes ORB/DRB columns (may need manual inspection)
2. If yes: Add extraction like Change 3
3. If no: Leave as total_rebounds only (no regression)
4. Repeat for all 6 national circuit adapters

### Step 5d: Update Other Major Datasources 🔄 CONDITIONAL
1. MaxPreps: Check if ORB/DRB available in HTML (currently marked "not typically provided")
2. State associations: Most don't provide split, skip for now
3. International: FIBA may have split, check if available

### Step 5e: Add Estimation Helper ⏳ OPTIONAL (Phase 2)
1. Add function to `src/utils/advanced_stats.py`
2. Export in `src/utils/__init__.py`
3. Use in datasources where total available but split not available

---

## Step 6: Documentation

**Comments in Code**:
- Add comment explaining ORB/DRB fields in model
- Document column name variations in datasources
- Explain estimation logic if used

**Inline Documentation**:
- Update PlayerSeasonStats docstring to mention ORB/DRB per-game fields
- Add examples showing ORB/DRB values

---

## Step 7: Testing Strategy

### Unit Tests

**Test Model**:
```python
def test_player_season_stats_orb_drb():
    stats = PlayerSeasonStats(
        player_id="test",
        player_name="Test Player",
        season="2024-25",
        games_played=20,
        offensive_rebounds=50,  # Total
        defensive_rebounds=150,  # Total
        offensive_rebounds_per_game=2.5,  # Per-game
        defensive_rebounds_per_game=7.5,  # Per-game
    )
    assert stats.offensive_rebounds == 50
    assert stats.defensive_rebounds == 150
    assert stats.total_rebounds == 200  # Should auto-calculate?
```

**Test Estimation Function**:
```python
def test_estimate_orb_drb_split():
    orb, drb = estimate_orb_drb_split(10.0)  # 10 RPG
    assert orb == 2.5  # 25%
    assert drb == 7.5  # 75%
```

### Integration Tests

**Test NPA Datasource**:
```python
@pytest.mark.integration
async def test_npa_extracts_orb_drb():
    # Test that NPA correctly extracts and maps ORB/DRB
    # Verify field names match model
```

**Test EYBL (if ORB/DRB available)**:
```python
@pytest.mark.integration
async def test_eybl_extracts_orb_drb():
    # Test EYBL ORB/DRB extraction if columns exist
```

---

## Step 8: Changed Functions (Full Implementations)

### File: src/models/stats.py

**Function**: `PlayerSeasonStats` class (lines 172-242)

**Change**: Add 2 new fields after line 192

### File: src/datasources/canada/npa.py

**Function**: `_parse_player_stats_from_row()` (lines ~280-360)

**Change**: Fix offensive_rebounds/defensive_rebounds field mapping

### File: src/datasources/us/eybl.py (IF ORB/DRB available)

**Function**: `_parse_player_stats_from_row()` (lines ~260-310)

**Change**: Add ORB/DRB extraction

---

## Step 9: Pipeline Updates

**No Function Renames Needed** - All changes are:
1. Adding new fields (non-breaking)
2. Fixing bug in existing datasource
3. Enhancing extraction (backward compatible)

**Existing Pipeline Compatibility**:
- All new fields are Optional - no breaking changes
- Existing code continues to work
- New data available when sources provide it

---

## Step 10: PROJECT_LOG Entry (Compact Format)

```markdown
#### [2025-11-15 15:00] Enhancement 6: Offensive/Defensive Rebounding Split (+2% Coverage)
- ✅ Added offensive_rebounds_per_game, defensive_rebounds_per_game to PlayerSeasonStats (src/models/stats.py)
- ✅ Fixed NPA datasource field mapping bug (src/datasources/canada/npa.py, used wrong field names)
- ✅ Updated EYBL adapters to extract ORB/DRB when available (src/datasources/us/eybl*.py, uaa*.py, three_ssb*.py)
- 🔄 Created estimation helper for ORB/DRB split (src/utils/advanced_stats.py, Phase 2 - optional)
- Impact: +2% coverage, enables motor/effort analysis via ORB rate
```

---

## Expected Impact

**Data Coverage**: +2% (31% → 33% or 46% → 48% after Enhancement 2)

**New Metrics Available**:
1. Offensive rebounds per game (ORB/g)
2. Defensive rebounds per game (DRB/g)
3. Offensive rebound rate (ORB / total team misses)
4. Defensive rebound rate (DRB / opponent team misses)

**Forecasting Value**: **MEDIUM**
- ORB rate indicates motor, effort, athleticism
- DRB rate indicates positioning, defensive awareness
- ORB/DRB ratio can indicate playing style
- High ORB% correlates with NBA success for bigs

**Data Sources Affected**:
- ✅ NPA (bug fix)
- 🔄 EYBL, UAA, 3SSB (if data available)
- ⏳ Others (Phase 2 if data available)

---

## Risk Assessment

**Risk**: ORB/DRB data may not be available in all sources
**Mitigation**: Make all fields Optional, graceful handling of missing data

**Risk**: Estimation may be inaccurate for individual players
**Mitigation**: Only estimate when explicitly requested, mark as estimated

**Risk**: Breaking changes if field names wrong
**Mitigation**: All new fields Optional, extensive testing before merge

---

## Success Criteria

- [ ] Model fields added successfully
- [ ] NPA datasource bug fixed
- [ ] At least 1 national circuit (EYBL/UAA/3SSB) extracts ORB/DRB
- [ ] Tests pass
- [ ] No breaking changes to existing functionality
- [ ] PROJECT_LOG updated

---

**Next Action**: Begin implementation with Step 5a (Add model fields)
