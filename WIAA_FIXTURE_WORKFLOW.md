# Wisconsin WIAA Fixture Backfill Workflow Guide

**Last Updated**: 2025-11-14
**Repository**: ghadfield32/hs_bball_players_mcp
**Current Status**: 2/80 fixtures present (2.5% complete)

---

## Quick Reference

### Current Coverage
- **Present**: 2/80 (2.5%) - 2024 Boys/Girls Div1
- **Planned Priority 1**: 6 fixtures - 2024 Div2-4 (Boys/Girls)
- **Planned Priority 2**: 16 fixtures - 2022-2023 all divisions
- **Future**: 56 fixtures - 2015-2021 all divisions

### One-Command Checklist
```powershell
# 1. Activate virtual environment
& .venv\Scripts\Activate.ps1

# 2. Verify environment
.venv\Scripts\python.exe -m scripts.debug_import_issue

# 3. Check current coverage
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py

# 4. Open Priority 1 fixtures in browser (2024 Div2-4)
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 1

# 5. After saving HTML files, inspect them
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2024 --gender Boys --division Div2

# 6. Run tests to validate
.venv\Scripts\python.exe -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
```

---

## Complete Workflow

### Phase 1: Environment Setup (One-Time)

#### 1.1 Activate Virtual Environment
```powershell
cd C:\docker_projects\betts_basketball\hs_bball_players_mcp
& .venv\Scripts\Activate.ps1
```

#### 1.2 Verify pytest Installation
```powershell
.venv\Scripts\python.exe -m pytest --version
```

**Expected Output**: `pytest 9.0.1` (or higher)

**If Missing**:
```powershell
uv pip install pytest
```

#### 1.3 Verify Import System
```powershell
.venv\Scripts\python.exe -m scripts.debug_import_issue
```

**Expected**: `[OK] Package import successful` and `[OK] No import issues found!` (or only self-referential warnings)

**Purpose**: This diagnostic tool ensures all Wisconsin WIAA imports work correctly before proceeding.

---

### Phase 2: Baseline Assessment

#### 2.1 Check Current Coverage
```powershell
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py
```

**Output Includes**:
- Overall progress percentage
- Status breakdown (Present/Planned/Future)
- Coverage by year and gender
- Next recommended actions

#### 2.2 View Detailed Grid (Optional)
```powershell
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py --grid
```

**Shows**: Year-by-year matrix of all 80 fixture combinations with status symbols

#### 2.3 List Missing Fixtures Only (Optional)
```powershell
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py --missing-only
```

**Shows**: Only fixtures not yet marked as "present", grouped by priority

---

### Phase 3: Priority 1 - Complete 2024 Season (6 Fixtures)

**Goal**: Finish current season coverage (2024 Div2-4 for Boys/Girls)

**Time Estimate**: ~15 minutes

#### 3.1 Open Browser Tabs for Priority 1 Fixtures
```powershell
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 1
```

**What Happens**:
1. Script reads `manifest_wisconsin.yml`
2. Finds all Priority 1 fixtures (2024 Div2-4)
3. Opens 6 browser tabs to WIAA URLs
4. Displays exact filenames to use when saving

**Browser Tabs Opened**:
- 2024 Boys Div2
- 2024 Boys Div3
- 2024 Boys Div4
- 2024 Girls Div2
- 2024 Girls Div3
- 2024 Girls Div4

#### 3.2 Save HTML Files
For **each tab** opened:

1. **Verify the page loaded correctly**:
   - Should show a tournament bracket
   - Should have team names and scores
   - Should NOT be a redirect or error page

2. **Save the page** (`Ctrl+S` or `File → Save Page As`):
   - **Format**: "Web Page, HTML Only" (NOT "Complete")
   - **Location**: `C:\docker_projects\betts_basketball\hs_bball_players_mcp\tests\fixtures\wiaa\`
   - **Filename**: Use EXACT name from script output:
     - `2024_Basketball_Boys_Div2.html`
     - `2024_Basketball_Boys_Div3.html`
     - `2024_Basketball_Boys_Div4.html`
     - `2024_Basketball_Girls_Div2.html`
     - `2024_Basketball_Girls_Div3.html`
     - `2024_Basketball_Girls_Div4.html`

3. **Do NOT save** the `_files` folder (only the single .html file)

#### 3.3 Update Manifest Status
Open `tests/fixtures/wiaa/manifest_wisconsin.yml` and update ALL 6 fixtures:

**Find this** (for each of the 6 fixtures):
```yaml
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
```

**Change to**:
```yaml
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "present"
  priority: 1
```

**Repeat for**: Boys Div2/3/4 and Girls Div2/3/4

#### 3.4 Validate Fixtures
Run spot-checks on 2-3 fixtures to ensure quality:

```powershell
# Check Boys Div2
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2024 --gender Boys --division Div2

# Check Girls Div3
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2024 --gender Girls --division Div3
```

**Expected Output**:
- `[+] File exists`
- `[+] Parsed successfully`
- `[+] X games found` (X > 0, typically 13-15 games)
- `[+] No self-games detected`
- `[+] All scores in valid range`
- Sample team names and scores displayed

**If FAIL**: Re-download that specific HTML file and check again

#### 3.5 Run Wisconsin Tests
```powershell
.venv\Scripts\python.exe -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
```

**Expected**: Tests for all 8 × 2024 fixtures should PASS (Div1-4, Boys/Girls)

#### 3.6 Verify Coverage Increase
```powershell
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py
```

**Expected**:
- Overall: **8/80 fixtures (10%)**
- 2024: **8/8 (100%)**
- Boys: **4/40 (10%)**
- Girls: **4/40 (10%)**

---

### Phase 4: Priority 2 - Recent Historical Data (16 Fixtures)

**Goal**: Add 2023 and 2022 complete coverage

**Time Estimate**: ~30 minutes (can split into 2 sessions: 2023 first, then 2022)

#### 4.1 Open Browser Tabs for Priority 2 Fixtures
```powershell
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 2
```

**Alternatively, do one year at a time**:
```powershell
# Just 2023 (8 fixtures)
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 2 --year 2023

# Then 2022 (8 fixtures)
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 2 --year 2022
```

#### 4.2 Save HTML Files
Same process as Phase 3.2, but for 2023/2022:

**2023 Filenames**:
- `2023_Basketball_Boys_Div1.html`
- `2023_Basketball_Boys_Div2.html`
- `2023_Basketball_Boys_Div3.html`
- `2023_Basketball_Boys_Div4.html`
- `2023_Basketball_Girls_Div1.html`
- `2023_Basketball_Girls_Div2.html`
- `2023_Basketball_Girls_Div3.html`
- `2023_Basketball_Girls_Div4.html`

**2022 Filenames**: Same pattern with `2022_Basketball_...`

#### 4.3 Update Manifest
Change `status: "planned"` to `status: "present"` for all 16 fixtures (2023 + 2022)

#### 4.4 Validate Fixtures
Spot-check at least 2-3 fixtures per year:

```powershell
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2023 --gender Boys --division Div1
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2022 --gender Girls --division Div4
```

#### 4.5 Run Tests
```powershell
.venv\Scripts\python.exe -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
```

**Expected**: All 24 fixtures should PASS (2022-2024, all divisions)

#### 4.6 Verify Coverage
```powershell
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py
```

**Expected After Phase 4**:
- Overall: **24/80 fixtures (30%)**
- 2024: **8/8 (100%)**
- 2023: **8/8 (100%)**
- 2022: **8/8 (100%)**

---

### Phase 5: Historical Backfill (2015-2021) - Future Work

**Goal**: Complete coverage for 7 additional years (56 fixtures)

**Recommendation**: Work **one year at a time**, starting from most recent (2021) and going backward

**Process** (repeat for each year):
1. Change `status: "future"` to `status: "planned"` in manifest for that year
2. Run: `.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --year 2021`
3. Save 8 HTML files
4. Update manifest: `status: "planned"` → `status: "present"`
5. Validate with `inspect_wiaa_fixture.py`
6. Run tests
7. Check coverage

**Years to backfill**: 2021, 2020, 2019, 2018, 2017, 2016, 2015

---

## Troubleshooting

### Issue: Browser opens but page shows error or redirect

**Solution**: Check the WIAA URL pattern. WIAA may have changed their URL structure for older years.

**Action**:
1. Manually navigate to WIAA tournament results page
2. Find the correct bracket URL for that year/gender/division
3. Update `BASE_URL` in `scripts/open_missing_wiaa_fixtures.py` if needed
4. Or manually download and save with correct filename

### Issue: `inspect_wiaa_fixture.py` reports 0 games parsed

**Possible Causes**:
- Saved the wrong page (e.g., schedule instead of bracket)
- WIAA changed their HTML structure for that year
- File is empty or corrupted

**Solution**:
1. Re-download the HTML file
2. Open the .html file in a browser to verify it contains bracket data
3. If parser fails on valid data, check [wisconsin_wiaa.py](src/datasources/us/wisconsin_wiaa.py) parser logic

### Issue: Tests fail with "fixture file not found"

**Solution**: Verify:
1. HTML file is in `tests/fixtures/wiaa/` directory
2. Filename matches EXACT format: `{year}_Basketball_{gender}_{division}.html`
3. Manifest status is `"present"` for that fixture

### Issue: Import errors when running scripts

**Solution**:
```powershell
.venv\Scripts\python.exe -m scripts.debug_import_issue
```

Check output for specific import mismatches and fix as indicated.

---

## Key Files Reference

### Scripts
- `scripts/show_wiaa_coverage.py` - Coverage dashboard and progress tracking
- `scripts/open_missing_wiaa_fixtures.py` - Browser helper for downloading fixtures
- `scripts/inspect_wiaa_fixture.py` - Fixture validation and sanity checks
- `scripts/debug_import_issue.py` - Import diagnostic tool
- `scripts/rollover_wiaa_season.py` - Annual season rollover automation

### Data Files
- `tests/fixtures/wiaa/manifest_wisconsin.yml` - Single source of truth for fixture status
- `tests/fixtures/wiaa/*.html` - Saved tournament bracket HTML files

### Source Code
- `src/datasources/us/wisconsin_wiaa.py` - WIAA data source adapter
- `tests/test_datasources/test_wisconsin_wiaa_historical.py` - Historical fixture tests

### Documentation
- `PROJECT_LOG.md` - Complete project history and session logs
- `WIAA_FIXTURE_WORKFLOW.md` - This file

---

## Progress Tracking

### Milestone Checklist

- [x] Phase 0: Environment setup and tooling
  - [x] pytest installed
  - [x] debug_import_issue.py working
  - [x] Coverage dashboard running

- [ ] Phase 1: 2024 Complete (Priority 1)
  - [x] 2024 Boys/Girls Div1 (already present)
  - [ ] 2024 Boys Div2
  - [ ] 2024 Boys Div3
  - [ ] 2024 Boys Div4
  - [ ] 2024 Girls Div2
  - [ ] 2024 Girls Div3
  - [ ] 2024 Girls Div4

- [ ] Phase 2: 2023 Complete (Priority 2)
  - [ ] 2023 Boys Div1-4
  - [ ] 2023 Girls Div1-4

- [ ] Phase 3: 2022 Complete (Priority 2)
  - [ ] 2022 Boys Div1-4
  - [ ] 2022 Girls Div1-4

- [ ] Phase 4: 2015-2021 (Future)
  - [ ] 2021 (8 fixtures)
  - [ ] 2020 (8 fixtures)
  - [ ] 2019 (8 fixtures)
  - [ ] 2018 (8 fixtures)
  - [ ] 2017 (8 fixtures)
  - [ ] 2016 (8 fixtures)
  - [ ] 2015 (8 fixtures)

### Coverage Milestones

| Milestone | Fixtures | Coverage % | Status |
|-----------|----------|------------|--------|
| Baseline (Div1 2024) | 2/80 | 2.5% | ✓ DONE |
| Complete 2024 | 8/80 | 10% | In Progress |
| Add 2023 | 16/80 | 20% | Planned |
| Add 2022 | 24/80 | 30% | Planned |
| Add 2021 | 32/80 | 40% | Future |
| Add 2020 | 40/80 | 50% | Future |
| Add 2019 | 48/80 | 60% | Future |
| Add 2018 | 56/80 | 70% | Future |
| Add 2017 | 64/80 | 80% | Future |
| Add 2016 | 72/80 | 90% | Future |
| Add 2015 | 80/80 | 100% | Future |

---

## Best Practices

### DO
- ✓ Run coverage check before and after each batch of additions
- ✓ Validate fixtures with `inspect_wiaa_fixture.py` before marking as "present"
- ✓ Use exact filenames shown by the script
- ✓ Save as "HTML Only" (not "Complete")
- ✓ Work in priority order (Priority 1 → Priority 2 → Future)
- ✓ Test after each batch with pytest
- ✓ Update PROJECT_LOG after completing each phase

### DON'T
- ✗ Don't skip validation steps
- ✗ Don't save _files folders (only .html)
- ✗ Don't rename files manually
- ✗ Don't mark fixtures as "present" without validating
- ✗ Don't edit manifest YAML by hand if you can avoid it (easy to create syntax errors)
- ✗ Don't download fixtures out of priority order

---

## Time Estimates

| Task | Time | Notes |
|------|------|-------|
| Environment setup (one-time) | 5 min | Installing pytest, verifying imports |
| Baseline assessment | 2 min | Running coverage checks |
| Priority 1 (6 fixtures) | 15 min | Open tabs, save HTML, update manifest, validate |
| Priority 2 - 2023 (8 fixtures) | 20 min | Same process as Priority 1 |
| Priority 2 - 2022 (8 fixtures) | 20 min | Same process as Priority 1 |
| Each additional year (2015-2021) | 20 min | Repeat process for 8 fixtures |
| **Total for Phases 1-2** | ~60 min | Gets you to 30% coverage |
| **Total for 100% coverage** | ~3 hours | Spread across multiple sessions |

---

## Next Steps After This Workflow

Once you reach 100% coverage (80/80 fixtures):

1. **Annual Rollover** - Each March after new season:
   ```powershell
   .venv\Scripts\python.exe scripts/rollover_wiaa_season.py 2025 --download --interactive
   ```

2. **Maintenance** - Periodically verify all fixtures still parse correctly

3. **Consider API Access** - Request official WIAA API credentials:
   ```powershell
   .venv\Scripts\python.exe scripts/contact_wiaa.py --generate
   ```

---

**Questions or Issues?** Check `PROJECT_LOG.md` for detailed implementation notes or create an issue in the repository.
