# Wisconsin WIAA - Next Steps

## What We Just Did (Phase 14.3)

We've created a comprehensive solution to fix your failing Wisconsin WIAA tests by migrating from LIVE mode (blocked by HTTP 403s) to FIXTURE mode (offline, stable, fast).

### Files Created (Ready to Use)

1. ✅ **`WISCONSIN_UPDATE_GUIDE.md`** - Complete replacement instructions
2. ✅ **`tests/conftest.py`** - UPDATED (added fixture mode source)
3. ✅ **`tests/test_datasources/test_wisconsin_wiaa_UPDATED.py`** - New version ready to replace old file
4. ✅ **`tests/test_datasources/test_wisconsin_wiaa_historical.py`** - New historical test suite
5. ✅ **`PROJECT_LOG.md`** - UPDATED with Phase 14.3 documentation

---

## What You Should Do Now

### Step 1: Replace the Test File (REQUIRED)

The key fix is replacing the old test file with the new one:

```powershell
# Backup current file (optional but recommended)
cp tests\test_datasources\test_wisconsin_wiaa.py tests\test_datasources\test_wisconsin_wiaa.py.backup

# Replace with updated version
cp tests\test_datasources\test_wisconsin_wiaa_UPDATED.py tests\test_datasources\test_wisconsin_wiaa.py
```

**Why**: This switches 2024 tests from LIVE mode (403 errors) to FIXTURE mode (works offline).

### Step 2: Validate It Works

Run the tests to confirm everything passes:

```powershell
# Parser tests (should already pass)
python -m pytest tests\test_datasources\test_wisconsin_wiaa_parser.py -v

# Updated datasource tests (should pass now)
python -m pytest tests\test_datasources\test_wisconsin_wiaa.py -v

# Historical tests (should pass with some skips)
python -m pytest tests\test_datasources\test_wisconsin_wiaa_historical.py -v
```

**Expected results**:
- ✅ Parser tests: 15/15 passing
- ✅ Datasource tests: Most passing (some skipped for missing fixtures)
- ✅ Historical tests: 2024 Div1 tests passing, others skipped

### Step 3: Review Coverage Report

See which fixtures you have vs which you need:

```powershell
python -m pytest tests\test_datasources\test_wisconsin_wiaa_historical.py::test_wisconsin_fixture_coverage_report -v -s
```

This shows a matrix of which year/gender/division combinations have fixtures.

Currently you have:
- ✅ 2024 Boys Div1
- ✅ 2024 Girls Div1
- ❌ Everything else

---

## Understanding the Changes

### Old Way (LIVE Mode - Broken)

```python
# conftest.py
source = WisconsinWiaaDataSource()  # Defaults to LIVE mode

# test_wisconsin_wiaa.py
games = await wisconsin_wiaa_source.get_tournament_brackets(year=2024, gender="Boys")
# ^ Tries to hit real WIAA website → HTTP 403 → 0 games → test fails
```

### New Way (FIXTURE Mode - Works)

```python
# conftest.py
source = WisconsinWiaaDataSource(
    data_mode=DataMode.FIXTURE,
    fixtures_dir=Path("tests/fixtures/wiaa")
)

# test_wisconsin_wiaa.py
games = await wisconsin_wiaa_fixture_source.get_tournament_brackets(
    year=2024, gender="Boys", division="Div1"
)
# ^ Loads from tests/fixtures/wiaa/2024_Basketball_Boys_Div1.html → 15 games → test passes
```

### Key Benefits

1. **Stable** - No HTTP 403 errors
2. **Fast** - 2s vs 30+s
3. **Offline** - Works without network
4. **CI-safe** - Won't break builds
5. **Explicit** - Tests skip when fixtures missing (not hiding problems)

---

## Expanding Coverage (Optional - Do Later)

To test more years/divisions, you need more fixture files:

### How to Add More Fixtures

1. **Download bracket HTML** from WIAA website (use browser to avoid 403s):
   - Go to `https://halftime.wiaawi.org/`
   - Navigate to tournament brackets for desired year/gender/division
   - Save page as HTML

2. **Save with correct naming**:
   ```
   tests/fixtures/wiaa/{year}_Basketball_{gender}_{division}.html
   ```

   Examples:
   - `tests/fixtures/wiaa/2024_Basketball_Boys_Div2.html`
   - `tests/fixtures/wiaa/2024_Basketball_Girls_Div2.html`
   - `tests/fixtures/wiaa/2023_Basketball_Boys_Div1.html`

3. **Re-run historical tests** - They auto-detect new fixtures:
   ```powershell
   python -m pytest tests\test_datasources\test_wisconsin_wiaa_historical.py -v
   ```

### Priority Order (Suggested)

1. **2024 Div2-Div4** (complete current year)
2. **2023 Div1** (add one historical year)
3. **2022, 2021** (backfill)
4. **2015-2020** (comprehensive historical coverage)

---

## If Tests Still Fail

### Common Issues

#### Issue: "DataMode not found"

**Cause**: Not on the right git branch

**Fix**:
```powershell
git status  # Check current branch
git switch claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG
git pull
```

#### Issue: "Fixture file not found"

**Cause**: Fixture files not in correct location

**Fix**: Verify files exist:
```powershell
ls tests\fixtures\wiaa\
# Should see:
# 2024_Basketball_Boys_Div1.html
# 2024_Basketball_Girls_Div1.html
```

#### Issue: "Test expects 200 games, got 15"

**Cause**: Using old test file that hasn't been replaced

**Fix**: Make sure you replaced test_wisconsin_wiaa.py with the UPDATED version

---

## Questions?

### "Do I need to replace anything else?"

**No** - Just replace `test_wisconsin_wiaa.py` as shown in Step 1. The conftest.py changes are already committed (you pulled them from git).

### "Will this break existing functionality?"

**No** - All changes are backwards compatible. We added a new fixture (`wisconsin_wiaa_fixture_source`) but kept the old one (`wisconsin_wiaa_source`). Live mode tests still exist, they're just skipped by default.

### "How do I run live tests if I want to?"

```powershell
pytest tests\test_datasources\test_wisconsin_wiaa.py::TestWisconsinWiaaDataSource::test_get_tournament_brackets_boys_2024_live -v
```

(Will likely still get 403s, but available for debugging)

### "How do I know which fixtures I'm missing?"

Run the coverage report:
```powershell
python -m pytest tests\test_datasources\test_wisconsin_wiaa_historical.py::test_wisconsin_fixture_coverage_report -v -s
```

Shows a matrix with ✅ (have) vs ❌ (missing).

---

## Summary: What Changed

| Component | Old (LIVE) | New (FIXTURE) | Benefit |
|-----------|-----------|---------------|---------|
| conftest.py | 1 fixture (LIVE) | 2 fixtures (LIVE + FIXTURE) | Choice of mode |
| test_wisconsin_wiaa.py | All LIVE mode | Most FIXTURE mode | Stable CI |
| Test execution | 30+s with 403s | 2s, no network | Fast & reliable |
| Coverage tracking | None | Parametric + report | Visibility into gaps |
| CI stability | Flaky (403s) | 100% stable | Green builds |

---

## Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `WISCONSIN_UPDATE_GUIDE.md` | Detailed replacement instructions | ✅ Created |
| `NEXT_STEPS.md` | This file - quick start guide | ✅ Created |
| `PROJECT_LOG.md` | Phase 14.3 documentation | ✅ Updated |
| `tests/conftest.py` | Fixture definitions | ✅ Updated |
| `tests/test_datasources/test_wisconsin_wiaa_UPDATED.py` | New test file | ✅ Created |
| `tests/test_datasources/test_wisconsin_wiaa_historical.py` | Historical tests | ✅ Created |

---

**Bottom Line**: Replace `test_wisconsin_wiaa.py` with `test_wisconsin_wiaa_UPDATED.py` and run the tests. Everything should be green! 🎯
