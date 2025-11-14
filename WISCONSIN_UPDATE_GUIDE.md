# Wisconsin WIAA Test Updates - Implementation Guide

## Summary

This update transitions Wisconsin WIAA tests from LIVE mode (hitting real website with HTTP 403s) to FIXTURE mode (offline testing) for stable CI/CD.

### Changes Made

1. **New fixture in conftest.py** - `wisconsin_wiaa_fixture_source` for offline testing
2. **Updated test file** - Separates fixture-based tests from live integration tests
3. **Historical test suite** - Parametric tests with coverage reporting
4. **Fixed round name expectations** - Aligned with full names like "Regional Semifinals"

---

## Step-by-Step Replacement Instructions

### 1. Update conftest.py

**File**: `tests/conftest.py`

**Location**: Lines 146-155 (existing fixture)

**Action**: Replace the existing `wisconsin_wiaa_source` fixture with BOTH fixtures

**Find this** (lines 146-155):
```python
@pytest_asyncio.fixture(scope="module")
async def wisconsin_wiaa_source() -> AsyncGenerator[WisconsinWiaaDataSource, None]:
    """Create Wisconsin WIAA datasource for testing."""
    source = WisconsinWiaaDataSource()
    yield source
    await source.close()
```

**Replace with**:
```python
@pytest_asyncio.fixture(scope="module")
async def wisconsin_wiaa_source() -> AsyncGenerator[WisconsinWiaaDataSource, None]:
    """Create Wisconsin WIAA datasource for testing (LIVE mode by default).

    Note: Uses LIVE mode which may hit real WIAA website and get HTTP 403s.
    For stable CI tests, use wisconsin_wiaa_fixture_source instead.
    """
    source = WisconsinWiaaDataSource()
    yield source
    await source.close()


@pytest_asyncio.fixture(scope="module")
async def wisconsin_wiaa_fixture_source() -> AsyncGenerator[WisconsinWiaaDataSource, None]:
    """Create Wisconsin WIAA datasource in FIXTURE mode for stable testing.

    Uses local fixture files from tests/fixtures/wiaa/ instead of live HTTP.
    Currently supports: 2024 Boys/Girls Div1
    """
    from pathlib import Path
    from src.datasources.us.wisconsin_wiaa import DataMode

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=Path("tests/fixtures/wiaa")
    )
    yield source
    await source.close()
```

---

### 2. Replace test_wisconsin_wiaa.py

**File**: `tests/test_datasources/test_wisconsin_wiaa.py`

**Action**: Replace entire file content

**Option A - Manual replacement**:
1. Backup current file:
   ```powershell
   cp tests/test_datasources/test_wisconsin_wiaa.py tests/test_datasources/test_wisconsin_wiaa.py.backup
   ```

2. Delete current file:
   ```powershell
   rm tests/test_datasources/test_wisconsin_wiaa.py
   ```

3. Rename updated file:
   ```powershell
   mv tests/test_datasources/test_wisconsin_wiaa_UPDATED.py tests/test_datasources/test_wisconsin_wiaa.py
   ```

**Option B - Direct overwrite** (if you're confident):
```powershell
cp tests/test_datasources/test_wisconsin_wiaa_UPDATED.py tests/test_datasources/test_wisconsin_wiaa.py
```

---

### 3. Add Historical Test Suite

**File**: `tests/test_datasources/test_wisconsin_wiaa_historical.py` (new file)

**Action**: File already created - nothing to replace

This file provides:
- Parametric tests across years/genders/divisions
- Coverage gap reporting
- Fixture validation
- Known team spot checks

---

## Validation - Run These Tests

After making the replacements, validate everything works:

### 1. Run Fixture-Based Parser Tests (Should Pass)
```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa_parser.py -v
# Expected: 15/15 passed
```

### 2. Run Updated Datasource Tests (Should Pass)
```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa.py -v
# Expected: Most tests passing (using fixture mode)
# Some tests skipped (marked as integration/missing fixtures)
```

### 3. Run Historical Tests (Should Pass with Skips)
```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
# Expected:
# - 2024 Boys/Girls Div1 tests pass
# - Other years/divisions skip (fixtures don't exist yet)
# - Coverage report generated
```

### 4. Check Coverage Report
```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py::test_wisconsin_fixture_coverage_report -v -s
# Expected: Shows which fixtures exist (currently only 2024 Boys/Girls Div1)
```

---

## What Tests Now Do

### Fixture-Based Tests (Stable, Fast, CI-Safe)

These tests use `wisconsin_wiaa_fixture_source` and run offline:

✅ `test_get_tournament_brackets_boys_2024_div1` - Boys 2024 Div1 (15 games from fixture)
✅ `test_get_tournament_brackets_girls_2024_div1` - Girls 2024 Div1 (15 games from fixture)
✅ `test_no_self_games` - Validates no team plays itself
✅ `test_no_duplicate_games` - Validates no duplicate games
✅ `test_valid_scores` - Scores in range 0-200
✅ `test_round_parsing` - Round names (updated expectations)
✅ `test_wisconsin_location_data` - Team IDs start with wiaa_wi_
✅ `test_division_filtering` - Div1 games only
✅ `test_team_extraction` - Unique teams extracted
✅ `test_data_completeness` - All fields populated

### Skipped Tests (Integration/Missing Fixtures)

These tests are marked with `@pytest.mark.skip`:

⏭️ `test_get_tournament_brackets_boys_2024_live` - LIVE mode (403 issues)
⏭️ `test_get_tournament_brackets_girls_2024_live` - LIVE mode (403 issues)
⏭️ `test_multiple_divisions` - Needs Div2-Div4 fixtures
⏭️ `test_historical_data_2023` - Needs 2023 fixtures

These can be run manually when needed:
```powershell
pytest tests/test_datasources/test_wisconsin_wiaa.py::TestWisconsinWiaaDataSource::test_get_tournament_brackets_boys_2024_live -v
```

---

## Current Fixture Coverage

| Year | Boys Div1 | Girls Div1 | Boys Div2 | Girls Div2 | Boys Div3 | Girls Div3 | Boys Div4 | Girls Div4 |
|------|-----------|------------|-----------|------------|-----------|------------|-----------|------------|
| 2024 | ✅        | ✅         | ❌        | ❌         | ❌        | ❌         | ❌        | ❌         |
| 2023 | ❌        | ❌         | ❌        | ❌         | ❌        | ❌         | ❌        | ❌         |

**Fixture files**:
- `tests/fixtures/wiaa/2024_Basketball_Boys_Div1.html` (15 games)
- `tests/fixtures/wiaa/2024_Basketball_Girls_Div1.html` (15 games)

---

## Next Steps (Expanding Coverage)

### Option 1: Add More 2024 Divisions

Add fixtures for Div2-Div4 for 2024:
1. Download bracket HTML from `halftime.wiaawi.org` (use browser to avoid 403s)
2. Save as `tests/fixtures/wiaa/2024_Basketball_{gender}_{division}.html`
3. Re-run tests - parametric tests will automatically detect new fixtures

### Option 2: Add Historical Years

Add fixtures for 2023, 2022, etc.:
1. Download bracket HTML for each year
2. Follow same naming convention
3. Update `YEARS` in `test_wisconsin_wiaa_historical.py` if desired

### Option 3: Manual Integration Testing

When you want to test LIVE mode:
```powershell
# Run specific live test (will likely get 403s)
pytest tests/test_datasources/test_wisconsin_wiaa.py::TestWisconsinWiaaDataSource::test_get_tournament_brackets_boys_2024_live -v

# Check HTTP stats to see 403 count
# (will be in test output)
```

---

## Troubleshooting

### Issue: Tests Still Failing

**Symptom**: Tests fail with "Expected at least 200 games, got 0"

**Cause**: Test is using LIVE mode (old fixture)

**Fix**: Make sure you replaced conftest.py AND the test file

### Issue: Import Error

**Symptom**: `ImportError: cannot import name 'DataMode'`

**Cause**: Running on old code that doesn't have DataMode enum

**Fix**: Make sure you're on branch `claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG`
```powershell
git status  # Check current branch
git pull origin claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG
```

### Issue: Fixture Not Found

**Symptom**: `Fixture missing: 2024 Boys Div1`

**Cause**: Fixture files not in correct location

**Fix**: Verify fixture files exist:
```powershell
ls tests/fixtures/wiaa/
# Should show:
# 2024_Basketball_Boys_Div1.html
# 2024_Basketball_Girls_Div1.html
```

---

## Key Benefits of This Update

1. **Stable CI/CD** - No HTTP 403s breaking builds
2. **Fast tests** - Offline testing is instant (1.73s vs 30+s)
3. **Explicit coverage** - Skipped tests show what's missing
4. **Easy expansion** - Just add fixture files to increase coverage
5. **Historical tracking** - Coverage report shows progress
6. **Backwards compatible** - LIVE mode tests still available (just skipped)

---

## Files Changed Summary

| File | Change | Lines Changed |
|------|--------|---------------|
| `tests/conftest.py` | Added fixture_source fixture | +15 lines |
| `tests/test_datasources/test_wisconsin_wiaa.py` | Complete rewrite | ~280 lines |
| `tests/test_datasources/test_wisconsin_wiaa_historical.py` | New file | +400 lines |

Total: ~695 lines changed/added
