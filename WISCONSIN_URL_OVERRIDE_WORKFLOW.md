# Wisconsin WIAA URL Override Workflow

**Purpose**: Handle 404 errors by allowing explicit URL overrides in manifest

**Created**: 2025-11-14
**Status**: Implemented and tested

---

## Quick Reference

### When to Use URL Overrides

Use URL overrides when:
- ✅ Script shows "Using fallback pattern" warning
- ✅ Browser opens to 404 page
- ✅ WIAA changed their URL structure
- ✅ Different divisions/years use different URL patterns

### Workflow Summary

```bash
# 1. Dry-run to see URLs
python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run

# 2. See 404-prone URLs with "fallback" source
# 3. Manually find real URLs on WIAA site
# 4. Edit manifest_wisconsin.yml, add url: fields
# 5. Re-run to download with correct URLs
python -m scripts.open_missing_wiaa_fixtures --priority 1
```

---

## Detailed Workflow

### Step 1: Run Dry-Run to Identify Problems

**Command**:
```powershell
cd C:\docker_projects\betts_basketball\hs_bball_players_mcp
& .venv\Scripts\Activate.ps1
python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
```

**What to Look For**:

```
Fixture 1/6: 2024 Boys Div2
--------------------------------------------------------------------------------
  Filename:    2024_Basketball_Boys_Div2.html
  Save to:     C:\...\tests\fixtures\wiaa
  URL:         https://halftime.wiaawi.org/.../2024_Basketball_Boys_Div2.html
  URL Source:  fallback                    ← ⚠️ WARNING: May 404!
  ⚠️  WARNING: Using fallback pattern - may 404!
     If this URL doesn't work, add 'url:' field to manifest
```

**Key Indicators**:
- ❌ `URL Source: fallback` → Using guess, may be wrong
- ✅ `URL Source: manifest` → Explicit URL, should work

### Step 2: Manually Find Real URLs

For each fixture showing `fallback` URL source:

1. **Open WIAA website** in browser:
   ```
   https://www.wiaawi.org
   ```

2. **Navigate to tournament brackets**:
   - Sports → Basketball
   - State Tournament → Past Results / Brackets
   - Select year (e.g., 2024)
   - Select gender (Boys / Girls)
   - Select division (Div1, Div2, Div3, Div4)

3. **Copy the actual bracket URL** from browser address bar:
   ```
   Example: https://halftime.wiaawi.org/SomeDifferentPath/ActualBracket.html
   ```

4. **Document what you found**:
   - If HTML exists: Copy URL
   - If only PDF: Copy PDF URL (note: may need different processing)
   - If doesn't exist: Note as unavailable

### Step 3: Update Manifest with URL Overrides

**Open manifest file**:
```powershell
code tests\fixtures\wiaa\manifest_wisconsin.yml
# OR
notepad tests\fixtures\wiaa\manifest_wisconsin.yml
```

**Find the fixture entry** (example for 2024 Boys Div2):

**BEFORE** (no URL override):
```yaml
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
  notes: "Priority 1: Complete 2024 coverage"
```

**AFTER** (with URL override):
```yaml
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
  url: "https://halftime.wiaawi.org/ActualPath/RealBracket.html"
  notes: "Priority 1: Complete 2024 coverage. URL differs from Div1 pattern, discovered manually 2025-11-14"
```

**What Changed**:
- ✅ Added `url:` field with actual URL from WIAA site
- ✅ Updated `notes:` to document when/why URL was added

**Repeat for all fixtures** that had 404s or `fallback` warnings.

### Step 4: Verify with Dry-Run

**Run dry-run again** to confirm changes:

```powershell
python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
```

**Expected output** (for fixtures you fixed):

```
Fixture 1/6: 2024 Boys Div2
--------------------------------------------------------------------------------
  Filename:    2024_Basketball_Boys_Div2.html
  Save to:     C:\...\tests\fixtures\wiaa
  URL:         https://halftime.wiaawi.org/ActualPath/RealBracket.html
  URL Source:  manifest                    ← ✅ GOOD: Using explicit override
```

**Verify**:
- ✅ All fixtures show `URL Source: manifest` (no fallbacks)
- ✅ URLs look correct
- ✅ No warning messages

### Step 5: Download Fixtures with Correct URLs

**Run without dry-run** to actually download:

```powershell
python -m scripts.open_missing_wiaa_fixtures --priority 1
```

**What happens**:
1. Script opens browser with correct URL (from manifest)
2. Browser shows actual bracket (not 404)
3. You save HTML file using "Save As → HTML Only"
4. Script verifies file was saved
5. Repeat for all fixtures

**If you still get 404**:
- Double-check URL in manifest
- Verify you copied full URL from WIAA site
- Try opening URL manually in browser first
- URL may have changed again (WIAA site update)

### Step 6: Validate Downloaded Fixtures

**Run inspection script** on each downloaded fixture:

```powershell
# Example for Boys Div2
python scripts\inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2

# Check all 6 Priority 1 fixtures
python scripts\inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div3
python scripts\inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div4
python scripts\inspect_wiaa_fixture.py --year 2024 --gender Girls --division Div2
python scripts\inspect_wiaa_fixture.py --year 2024 --gender Girls --division Div3
python scripts\inspect_wiaa_fixture.py --year 2024 --gender Girls --division Div4
```

**What to check**:
- ✅ File parses without errors
- ✅ Game count is reasonable (15-30 games typically)
- ✅ No self-games (team vs itself)
- ✅ Scores in valid range
- ✅ Expected rounds present (Regional, Sectional, State)

**If validation fails**:
- HTML might be truncated (re-download)
- Might have saved "Complete" instead of "HTML Only" (re-download)
- URL might point to wrong bracket (verify on WIAA site)

### Step 7: Update Manifest Status

**Option A: Automatic** (uses batch processor):
```powershell
python scripts\process_fixtures.py --priority 1
```

This will:
- Find all Priority 1 fixtures with HTML files
- Run inspections automatically
- Update manifest (planned → present)
- Run tests

**Option B: Manual**:

Open `tests\fixtures\wiaa\manifest_wisconsin.yml` and change:

```yaml
# BEFORE:
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
  url: "https://..."

# AFTER:
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "present"  # ← Changed from "planned"
  priority: 1
  url: "https://..."
```

### Step 8: Verify Coverage

```powershell
# Check coverage dashboard
python scripts\show_wiaa_coverage.py
```

**Expected output** (after completing 2024 Priority 1):
```
Overall Progress: 8/80 fixtures (10.0%)

2024: 8/8 ████████████████████ (100%)
```

### Step 9: Run Tests

```powershell
# Run historical tests
python -m pytest tests\test_datasources\test_wisconsin_wiaa_historical.py -v
```

**Expected**:
- Tests for all 8 fixtures should pass
- Other years will skip (normal until you add their fixtures)

### Step 10: Commit Progress

```powershell
# Stage HTML files and manifest
git add tests\fixtures\wiaa\*.html
git add tests\fixtures\wiaa\manifest_wisconsin.yml

# Commit with descriptive message
git commit -m "Add WIAA 2024 Div2-4 fixtures with URL overrides

- Discovered actual URLs manually (differ from Div1 pattern)
- Updated manifest with explicit url: fields for Div2-4
- Downloaded and validated 6 HTML fixtures
- Coverage: 8/80 (10%)
- Tests: All passing"

# Push to your branch
git push origin <your-branch>
```

---

## Troubleshooting

### Problem: "URL Source: fallback" even after adding url: field

**Causes**:
- YAML indentation wrong
- `url` field has typo
- URL value is empty string

**Fix**:
```yaml
# ✅ CORRECT:
- year: 2024
  gender: "Boys"
  division: "Div2"
  url: "https://actual-url.com"  # Properly indented, 2 spaces

# ❌ WRONG:
- year: 2024
  gender: "Boys"
  division: "Div2"
url: "https://actual-url.com"  # Not indented (0 spaces) - won't be associated with fixture
```

### Problem: Script still opens wrong URL

**Debug steps**:
1. Run with dry-run to see what URL is being used
2. Check manifest YAML syntax with a validator
3. Verify you saved manifest after editing
4. Try restarting script

### Problem: WIAA site has PDF, not HTML

**Solutions**:

**Option A: Note as unavailable**:
```yaml
- year: 2016
  gender: "Boys"
  division: "Div3"
  status: "unavailable"
  notes: "WIAA only has PDF for this bracket, no HTML available"
```

**Option B: Add PDF URL for future processing**:
```yaml
- year: 2016
  gender: "Boys"
  division: "Div3"
  status: "blocked"
  url: "https://wiaawi.org/brackets/2016_boys_div3.pdf"
  notes: "PDF only, needs PDF parser (future enhancement)"
```

### Problem: Dry-run shows URL but browser gives 404

**Possible causes**:
1. **WIAA site structure changed** → Find new URL manually
2. **URL copied incorrectly** → Check for typos, missing parts
3. **Bracket doesn't exist** → Mark as unavailable in manifest

---

## Examples

### Example 1: Fixing 2024 Boys Div2

**1. Dry-run shows fallback**:
```
URL Source: fallback
⚠️  WARNING: Using fallback pattern - may 404!
```

**2. Find real URL**:
- Navigate to wiaawi.org → Basketball → 2024 Boys Div2
- Copy URL: `https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_BBB_Div2_Final.html`

**3. Update manifest**:
```yaml
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
  url: "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_BBB_Div2_Final.html"
  notes: "Actual URL uses 'BBB' instead of 'Basketball_Boys', discovered 2025-11-14"
```

**4. Verify with dry-run**:
```
URL Source: manifest  ← ✅ Good!
```

**5. Download**:
```powershell
python -m scripts.open_missing_wiaa_fixtures --year 2024 --gender Boys --division Div2
```

### Example 2: Historical Year with Different Pattern

**For 2022 fixtures** that all use different URLs:

```yaml
# Pattern: Different domain for historical brackets
- year: 2022
  gender: "Boys"
  division: "Div1"
  status: "planned"
  priority: 2
  url: "https://archive.wiaawi.org/basketball/2022/boys-div1-bracket.html"
  notes: "Historical brackets use archive subdomain"

- year: 2022
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 2
  url: "https://archive.wiaawi.org/basketball/2022/boys-div2-bracket.html"
  notes: "Historical brackets use archive subdomain"
```

---

## Best Practices

### ✅ DO:
- Run dry-run first to identify fallback URLs
- Manually verify URLs in browser before adding to manifest
- Document in `notes:` field why URL override was needed
- Commit after each batch of fixtures (clear checkpoints)
- Keep manifest organized by year

### ❌ DON'T:
- Guess URLs or try variations programmatically
- Add URLs without verifying they work in browser
- Leave out `notes:` field (future you will thank you)
- Commit broken/404 URLs to manifest
- Skip validation step

---

## Summary

**New Capability**: Explicit URL overrides in manifest
**Problem Solved**: 404 errors from incorrect URL patterns
**Workflow Impact**: Adds ~2 min per fixture (manual URL discovery)
**Data Quality**: No guessing, all URLs verified manually
**Maintainability**: URLs documented in manifest, easy to update

**Total Time** for 6 Priority 1 fixtures:
- URL discovery: ~10 minutes (find all 6 URLs)
- Manifest updates: ~5 minutes (edit YAML)
- Download: ~10 minutes (save 6 HTML files)
- Validation: ~5 minutes (run inspectors)
- **Total**: ~30 minutes

**Comparison to Old Approach**:
- Old: Hit 404, give up or hack around it
- New: Hit 404, fix data, document, continue

---

**Status**: Workflow tested and ready for use
**Next Step**: Apply to 2024 Priority 1 fixtures (Boys/Girls Div2-4)
