# Wisconsin WIAA Fixture Acquisition Guide

This guide provides step-by-step instructions for downloading Wisconsin WIAA basketball bracket HTML fixtures to expand test coverage.

## Overview

Wisconsin WIAA fixtures are HTML snapshots of tournament bracket pages that enable offline testing without hitting the WIAA website (which blocks automated requests with HTTP 403 errors).

**Current Status:** 2/80 fixtures present (2.5% coverage)
**Target:** 80 fixtures (10 years × 2 genders × 4 divisions)

## Why Manual Download?

The WIAA website (`halftime.wiaawi.org`) has anti-bot protections that return HTTP 403 errors for automated HTTP requests. Manual browser downloads work because:
- Browsers send proper User-Agent headers
- Human-initiated requests bypass bot detection
- You can complete any CAPTCHA if required

## Prerequisites

- Web browser (Chrome, Firefox, Edge, Safari)
- Access to the hs_bball_players_mcp repository
- Python environment set up (for validation)

## Step-by-Step Process

### Step 1: Identify Which Fixtures to Download

Check the manifest for "planned" fixtures:

```bash
# View all planned fixtures
grep -A 2 'status: "planned"' tests/fixtures/wiaa/manifest_wisconsin.yml

# Or use the sanity script to see what's planned
python scripts/inspect_wiaa_fixture.py --all-planned
```

**Priority 1 (Complete 2024):**
- 2024_Basketball_Boys_Div2.html
- 2024_Basketball_Boys_Div3.html
- 2024_Basketball_Boys_Div4.html
- 2024_Basketball_Girls_Div2.html
- 2024_Basketball_Girls_Div3.html
- 2024_Basketball_Girls_Div4.html

**Priority 2 (Add 2023):**
- 2023_Basketball_{Boys|Girls}_{Div1|Div2|Div3|Div4}.html (8 fixtures)

### Step 2: Find the Bracket URL

Wisconsin WIAA tournament brackets are hosted at:
```
https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/
```

**URL Pattern:**
```
{year}_Basketball_{gender}_{division}_Sec{section}_{subsection}.html
```

**Examples:**
- 2024 Boys Div2 Section 1: `https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_Basketball_Boys_Div2_Sec1_2.html`
- 2024 Girls Div3 Section 2: `https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_Basketball_Girls_Div3_Sec2_2.html`

**How to discover URLs:**
1. Go to [WIAA Brackets Portal](https://www.wiaawi.org/Sports/Basketball/Boys-Basketball)
2. Navigate to "Tournament Brackets" or "Results"
3. Select year, gender, and division
4. Right-click the bracket page and "View Page Source" to see the exact URL
5. Copy the URL from the address bar

**Note:** Wisconsin typically has 8 sections per division. You can try different section numbers (1-8) to find active bracket pages.

### Step 3: Download the Bracket HTML

**Method 1: Save Page As (Recommended)**

1. Open the bracket URL in your browser
2. Wait for the page to fully load (verify bracket table is visible)
3. Right-click anywhere on the page
4. Select "Save Page As..." or "Save As..." (CTRL+S / CMD+S)
5. In the save dialog:
   - **Save as type:** "Web Page, HTML only" or "HTML only"
   - **DO NOT** select "Web Page, Complete" (we don't need CSS/images)
   - **Filename:** Use exact naming convention: `{year}_Basketball_{gender}_{division}.html`
   - **Location:** Save to `tests/fixtures/wiaa/`

**Method 2: View Source and Copy**

1. Open the bracket URL in your browser
2. Right-click → "View Page Source" (or CTRL+U / CMD+Option+U)
3. Select all (CTRL+A / CMD+A)
4. Copy (CTRL+C / CMD+C)
5. Create new file in `tests/fixtures/wiaa/{year}_Basketball_{gender}_{division}.html`
6. Paste and save

### Step 4: Add Provenance Comment

Add a comment at the top of the saved HTML file for tracking:

```html
<!--
  Source: https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_Basketball_Boys_Div2_Sec1_2.html
  Downloaded: 2025-11-14
  Author: Your Name
  Notes: WIAA Wisconsin Boys Basketball - Division 2 - 2024 Tournament Bracket
  Section/Subsection: Sec1_2 (adjust if you merged multiple sections)
-->
```

Place this comment **before** the `<!DOCTYPE>` or `<html>` tag.

### Step 5: Validate the Fixture

Run the sanity check script to ensure the fixture parses correctly:

```bash
# Check the specific fixture you just downloaded
python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2
```

**What the script checks:**
- ✅ File exists and is readable
- ✅ Parses without errors
- ✅ Produces > 0 games
- ✅ No self-games (team vs itself)
- ✅ Scores in valid range (0-200)
- ✅ Expected rounds present (Regional, Sectional, State)
- ✅ Round distribution looks reasonable
- ✅ Championship game exists

**If the script PASSES:**
```
✅ PASS: Fixture passed all critical checks
```
→ Proceed to Step 6

**If the script FAILS:**
```
❌ FAIL: [specific error message]
```
→ Fix the issue:
- **"Fixture file does not exist"**: Check filename spelling and location
- **"Parser error"**: HTML may be incomplete; re-download
- **"Parsed 0 games"**: Wrong URL or empty bracket; verify URL
- **"Invalid scores"**: Parser issue; report to maintainer
- **"Missing expected rounds"**: May be partial bracket; check if it's a subsection

### Step 6: Update Manifest Status

Once the fixture passes validation, update its status in the manifest:

```yaml
# In tests/fixtures/wiaa/manifest_wisconsin.yml
# Change from:
  - year: 2024
    gender: "Boys"
    division: "Div2"
    status: "planned"
    priority: 1

# To:
  - year: 2024
    gender: "Boys"
    division: "Div2"
    status: "present"
    notes: "Downloaded 2025-11-14 - 15 games validated"
```

### Step 7: Run Historical Tests

Verify the new fixture is tested:

```bash
# Run manifest validation test
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py::test_manifest_validation -v

# Run all historical tests (your new fixture will no longer be skipped)
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

# Check coverage report
python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py::test_wisconsin_fixture_coverage_report -v -s
```

Expected result: The tests for your fixture now **PASS** instead of **SKIP**.

### Step 8: Commit the Fixture

```bash
# Add the fixture file
git add tests/fixtures/wiaa/{year}_Basketball_{gender}_{division}.html

# Update manifest
git add tests/fixtures/wiaa/manifest_wisconsin.yml

# Commit with descriptive message
git commit -m "Add Wisconsin WIAA fixture: {year} {gender} {division}

- Downloaded from halftime.wiaawi.org on YYYY-MM-DD
- Validated with inspect_wiaa_fixture.py (15 games, all checks passed)
- Updated manifest status to 'present'
- Coverage now: X/80 fixtures (X.X%)"

# Push to branch
git push
```

## Troubleshooting

### Issue: HTTP 403 Forbidden

**Symptom:** Browser shows "Access Denied" or "403 Forbidden"

**Solution:**
- Clear browser cache and cookies
- Try a different browser
- Try incognito/private mode
- Wait 10 minutes and try again (may be temporary rate limiting)
- Check if URL is correct (typos in year/gender/division)

### Issue: Empty Bracket Page

**Symptom:** Page loads but shows "No games found" or empty table

**Solution:**
- Bracket may not exist for that division in that year
- Try different section numbers (Sec1_2, Sec2_2, etc.)
- Verify the year/gender/division combination is valid on WIAA site
- If truly unavailable, update manifest status to "unavailable"

### Issue: Parser Errors

**Symptom:** `inspect_wiaa_fixture.py` fails with parser error

**Solution:**
1. Check if HTML is complete (should end with `</html>`)
2. Re-download the file (may have been truncated)
3. Verify you saved as "HTML only" not "Complete Page"
4. If issue persists, report to maintainer with the HTML file

### Issue: Fixture Parses But Has Wrong Data

**Symptom:** Script passes but games look wrong (wrong teams, scores, etc.)

**Solution:**
- Verify you downloaded the correct year/gender/division
- Check if you accidentally saved a different bracket page
- Look at the HTML source to verify content matches expectations
- Re-download if needed

## Expansion Roadmap

### Phase 1: Complete 2024 (Target: 8/80 fixtures = 10% coverage)
- [x] 2024 Boys Div1 (present)
- [x] 2024 Girls Div1 (present)
- [ ] 2024 Boys Div2 (planned)
- [ ] 2024 Boys Div3 (planned)
- [ ] 2024 Boys Div4 (planned)
- [ ] 2024 Girls Div2 (planned)
- [ ] 2024 Girls Div3 (planned)
- [ ] 2024 Girls Div4 (planned)

### Phase 2: Add 2023 (Target: 16/80 fixtures = 20% coverage)
- [ ] 2023 Boys Div1-4 (planned)
- [ ] 2023 Girls Div1-4 (planned)

### Phase 3: Add 2022 (Target: 24/80 fixtures = 30% coverage)
- [ ] 2022 Boys Div1-4 (planned)
- [ ] 2022 Girls Div1-4 (planned)

### Phase 4: Historical Backfill (Target: 80/80 fixtures = 100% coverage)
- [ ] 2021 Boys/Girls Div1-4 (8 fixtures)
- [ ] 2020 Boys/Girls Div1-4 (8 fixtures)
- [ ] 2019 Boys/Girls Div1-4 (8 fixtures)
- [ ] 2018 Boys/Girls Div1-4 (8 fixtures)
- [ ] 2017 Boys/Girls Div1-4 (8 fixtures)
- [ ] 2016 Boys/Girls Div1-4 (8 fixtures)
- [ ] 2015 Boys/Girls Div1-4 (8 fixtures)

## File Naming Convention

**CRITICAL:** Use exact naming convention for fixture files:

```
{year}_Basketball_{gender}_{division}.html
```

**Valid Examples:**
- ✅ `2024_Basketball_Boys_Div1.html`
- ✅ `2023_Basketball_Girls_Div4.html`
- ✅ `2022_Basketball_Boys_Div2.html`

**Invalid Examples:**
- ❌ `2024_boys_div1.html` (wrong case)
- ❌ `2024_Basketball_Boys_Division1.html` (Division vs Div)
- ❌ `basketball_2024_boys_div1.html` (wrong order)
- ❌ `2024_Basketball_Boys_D1.html` (D1 vs Div1)

**Why it matters:** Test code looks for exact filenames:
```python
fixture_path = FIXTURES_DIR / f"{year}_Basketball_{gender}_{division}.html"
```

## Quality Standards

Every fixture should meet these standards before marking as "present":

1. **Completeness:** Full HTML document with DOCTYPE, html, head, body tags
2. **Provenance:** Comment at top with source URL, download date, author
3. **Parseable:** Passes all checks in `inspect_wiaa_fixture.py`
4. **Validated:** At least these checks pass:
   - Games count > 0
   - No self-games
   - Valid scores (0-200)
   - Expected rounds present
   - Championship game exists
5. **Documented:** Manifest updated with status="present" and notes

## Advanced: Merging Multiple Section Files

Some divisions split brackets across multiple section files (e.g., `Sec1_2.html`, `Sec2_2.html`, etc.).

**Option A: Download One Representative Section**
- Choose the section with the most complete bracket
- Document which section in the provenance comment
- This is sufficient for testing purposes

**Option B: Merge Multiple Sections**
- Download all sections for the division
- Extract the game tables from each
- Manually merge into a single HTML file
- Ensure no duplicate games
- Validate with sanity script

For testing purposes, **Option A is recommended** - we just need a representative sample of games from each division to validate the parser.

## Getting Help

**Issues with fixture acquisition:**
1. Check this guide's troubleshooting section
2. Run `python scripts/inspect_wiaa_fixture.py --help`
3. Review existing fixtures in `tests/fixtures/wiaa/` for examples
4. Check manifest at `tests/fixtures/wiaa/manifest_wisconsin.yml`

**Issues with validation:**
1. Run verbose sanity check: `python scripts/inspect_wiaa_fixture.py --year YYYY --gender G --division D`
2. Look at parser code: `src/datasources/us/wisconsin_wiaa.py`
3. Run parser tests: `python -m pytest tests/test_datasources/test_wisconsin_wiaa_parser.py -v`

**Still stuck:**
- Open an issue with the HTML file attached
- Include the output from `inspect_wiaa_fixture.py`
- Mention which year/gender/division you're trying to add

## Contribution Checklist

Before submitting a PR with new fixtures:

- [ ] Downloaded HTML using browser (to avoid 403s)
- [ ] Saved with exact naming convention
- [ ] Added provenance comment to HTML file
- [ ] Validated with `inspect_wiaa_fixture.py` (passed all checks)
- [ ] Updated manifest status to "present"
- [ ] Added notes to manifest entry (download date, game count)
- [ ] Ran historical tests (fixture no longer skipped)
- [ ] Ran coverage report (percentage increased)
- [ ] Committed with descriptive message
- [ ] Pushed to branch

## Resources

- **WIAA Official Site:** https://www.wiaawi.org
- **Tournament Brackets:** https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/
- **Manifest:** `tests/fixtures/wiaa/manifest_wisconsin.yml`
- **Sanity Script:** `scripts/inspect_wiaa_fixture.py`
- **Historical Tests:** `tests/test_datasources/test_wisconsin_wiaa_historical.py`
- **Parser Code:** `src/datasources/us/wisconsin_wiaa.py`
