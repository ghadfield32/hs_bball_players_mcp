# Wisconsin WIAA Historical Backfill Guide

**Complete workflow for acquiring, validating, and integrating 80 Wisconsin WIAA tournament fixtures (2015-2024)**

---

## 📊 Coverage Overview

**Target Grid**: 10 years × 2 genders × 4 divisions = **80 fixtures**

| Years | Genders | Divisions | Total Fixtures |
|-------|---------|-----------|----------------|
| 2015-2024 (10 years) | Boys, Girls (2) | Div1-Div4 (4) | **80** |

**Current Status**: 2/80 present (2.5%)
- ✅ 2024 Boys Div1
- ✅ 2024 Girls Div1

**Remaining**: 78 fixtures across three priority levels

---

##  1️⃣ One-Time Setup (Do This Once)

### 1.1 Install pytest in Virtual Environment

```powershell
# Activate virtual environment
cd C:\docker_projects\betts_basketball\hs_bball_players_mcp
& .venv\Scripts\Activate.ps1

# Install pytest
python -m pip install pytest

# Verify installation
python -m pytest --version
```

### 1.2 Verify Scripts Work

```powershell
# Test coverage dashboard
python scripts/show_wiaa_coverage.py

# Test debug script
python scripts/debug_import_issue.py

# Test inspector (on existing fixture)
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div1
```

**Expected Output**: All scripts should run without import errors.

---

## 2️⃣ Priority 1: Complete 2024 (6 fixtures)

**Goal**: Finish all 2024 Boys/Girls Div2-Div4 brackets

### Fixtures Needed:
- `2024_Basketball_Boys_Div2.html`
- `2024_Basketball_Boys_Div3.html`
- `2024_Basketball_Boys_Div4.html`
- `2024_Basketball_Girls_Div2.html`
- `2024_Basketball_Girls_Div3.html`
- `2024_Basketball_Girls_Div4.html`

### Workflow:

#### Step 2.1: Open Browser Tabs for Missing Fixtures

```powershell
python scripts/open_missing_wiaa_fixtures.py --priority 1
```

**What this does**:
- Reads `manifest_wisconsin.yml`
- Finds all Priority 1 fixtures (status != "present")
- Opens WIAA bracket URLs in your default browser (6 tabs)
- Shows exact filename to use when saving

#### Step 2.2: Save HTML Files (Manual - Human-in-the-Loop)

For each browser tab:

1. **Verify URL**: Confirm year/gender/division matches what you expect
2. **Check Content**: Page should show tournament bracket (not 403 error page)
3. **Save HTML**:
   - Press `Ctrl+S` (or File → Save Page As)
   - **Type**: "Web Page, HTML only" (NOT "Complete")
   - **Location**: `C:\docker_projects\betts_basketball\hs_bball_players_mcp\tests\fixtures\wiaa\`
   - **Filename**: Use EXACT name shown by script (e.g., `2024_Basketball_Boys_Div2.html`)

**Important**: Save as "HTML only", not "Complete" (which creates extra folders)

#### Step 2.3: Validate Each Fixture

Run inspector on each downloaded fixture:

```powershell
# Example for Boys Div2
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2

# Repeat for all 6 fixtures:
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div3
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div4
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Girls --division Div2
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Girls --division Div3
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Girls --division Div4
```

**What to Look For**:
- ✅ File exists and is readable
- ✅ Game count > 0 (should be 15-30 games)
- ✅ No self-games (team playing itself)
- ✅ Scores in valid range (0-200)
- ✅ Expected rounds present (Regional, Sectional, State)

**If Validation Fails**:
- Check HTML file isn't a 403 error page
- Verify you saved "HTML only" (not "Complete")
- Re-download if needed

#### Step 2.4: Batch Update Manifest

Option A: **Automatic** (recommended):
```powershell
python scripts/process_fixtures.py --priority 1
```

This will:
- Find all Priority 1 fixtures with HTML files
- Run inspections
- Update manifest (planned → present)
- Run tests
- Show summary report

Option B: **Manual**:
Open `tests/fixtures/wiaa/manifest_wisconsin.yml` and change:

```yaml
# BEFORE:
- year: 2024
  gender: Boys
  division: Div2
  file: tests/fixtures/wiaa/2024_Basketball_Boys_Div2.html
  status: planned
  priority: 1

# AFTER:
- year: 2024
  gender: Boys
  division: Div2
  file: tests/fixtures/wiaa/2024_Basketball_Boys_Div2.html
  status: present  # ← Changed from "planned"
  priority: 1
```

Repeat for all 6 fixtures.

#### Step 2.5: Verify Coverage

```powershell
# Check coverage dashboard
python scripts/show_wiaa_coverage.py
```

**Expected Output**:
```
Overall Progress: 8/80 fixtures (10.0%)
2024: 8/8 ████████████████████ (100%)
```

#### Step 2.6: Run Tests

```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa.py -v
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
```

**Expected Results**:
- `test_wisconsin_wiaa.py`: ~14 passed, 5 skipped
- `test_wisconsin_wiaa_historical.py`: ~19 passed, ~215 skipped (skips are normal for missing fixtures)

#### Step 2.7: Commit Progress

```powershell
git add tests/fixtures/wiaa/*.html
git add tests/fixtures/wiaa/manifest_wisconsin.yml
git commit -m "Add WIAA 2024 Boys/Girls Div2-4 fixtures (Priority 1)

- Downloaded 6 HTML fixtures from WIAA halftime site
- Validated via inspect_wiaa_fixture.py (all passed)
- Updated manifest: planned → present
- Coverage: 8/80 (10.0%)
- Tests: All passing"

git push origin <your-branch>
```

---

## 3️⃣ Priority 2: Add 2023 & 2022 (16 fixtures)

**Goal**: Complete all divisions for past 2 seasons

### Fixtures Needed:

**2023** (8 fixtures):
- `2023_Basketball_Boys_Div1.html` through `Div4.html`
- `2023_Basketball_Girls_Div1.html` through `Div4.html`

**2022** (8 fixtures):
- `2022_Basketball_Boys_Div1.html` through `Div4.html`
- `2022_Basketball_Girls_Div1.html` through `Div4.html`

### Workflow (Same as Priority 1):

#### Step 3.1: Open Browsers

```powershell
python scripts/open_missing_wiaa_fixtures.py --priority 2
```

**OR** do one year at a time:
```powershell
python scripts/open_missing_wiaa_fixtures.py --year 2023
python scripts/open_missing_wiaa_fixtures.py --year 2022
```

#### Step 3.2: Save HTML Files

Same process as Priority 1 (Ctrl+S, HTML only, correct filenames)

#### Step 3.3: Validate (Spot Check)

You don't need to run every single fixture through the inspector. Spot check a few:

```powershell
# Check one Boys and one Girls per year
python scripts/inspect_wiaa_fixture.py --year 2023 --gender Boys --division Div1
python scripts/inspect_wiaa_fixture.py --year 2023 --gender Girls --division Div4

python scripts/inspect_wiaa_fixture.py --year 2022 --gender Boys --division Div1
python scripts/inspect_wiaa_fixture.py --year 2022 --gender Girls --division Div4
```

#### Step 3.4: Batch Update

```powershell
python scripts/process_fixtures.py --year 2023
python scripts/process_fixtures.py --year 2022
```

**OR** process both at once:
```powershell
python scripts/process_fixtures.py --priority 2
```

#### Step 3.5: Verify

```powershell
python scripts/show_wiaa_coverage.py
```

**Expected**:
```
Overall Progress: 24/80 fixtures (30.0%)
2022: 8/8 ████████████████████ (100%)
2023: 8/8 ████████████████████ (100%)
2024: 8/8 ████████████████████ (100%)
```

#### Step 3.6: Run Tests & Commit

```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

git add tests/fixtures/wiaa/*.html tests/fixtures/wiaa/manifest_wisconsin.yml
git commit -m "Add WIAA 2023 & 2022 fixtures (Priority 2)

- Downloaded 16 HTML fixtures (2023: 8, 2022: 8)
- Validated via spot checks
- Coverage: 24/80 (30.0%)
- Tests: All passing"
git push
```

---

## 4️⃣ Phase 3: Backfill 2015-2021 (56 fixtures)

**Goal**: Complete historical coverage for 7 remaining years

### Fixtures Needed:

**2021** (8 fixtures), **2020** (8), **2019** (8), **2018** (8), **2017** (8), **2016** (8), **2015** (8)

### Strategy: One Year at a Time

Do these in **reverse chronological order** (2021 → 2020 → ... → 2015) because:
- Recent years more likely to have complete data
- Easier to verify against other sources (MaxPreps, etc.)
- Natural checkpoint every 8 fixtures

### Workflow (Per Year):

#### Step 4.1: Download One Year

```powershell
# Example: 2021
python scripts/open_missing_wiaa_fixtures.py --year 2021
```

#### Step 4.2: Save 8 HTML Files

Same process (Ctrl+S, HTML only, exact filenames)

#### Step 4.3: Validate (Spot Check)

```powershell
# Check corners of the grid (Div1 & Div4 for both genders)
python scripts/inspect_wiaa_fixture.py --year 2021 --gender Boys --division Div1
python scripts/inspect_wiaa_fixture.py --year 2021 --gender Boys --division Div4
python scripts/inspect_wiaa_fixture.py --year 2021 --gender Girls --division Div1
python scripts/inspect_wiaa_fixture.py --year 2021 --gender Girls --division Div4
```

#### Step 4.4: Update Manifest

```powershell
python scripts/process_fixtures.py --year 2021
```

#### Step 4.5: Verify & Commit

```powershell
python scripts/show_wiaa_coverage.py
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

git add tests/fixtures/wiaa/*.html tests/fixtures/wiaa/manifest_wisconsin.yml
git commit -m "Add WIAA 2021 fixtures (Phase 3)

- Downloaded 8 HTML fixtures (Boys/Girls Div1-4)
- Validated via spot checks
- Coverage: 32/80 (40.0%)
- Tests: All passing"
git push
```

#### Step 4.6: Repeat for Remaining Years

Continue with 2020, 2019, ..., 2015 using the same workflow.

**Progress checkpoints**:
- After 2021: 32/80 (40%)
- After 2020: 40/80 (50%)
- After 2019: 48/80 (60%)
- After 2018: 56/80 (70%)
- After 2017: 64/80 (80%)
- After 2016: 72/80 (90%)
- After 2015: 80/80 (100%) ✅

### Handling Missing/Broken Data

If you encounter issues with older years:

**Problem**: WIAA doesn't have HTML brackets for certain years (only PDFs or summaries)

**Solution**:
1. Document in manifest with a note:
   ```yaml
   - year: 2016
     gender: Boys
     division: Div3
     file: tests/fixtures/wiaa/2016_Basketball_Boys_Div3.html
     status: blocked  # Or leave as "future"
     priority: 3
     notes: "WIAA site only has PDF for this bracket, no HTML available"
   ```

2. Update PROJECT_LOG noting the gap
3. Continue with other years - better to have documented gaps than bad data

**Problem**: HTML is truncated or has parsing errors

**Solution**:
1. Re-download from browser (sometimes first save fails)
2. Check if WIAA site structure changed (compare to working fixture)
3. If persistent, document as "blocked" and investigate parser

---

## 5️⃣ Verification & Quality Checks

### After Each Batch

**Run Full Test Suite**:
```powershell
# Historical fixture tests
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

# Parser tests
python -m pytest tests/test_datasources/test_wisconsin_wiaa_parser.py -v

# Integration tests
python -m pytest tests/test_datasources/test_wisconsin_wiaa.py -v
```

**Check Coverage Dashboard**:
```powershell
python scripts/show_wiaa_coverage.py --grid
```

**Spot Check Parsed Data**:
```powershell
# Inspect a fixture in detail
python scripts/inspect_wiaa_fixture.py --year 2020 --gender Girls --division Div2
```

### Final Validation (After All 80 Fixtures)

```powershell
# Run complete test suite
python -m pytest tests/test_datasources/ -k wisconsin -v

# Generate coverage report
python scripts/show_wiaa_coverage.py --export coverage_complete.json

# Verify no blocked/missing entries
python scripts/show_wiaa_coverage.py --missing-only
```

**Expected Final State**:
- 80/80 fixtures present (or documented gaps)
- All tests passing
- Coverage dashboard shows 100% (or 100% of available data)

---

## 6️⃣ Script Reference

### Quick Command Cheat Sheet

```powershell
# === DISCOVERY ===
# Show what's missing
python scripts/show_wiaa_coverage.py
python scripts/show_wiaa_coverage.py --missing-only

# === ACQUISITION ===
# Open browsers for missing fixtures
python scripts/open_missing_wiaa_fixtures.py --priority 1    # 2024 Div2-4
python scripts/open_missing_wiaa_fixtures.py --priority 2    # 2023, 2022
python scripts/open_missing_wiaa_fixtures.py --year 2021     # Specific year

# === VALIDATION ===
# Check single fixture
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2

# Batch process (validates + updates manifest)
python scripts/process_fixtures.py --priority 1
python scripts/process_fixtures.py --year 2023
python scripts/process_fixtures.py --dry-run  # Preview without updating

# === TESTING ===
# Run Wisconsin tests
python -m pytest tests/test_datasources/test_wisconsin_wiaa.py -v
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

# === DEBUGGING ===
# If imports fail
python scripts/debug_import_issue.py
```

### File Naming Convention

**Pattern**: `{YEAR}_Basketball_{GENDER}_{DIVISION}.html`

**Examples**:
- `2024_Basketball_Boys_Div1.html`
- `2023_Basketball_Girls_Div4.html`
- `2015_Basketball_Boys_Div2.html`

**Location**: `tests/fixtures/wiaa/`

### Manifest Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `present` | HTML exists, validated, tests pass | Ready to use |
| `planned` | Priority 1 or 2, ready to download | Target for acquisition |
| `future` | Phase 3, low priority | Backfill when ready |
| `blocked` | Cannot obtain (PDF only, etc.) | Documented gap |

---

## 7️⃣ Time Estimates

Based on the workflow:

| Phase | Fixtures | Time per Fixture | Total Time |
|-------|----------|------------------|------------|
| Setup (one-time) | - | - | 10 minutes |
| Priority 1 (2024 Div2-4) | 6 | ~2 min | 12 minutes |
| Priority 2 (2023, 2022) | 16 | ~2 min | 32 minutes |
| Phase 3 (2015-2021) | 56 | ~2 min | 112 minutes |
| **Total** | **78** | | **~2.5 hours** |

**Per-Fixture Breakdown**:
- Open browser: 10 seconds
- Save HTML: 30 seconds
- Validation: 30 seconds
- Manifest update: 30 seconds (automated)
- Commit: 20 seconds

**Efficiency Tips**:
- Use batch mode: `--batch-size 5` (open 5 tabs at once)
- Process whole years at a time
- Let scripts handle manifest updates (don't edit YAML manually)
- Commit after each year for clear checkpoints

---

## 8️⃣ Troubleshooting

### "ImportError: cannot import name..."

**Fix**: Run from repo root, or use `-m` flag:
```powershell
cd C:\docker_projects\betts_basketball\hs_bball_players_mcp
python scripts/debug_import_issue.py
# OR
python -m scripts.debug_import_issue
```

### "No module named pytest"

**Fix**: Install pytest in your venv:
```powershell
& .venv\Scripts\Activate.ps1
python -m pip install pytest
```

### "Manifest not found"

**Fix**: Run scripts from repository root:
```powershell
cd C:\docker_projects\betts_basketball\hs_bball_players_mcp
python scripts/show_wiaa_coverage.py
```

### Inspector shows "0 games parsed"

**Causes**:
1. HTML file is a 403 error page (not actual bracket)
2. Saved as "Complete" instead of "HTML only"
3. WIAA changed their HTML structure

**Fix**:
1. Re-download using browser "Save As → HTML only"
2. Check HTML file manually (should contain `<table>` tags with game data)
3. Compare to a working fixture (e.g., 2024 Boys Div1)

### Tests fail after adding fixtures

**Causes**:
1. Fixture HTML is malformed
2. Manifest status not updated
3. Parser encountered new edge case

**Debug**:
```powershell
# Run single test with verbose output
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py::test_fixture_2024_Boys_Div2 -vv

# Inspect the problematic fixture
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2
```

---

## 9️⃣ Success Criteria

### After Priority 1:
- ✅ 8/80 fixtures present (10%)
- ✅ All 2024 tests passing
- ✅ Coverage dashboard shows 2024 row at 100%

### After Priority 2:
- ✅ 24/80 fixtures present (30%)
- ✅ 2022-2024 tests passing
- ✅ Coverage dashboard shows 3 complete years

### After Phase 3:
- ✅ 80/80 fixtures present (100%) OR documented gaps
- ✅ All historical tests passing
- ✅ Coverage dashboard shows 10 complete years
- ✅ PROJECT_LOG documents any blocked/unavailable fixtures

---

## 🔟 Next Steps After Completion

Once you have 80/80 coverage:

1. **Update PROJECT_LOG** with completion metrics
2. **Consider MaxPreps cross-validation**:
   ```python
   # For each WIAA champion, verify team exists in MaxPreps
   # (Already have MaxPreps adapter ready)
   ```
3. **Merge to main** when tests are green
4. **Season Rollover** (annual):
   ```powershell
   python scripts/rollover_wiaa_season.py 2025 --download --interactive
   ```

---

**Last Updated**: 2025-11-14
**Estimated Completion Time**: 2.5 hours for all 78 remaining fixtures
**Current Coverage**: 2/80 (2.5%)
**Target Coverage**: 80/80 (100%)
