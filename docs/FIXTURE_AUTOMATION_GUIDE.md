# Wisconsin WIAA Fixture Automation Guide

This guide explains how to use the automated fixture processing scripts to efficiently expand Wisconsin WIAA test coverage from 2/80 (2.5%) to 80/80 (100%) fixtures.

## Overview

**Manual Workflow** (before automation):
- 7 steps per fixture × 78 missing fixtures = 546 manual actions
- Error-prone (typos, forgotten steps, inconsistent validation)
- Slow feedback (sequential processing)

**Automated Workflow** (with these scripts):
- Download fixtures → Run one command → Done
- Batch processing of 10+ fixtures at once
- Automatic validation + testing + manifest updates
- Clear reporting of successes and failures

## Quick Start

### Option 1: Process All Planned Fixtures (Recommended)

```powershell
# Windows PowerShell
.\scripts\Process-Fixtures.ps1 -Planned

# Or directly with Python (cross-platform)
python scripts/process_fixtures.py --planned
```

This will:
1. Find all fixtures marked as "planned" in manifest (22 fixtures for Priority 1 & 2)
2. Check which HTML files you've already downloaded
3. Validate each downloaded fixture
4. Update manifest for successful validations
5. Generate summary report

### Option 2: Process Specific Fixtures

```powershell
# Process just the 2024 Div2-Div4 fixtures (Priority 1)
python scripts/process_fixtures.py --fixtures "2024,Boys,Div2" "2024,Boys,Div3" "2024,Boys,Div4" "2024,Girls,Div2" "2024,Girls,Div3" "2024,Girls,Div4"
```

### Option 3: Dry Run (Test Without Changes)

```powershell
# See what would happen without actually updating the manifest
python scripts/process_fixtures.py --planned --dry-run
```

## Detailed Workflow

### Step 1: Download Fixtures (Human-in-the-Loop)

You still need to manually download fixture HTML files because WIAA blocks automated downloads with HTTP 403 errors. However, we provide a browser helper script that automates URL opening, file naming guidance, and progress tracking.

#### Option 1A: Automated Browser Helper (Recommended)

**Use the browser helper script to streamline downloads:**

```bash
# Open browsers for all planned fixtures
python scripts/open_missing_wiaa_fixtures.py --planned

# Or just Priority 1 fixtures (2024 remaining)
python scripts/open_missing_wiaa_fixtures.py --priority 1

# Or specific year
python scripts/open_missing_wiaa_fixtures.py --year 2024

# Or specific fixtures
python scripts/open_missing_wiaa_fixtures.py --fixtures "2024,Boys,Div2" "2024,Girls,Div3"
```

**What the script does:**
1. Reads manifest to find missing fixtures
2. Filters based on your criteria (planned/priority/year)
3. Opens each URL in your browser automatically
4. Shows exact filename to use when saving
5. Waits for you to save, then moves to next fixture
6. Tracks progress (X of Y downloaded)
7. Generates summary report

**Your workflow:**
1. Run the script with your desired filter
2. When browser opens, use **Save Page As... → HTML Only**
3. Save to `tests/fixtures/wiaa/` with the filename shown
4. Press ENTER to continue to next fixture
5. Script reports what was saved and what's remaining

**Example session:**
```
$ python scripts/open_missing_wiaa_fixtures.py --priority 1

📋 Found 6 missing fixture(s) to download
   2 fixture(s) already present

================================================================================
Fixture 1/6: 2024 Boys Div2
================================================================================
URL: https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_Basketball_Boys_Div2.html
Save as: 2024_Basketball_Boys_Div2.html
Save location: /home/user/hs_bball_players_mcp/tests/fixtures/wiaa

✅ Opened in browser

Instructions:
  1. In your browser, use 'Save Page As...' or Ctrl+S / Cmd+S
  2. Choose format: 'Webpage, HTML Only' (NOT 'Complete')
  3. Save to: /home/user/hs_bball_players_mcp/tests/fixtures/wiaa
  4. Use filename: 2024_Basketball_Boys_Div2.html

Press ENTER when saved, 's' to skip, 'q' to quit:
✅ Confirmed: 2024_Basketball_Boys_Div2.html exists

[... repeats for remaining fixtures ...]

================================================================================
SESSION SUMMARY
================================================================================
Browsers opened: 6
Files saved:     6
Skipped:         0
Already present: 2

✅ Next step: Validate and update manifest
   Run: python scripts/process_fixtures.py --planned
```

**Batch mode (open multiple tabs at once):**
```bash
# Open 5 tabs at a time instead of one-by-one
python scripts/open_missing_wiaa_fixtures.py --priority 1 --batch-size 5
```

**Auto-validate after downloading:**
```bash
# Automatically runs process_fixtures.py when downloads complete
python scripts/open_missing_wiaa_fixtures.py --planned --auto-validate
```

#### Option 1B: Manual Download (Alternative)

If you prefer to download manually without the helper script:

1. Open browser to `https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/`
2. Navigate to bracket page (e.g., `2024_Basketball_Boys_Div2.html`)
3. Save page as **HTML only** (not complete with assets)
4. Place in `tests/fixtures/wiaa/` with exact naming: `{year}_Basketball_{gender}_{division}.html`

**Example for 2024 Boys Div2:**
- Browser: `https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_Basketball_Boys_Div2.html`
- Save as: `tests/fixtures/wiaa/2024_Basketball_Boys_Div2.html`

**Tip:** Download all Priority 1 fixtures (6 files) before running the batch processor.

### Step 2: Run Batch Processor

```powershell
# Process all planned fixtures that have been downloaded
python scripts/process_fixtures.py --planned
```

**What happens for each fixture:**

1. **File Check**: Verifies HTML file exists
   - If missing → adds to "needs_download" list
   - If exists → proceeds to validation

2. **Inspection**: Runs `inspect_wiaa_fixture.py` quality checks
   - Parses HTML with WIAA parser
   - Checks: game count, scores, rounds, no self-games
   - If fails → adds to "inspection_failed" list
   - If passes → proceeds to testing

3. **Testing**: Runs pytest for this fixture
   - Executes parametric tests for this year/gender/division
   - Verifies: health, rounds, completeness
   - If fails → adds to "tests_failed" list
   - If passes → proceeds to manifest update

4. **Manifest Update**: Changes status from "planned" to "present"
   - Backs up manifest before changes
   - Updates status field
   - Adds timestamp and validation notes
   - Saves updated manifest

### Step 3: Review Results

The script generates a summary report showing:

**✅ NEWLY VALIDATED**: Fixtures that passed all checks and were marked as present
```
✅ NEWLY VALIDATED (3):
   - 2024 Boys Div2: planned → present
   - 2024 Boys Div3: planned → present
   - 2024 Girls Div2: planned → present
```

**ℹ️ ALREADY PRESENT**: Fixtures already validated (no action needed)
```
ℹ️ ALREADY PRESENT (2):
   - 2024 Boys Div1
   - 2024 Girls Div1
```

**📥 NEEDS DOWNLOAD**: Fixtures marked as planned but HTML file not found
```
📥 NEEDS DOWNLOAD (3):
   - 2024 Boys Div4: 2024_Basketball_Boys_Div4.html
   - 2024 Girls Div3: 2024_Basketball_Girls_Div3.html
   - 2024 Girls Div4: 2024_Basketball_Girls_Div4.html

   Action: Download these from WIAA website and re-run
```

**❌ INSPECTION FAILED**: Fixtures that failed quality checks
```
❌ INSPECTION FAILED (1):
   - 2023 Boys Div1: Parsed 0 games

   Action: Fix fixtures or parser before marking as present
```

**❌ TESTS FAILED**: Fixtures that passed inspection but failed pytest
```
❌ TESTS FAILED (1):
   - 2022 Girls Div2: Some tests failed (see pytest output)

   Action: Review test failures
```

### Step 4: Commit Changes

After successful processing:

```powershell
# Review changes
git status
git diff tests/fixtures/wiaa/manifest_wisconsin.yml

# Stage and commit
git add tests/fixtures/wiaa/
git commit -m "Add 3 Wisconsin WIAA 2024 fixtures (Boys Div2-3, Girls Div2)

Fixtures added:
- 2024_Basketball_Boys_Div2.html
- 2024_Basketball_Boys_Div3.html
- 2024_Basketball_Girls_Div2.html

Validated with process_fixtures.py: inspection and tests passed.
Manifest updated to mark as 'present'."

# Push
git push
```

**Or use auto-commit mode (PowerShell only):**

```powershell
.\scripts\Process-Fixtures.ps1 -Planned -Commit
```

This will automatically:
- Stage fixture files and manifest
- Generate descriptive commit message
- Commit changes
- Prompt to push

## Command Reference

### open_missing_wiaa_fixtures.py (Browser Helper)

**Purpose:** Opens browser tabs for missing fixtures to streamline the download process.

**Open all planned fixtures:**
```bash
python scripts/open_missing_wiaa_fixtures.py --planned
```

**Open only Priority 1 fixtures:**
```bash
python scripts/open_missing_wiaa_fixtures.py --priority 1
```

**Open only Priority 2 fixtures:**
```bash
python scripts/open_missing_wiaa_fixtures.py --priority 2
```

**Open specific year:**
```bash
python scripts/open_missing_wiaa_fixtures.py --year 2024
```

**Open specific fixtures:**
```bash
python scripts/open_missing_wiaa_fixtures.py --fixtures "2024,Boys,Div2" "2024,Girls,Div3"
```

**Batch mode (multiple tabs):**
```bash
# Open 5 tabs at once instead of one-by-one
python scripts/open_missing_wiaa_fixtures.py --planned --batch-size 5
```

**Auto-validate after downloading:**
```bash
# Runs process_fixtures.py automatically when done
python scripts/open_missing_wiaa_fixtures.py --planned --auto-validate
```

**Flags:**
- `--planned` - All fixtures with status="planned"
- `--priority N` - Only fixtures with priority=N (1 or 2)
- `--year YYYY` - Only fixtures from year YYYY
- `--fixtures "Y,G,D"` - Specific fixtures (format: "YEAR,GENDER,DIVISION")
- `--batch-size N` - Open N tabs before pausing (default: 1)
- `--auto-validate` - Run process_fixtures.py after downloads
- `--quiet` - Minimal output

**Interactive controls:**
- `ENTER` - Confirm file was saved, continue to next
- `s` - Skip this fixture
- `q` - Quit the session

### process_fixtures.py (Python)

**Process all planned fixtures:**
```bash
python scripts/process_fixtures.py
python scripts/process_fixtures.py --planned  # Explicit
```

**Process specific fixtures:**
```bash
python scripts/process_fixtures.py --fixtures "2024,Boys,Div2" "2024,Girls,Div3"
```

**Dry run (no changes):**
```bash
python scripts/process_fixtures.py --planned --dry-run
```

**Quiet mode (less output):**
```bash
python scripts/process_fixtures.py --planned --quiet
```

### Process-Fixtures.ps1 (PowerShell)

**Process all planned fixtures:**
```powershell
.\scripts\Process-Fixtures.ps1 -Planned
```

**Process specific fixtures:**
```powershell
.\scripts\Process-Fixtures.ps1 -Fixtures "2024,Boys,Div2", "2024,Girls,Div3"
```

**Dry run:**
```powershell
.\scripts\Process-Fixtures.ps1 -Planned -DryRun
```

**Auto-commit:**
```powershell
.\scripts\Process-Fixtures.ps1 -Planned -Commit
```

## Troubleshooting

### Issue: "Fixture file not found"

**Problem**: You haven't downloaded the HTML file yet.

**Solution**: Follow Step 1 to download from WIAA website.

### Issue: "Inspection failed: Parsed 0 games"

**Problem**: Fixture HTML is empty, malformed, or WIAA changed markup.

**Solutions**:
1. Re-download the fixture (might have been incomplete)
2. Open in browser to verify bracket renders correctly
3. Check if WIAA changed HTML structure (may need parser updates)

### Issue: "Tests failed"

**Problem**: Fixture parsed correctly but test assertions failed.

**Solutions**:
1. Run tests manually to see detailed failure:
   ```bash
   python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -k "2024_Boys_Div2" -v --tb=short
   ```
2. Check if test expectations need adjustment
3. Verify fixture has expected data (scores, teams, rounds)

### Issue: "No manifest entry"

**Problem**: Fixture combination not defined in manifest (unexpected).

**Solution**: Check manifest_wisconsin.yml to verify entry exists for that year/gender/division.

### Issue: Script hangs or times out

**Problem**: Inspection or tests taking too long.

**Timeouts**:
- Inspection: 30 seconds per fixture
- Tests: 60 seconds per fixture

**Solutions**:
1. Check if fixture file is very large (>1MB)
2. Run inspection/tests manually to see what's slow
3. May indicate parser performance issue

## Best Practices

### 1. Work in Batches

Download 5-10 fixtures before running the processor. This is more efficient than processing one at a time.

**Example workflow:**
```powershell
# Download all 2024 Div2-Div4 fixtures (6 files)
# Then process them all at once:
python scripts/process_fixtures.py --planned
```

### 2. Use Dry Run First

Before making real changes, do a dry run to see what would happen:
```powershell
python scripts/process_fixtures.py --planned --dry-run
```

This helps you:
- Verify which fixtures are ready
- Identify which need downloads
- Catch issues before updating manifest

### 3. Process Priority 1 Before Priority 2

Follow the roadmap:
- **Priority 1**: Complete 2024 (6 fixtures) → 10% coverage
- **Priority 2**: Add 2022-2023 (16 fixtures) → 30% coverage
- **Future**: Backfill 2015-2021 (56 fixtures) → 100% coverage

### 4. Commit Frequently

Don't wait to validate all 78 fixtures before committing. Commit after each successful batch:
- After Priority 1: Commit 6 fixtures
- After 2023: Commit 8 fixtures
- After 2022: Commit 8 fixtures
- etc.

This makes it easier to:
- Track progress
- Revert if needed
- Review changes in smaller chunks

### 5. Verify Tests After Batch

After processing a batch, run the full historical test suite to confirm:
```powershell
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
```

Check that:
- New fixtures show PASSED (not SKIPPED)
- Existing fixtures still pass
- Coverage report shows increased percentage

## Coverage Expansion Roadmap

### Current Status
- **Present**: 2/80 (2.5%)
  - 2024 Boys Div1
  - 2024 Girls Div1

### Priority 1: Complete 2024 (Target: 10% coverage)
**Action**: Download and process these 6 fixtures:
```
2024_Basketball_Boys_Div2.html
2024_Basketball_Boys_Div3.html
2024_Basketball_Boys_Div4.html
2024_Basketball_Girls_Div2.html
2024_Basketball_Girls_Div3.html
2024_Basketball_Girls_Div4.html
```

**Command**:
```powershell
python scripts/process_fixtures.py --fixtures "2024,Boys,Div2" "2024,Boys,Div3" "2024,Boys,Div4" "2024,Girls,Div2" "2024,Girls,Div3" "2024,Girls,Div4"
```

### Priority 2: Add 2023 & 2022 (Target: 30% coverage)
**Action**: Download and process 16 fixtures (8 per year):
- 2023: Boys/Girls Div1-Div4 (8 fixtures)
- 2022: Boys/Girls Div1-Div4 (8 fixtures)

**Command** (after downloading all 16 files):
```powershell
python scripts/process_fixtures.py --planned
```

### Future: Backfill 2015-2021 (Target: 100% coverage)
**Action**: Download and process remaining 56 fixtures

Work by year:
- 2021: 8 fixtures
- 2020: 8 fixtures
- 2019: 8 fixtures
- 2018: 8 fixtures
- 2017: 8 fixtures
- 2016: 8 fixtures
- 2015: 8 fixtures

## Performance

**Typical timing:**
- Inspection: ~2-5 seconds per fixture
- Tests: ~1-3 seconds per fixture
- Total: ~5-8 seconds per fixture

**Batch processing 10 fixtures**: ~1-2 minutes

**Manual workflow** (for comparison): ~5-10 minutes per fixture

**Time saved**: ~90% reduction in processing time!

## Advanced Usage

### Process Only Specific Years

```bash
# Process all 2024 fixtures
python scripts/process_fixtures.py --fixtures "2024,Boys,Div1" "2024,Boys,Div2" "2024,Boys,Div3" "2024,Boys,Div4" "2024,Girls,Div1" "2024,Girls,Div2" "2024,Girls,Div3" "2024,Girls,Div4"

# Or use a loop in PowerShell
$years = @(2024)
$genders = @("Boys", "Girls")
$divisions = @("Div1", "Div2", "Div3", "Div4")

$fixtures = foreach ($y in $years) {
    foreach ($g in $genders) {
        foreach ($d in $divisions) {
            "$y,$g,$d"
        }
    }
}

python scripts/process_fixtures.py --fixtures $fixtures
```

### Integrate with CI

Add to `.github/workflows/test.yml`:
```yaml
- name: Validate Wisconsin WIAA fixtures
  run: |
    python scripts/process_fixtures.py --planned --dry-run
    if [ $? -ne 0 ]; then
      echo "Fixture validation failed"
      exit 1
    fi
```

This ensures all fixtures in CI are properly validated.

## Support

**Issues with fixtures:**
1. Check `docs/WISCONSIN_FIXTURE_GUIDE.md` for manual workflow
2. Run inspection script manually: `python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2 -v`
3. Review parser code: `src/datasources/us/wisconsin_wiaa.py`

**Issues with scripts:**
1. Check Python version: `python --version` (need 3.11+)
2. Verify working directory: Must run from repo root
3. Check dependencies: `pip install pyyaml pytest`

**Questions:**
- Review `tests/fixtures/wiaa/manifest_wisconsin.yml` for coverage status
- Run coverage report: `python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py::test_wisconsin_fixture_coverage_report -v -s`
