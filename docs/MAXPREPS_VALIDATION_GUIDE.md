# MaxPreps Validation & Testing Guide

**Created**: 2025-11-14
**Status**: Ready for Manual Testing
**Purpose**: Guide for validating MaxPreps adapter and metrics extraction

---

## ⚠️ LEGAL COMPLIANCE WARNING

**IMPORTANT**: MaxPreps (CBS Sports Interactive) Terms of Service **prohibit automated scraping**.

This validation should ONLY be performed:
1. **With explicit permission** from MaxPreps/CBS Sports
2. **For educational/research purposes** (fair use)
3. **With commercial data license** (recommended for production use)

**Contact MaxPreps**:
- Email: coachsupport@maxpreps.com
- Phone: 800-329-7324
- Request: Commercial data licensing or API access

---

## Overview

The MaxPreps adapter has been enhanced to extract comprehensive statistics from stat leader pages across all 50 US states + DC.

### What's Been Implemented

**Phase 13.2 (Completed)**:
- ✅ Basic MaxPreps adapter with 51-state support
- ✅ Player search functionality
- ✅ State validation and URL building
- ✅ Browser automation for React rendering

**Phase 13.2.1 (Enhanced - Ready for Testing)**:
- ✅ Enhanced parser to extract ALL available metrics
- ✅ Validation script for testing
- ✅ Documentation of expected metrics

### What Needs Testing

**Manual validation required** to:
1. Verify MaxPreps HTML structure
2. Identify actual available columns
3. Test parser with real data
4. Adjust column mappings if needed

---

## Expected MaxPreps Metrics

Based on typical high school basketball stat leader pages, MaxPreps likely provides:

### Player Demographics
- **Player Name** ✓ Currently extracted
- **School** ✓ Currently extracted
- **Class/Grad Year** ✓ Currently extracted
- **Position** ✓ Currently extracted
- **Height** ✓ Currently extracted
- **Weight** ✓ Currently extracted

### Season Statistics (NEW)
- **GP** (Games Played) - NEW
- **PPG** (Points Per Game) - NEW
- **RPG** (Rebounds Per Game) - NEW
- **APG** (Assists Per Game) - NEW
- **SPG** (Steals Per Game) - NEW
- **BPG** (Blocks Per Game) - NEW
- **FG%** (Field Goal Percentage) - NEW
- **3P%** (Three Point Percentage) - NEW
- **FT%** (Free Throw Percentage) - NEW
- **MPG** (Minutes Per Game) - NEW (maybe)
- **TPG** (Turnovers Per Game) - NEW (maybe)

### Volume Stats (if available)
- **Total Points** (season total)
- **Total Rebounds** (season total)
- **Total Assists** (season total)
- **Total Steals** (season total)
- **Total Blocks** (season total)

---

## Validation Steps

### Step 1: Run Validation Script

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Run validation for one state
python scripts/validate_maxpreps.py --state CA --limit 5

# Run multi-state comparison
python scripts/validate_maxpreps.py --compare
```

**Expected Output**:
- Console output showing available columns
- HTML snapshot saved to `data/validation/maxpreps_ca_sample.html`
- JSON report saved to `data/validation/maxpreps_ca_metrics.json`

### Step 2: Analyze Validation Results

**Review the JSON report**:
```bash
cat data/validation/maxpreps_ca_metrics.json
```

**Key fields to check**:
- `"status"`: Should be `"success"`
- `"html_columns"`: List of actual column names from MaxPreps
- `"available_metrics"`: Identified stat columns
- `"recommendations"`: What to do next

**Review the HTML snapshot**:
```bash
open data/validation/maxpreps_ca_sample.html  # Mac
# OR
start data/validation/maxpreps_ca_sample.html  # Windows
```

### Step 3: Adjust Parser (If Needed)

If column names don't match expectations, update the parser in:
`src/datasources/us/maxpreps_enhanced_parser.py`

**Example**: If MaxPreps uses "Pts/Game" instead of "PPG":

```python
# In _parse_player_and_stats_from_row():

# OLD:
ppg = parse_float(row.get("PPG") or row.get("Points"))

# NEW:
ppg = parse_float(
    row.get("PPG") or
    row.get("Points") or
    row.get("Pts/Game") or  # Add new column name
    row.get("Pts/G")
)
```

### Step 4: Test Enhanced Parser

```python
# Test script (create as scripts/test_maxpreps_enhanced.py)
import asyncio
from src.datasources.us.maxpreps import MaxPrepsDataSource

async def test_enhanced_parser():
    async with MaxPrepsDataSource() as maxpreps:
        # Test search_players_with_stats (new method)
        results = await maxpreps.search_players_with_stats(
            state="CA",
            limit=10
        )

        print(f"Found {len(results)} players with stats")

        for player, stats in results:
            print(f"\nPlayer: {player.full_name}")
            print(f"  School: {player.school_name}")

            if stats:
                print(f"  Stats:")
                print(f"    Games: {stats.games_played}")
                print(f"    Points: {stats.points} ({stats.points_per_game} PPG)")
                print(f"    Rebounds: {stats.total_rebounds} ({stats.rebounds_per_game} RPG)")
                print(f"    Assists: {stats.assists} ({stats.assists_per_game} APG)")
                print(f"    FG%: {stats.field_goal_percentage}")
            else:
                print(f"  Stats: Not available")

asyncio.run(test_enhanced_parser())
```

---

## Integration Checklist

Once validation is successful, integrate enhanced parser:

### ✅ Step 1: Backup Original
```bash
cp src/datasources/us/maxpreps.py src/datasources/us/maxpreps_backup.py
```

### ✅ Step 2: Update maxpreps.py

**Replace method** (line ~490):
```python
# FROM:
def _parse_player_from_stats_row(self, row, state, data_source):
    # ... old implementation ...

# TO:
def _parse_player_and_stats_from_row(self, row, state, data_source, season=None):
    # ... enhanced implementation from maxpreps_enhanced_parser.py ...
```

**Update search_players** (line ~475):
```python
# FROM:
player = self._parse_player_from_stats_row(row, state, data_source)

# TO:
player, _ = self._parse_player_and_stats_from_row(row, state, data_source)
```

**Add new method** (line ~750):
```python
async def search_players_with_stats(self, state, name=None, team=None, season=None, limit=50):
    # ... from maxpreps_enhanced_parser.py ...
```

### ✅ Step 3: Update Tests

Add test for new method in `tests/test_datasources/test_maxpreps.py`:

```python
@pytest.mark.integration
@pytest.mark.skip(reason="ToS compliance")
async def test_search_players_with_stats(self, maxpreps):
    """Test enhanced search that returns stats."""
    results = await maxpreps.search_players_with_stats(state="CA", limit=3)

    assert isinstance(results, list)
    if len(results) > 0:
        player, stats = results[0]
        assert isinstance(player, Player)
        if stats:
            assert isinstance(stats, PlayerSeasonStats)
```

### ✅ Step 4: Update Exports

Ensure new method is accessible:
```python
# In src/datasources/us/__init__.py - already exported
from .maxpreps import MaxPrepsDataSource  # ✓ Already done
```

### ✅ Step 5: Document in PROJECT_LOG

Add Phase 13.2.1 completion to PROJECT_LOG.md

---

## Validation Results Template

After running validation, document results:

### State: California (CA)

**Date**: 2025-11-14
**Status**: ✅ Success / ⚠️ Partial / ❌ Failed

**HTML Structure**:
- Tables found: X
- Rows extracted: X
- Columns found: [list]

**Available Metrics**:
- PPG: ✅ Column "PPG"
- RPG: ✅ Column "RPG"
- APG: ✅ Column "APG"
- SPG: ✅ Column "SPG"
- BPG: ✅ Column "BPG"
- FG%: ✅ Column "FG%"
- 3P%: ✅ Column "3P%"
- FT%: ✅ Column "FT%"
- GP: ✅ Column "GP"
- MPG: ⚠️ Not found

**Sample Data**:
```json
{
  "player": "John Doe",
  "school": "Lincoln High",
  "ppg": 25.3,
  "rpg": 5.2,
  "apg": 4.1
}
```

**Recommendations**:
- ✅ Parser works as expected
- ⚠️ Adjust column mapping for MPG
- ✅ Ready for production use (with ToS compliance)

---

## State-by-State Testing Plan

Recommended testing order (prioritize high-value states):

### Tier 1: High-Value States (Test First)
1. **California (CA)** - Largest basketball population
2. **Texas (TX)** - Large population, RankOne overlap
3. **New York (NY)** - Major basketball state
4. **Florida (FL)** - Strong programs
5. **Georgia (GA)** - Strong programs

### Tier 2: Representative Sample (Test 2-3)
6. Illinois (IL)
7. Pennsylvania (PA)
8. North Carolina (NC)
9. Ohio (OH)
10. Michigan (MI)

### Tier 3: Validate Coverage (Spot Check)
- Small states: Wyoming (WY), Vermont (VT), Alaska (AK)
- Mid-size states: Oregon (OR), Colorado (CO)

### Tier 4: Comprehensive (If Time Allows)
- All remaining 41 states

---

## Troubleshooting

### Issue: No tables found

**Possible causes**:
- URL endpoint incorrect
- React content didn't render
- Anti-bot protection blocked request

**Solutions**:
1. Check URL manually in browser
2. Increase browser timeout
3. Add wait for specific element
4. Try different user agent

### Issue: Tables found but no rows

**Possible causes**:
- Table structure different than expected
- Season ended (no current data)
- State has no stat leaders page

**Solutions**:
1. Inspect HTML snapshot
2. Look for different table class/ID
3. Try different season parameter

### Issue: Columns don't match

**Possible causes**:
- MaxPreps changed column names
- State uses different format
- Sport-specific columns

**Solutions**:
1. Review `html_columns` in JSON report
2. Update column mappings in parser
3. Add fallback column names

---

## Next Steps After Validation

1. **Document findings** in PROJECT_LOG.md
2. **Integrate enhanced parser** if validation successful
3. **Update configuration** based on actual performance
4. **Consider commercial licensing** for production use
5. **Move to Phase 13.3**: 247Sports recruiting adapter

---

## Legal Compliance Checklist

Before using MaxPreps adapter in production:

- [ ] Reviewed MaxPreps Terms of Service
- [ ] Contacted MaxPreps for permission/licensing
- [ ] Implemented commercial data license (if applicable)
- [ ] Added rate limiting (10 req/min minimum)
- [ ] Added user agent identification
- [ ] Implemented respectful caching
- [ ] Added error handling for blocked requests
- [ ] Documented legal compliance in code
- [ ] Informed users of ToS restrictions

---

## Resources

- **MaxPreps Website**: https://www.maxpreps.com
- **Validation Script**: `scripts/validate_maxpreps.py`
- **Enhanced Parser**: `src/datasources/us/maxpreps_enhanced_parser.py`
- **Tests**: `tests/test_datasources/test_maxpreps.py`
- **This Guide**: `docs/MAXPREPS_VALIDATION_GUIDE.md`

---

**Last Updated**: 2025-11-14
**Status**: Ready for Manual Testing
