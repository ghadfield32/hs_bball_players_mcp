# Wisconsin WIAA - Priority 1 Workflow (Complete 2024 Season)

**Goal**: Add 2024 Boys/Girls Div2-4 fixtures (6 total) to reach 8/80 coverage (10%)

**Time Estimate**: ~12 minutes (~2 min per fixture)

---

## Step 1: Manually Find Real WIAA URLs (5-10 minutes)

For each of these 6 fixtures, navigate the WIAA website and find the bracket page:

1. **2024 Boys Div2**
   - Go to: https://www.wiaawi.org or https://halftime.wiaawi.org
   - Navigate: Boys Basketball → 2024 → Division 2 → Tournament Bracket
   - Copy the real URL

2. **2024 Boys Div3**
   - Navigate: Boys Basketball → 2024 → Division 3 → Tournament Bracket
   - Copy the real URL

3. **2024 Boys Div4**
   - Navigate: Boys Basketball → 2024 → Division 4 → Tournament Bracket
   - Copy the real URL

4. **2024 Girls Div2**
   - Navigate: Girls Basketball → 2024 → Division 2 → Tournament Bracket
   - Copy the real URL

5. **2024 Girls Div3**
   - Navigate: Girls Basketball → 2024 → Division 3 → Tournament Bracket
   - Copy the real URL

6. **2024 Girls Div4**
   - Navigate: Girls Basketball → 2024 → Division 4 → Tournament Bracket
   - Copy the real URL

---

## Step 2: Add URL Overrides to Manifest (2-3 minutes)

Open: `tests/fixtures/wiaa/manifest_wisconsin.yml`

Find each of these 6 entries (search for "2024" and "priority: 1"):

```yaml
# BEFORE (fallback URL - 404s)
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
  file: tests/fixtures/wiaa/2024_Basketball_Boys_Div2.html

# AFTER (add the url: line you discovered)
- year: 2024
  gender: "Boys"
  division: "Div2"
  status: "planned"
  priority: 1
  file: tests/fixtures/wiaa/2024_Basketball_Boys_Div2.html
  url: "https://PASTE-REAL-URL-HERE"  # ← ADD THIS LINE
  notes: "URL verified manually 2025-11-14"
```

Repeat for all 6 fixtures (Boys/Girls Div2-4).

---

## Step 3: Verify No More Fallback Warnings (30 seconds)

```powershell
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
```

**Expected Output (all 6 should show)**:
```text
Fixture 1/6: 2024 Boys Div2
  URL:        https://YOUR-REAL-URL
  URL Source:  manifest  # ← NOT "fallback"!
```

If you still see `URL Source: fallback`, go back and check that fixture's `url:` field in the manifest.

---

## Step 4: Download HTML Fixtures (2-3 minutes)

```powershell
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 1
```

For each browser tab that opens:

1. ✅ Verify the bracket page loaded (not a 404 or redirect)
2. `Ctrl+S` (Save Page As...)
3. Format: **"Webpage, HTML Only"** (NOT "Complete")
4. Folder: `C:\docker_projects\betts_basketball\hs_bball_players_mcp\tests\fixtures\wiaa`
5. Filename: **Use the exact name shown** (e.g., `2024_Basketball_Boys_Div2.html`)

After saving all 6, verify in Explorer:

```text
tests\fixtures\wiaa\
├── 2024_Basketball_Boys_Div1.html   (already exists)
├── 2024_Basketball_Boys_Div2.html   (NEW)
├── 2024_Basketball_Boys_Div3.html   (NEW)
├── 2024_Basketball_Boys_Div4.html   (NEW)
├── 2024_Basketball_Girls_Div1.html  (already exists)
├── 2024_Basketball_Girls_Div2.html  (NEW)
├── 2024_Basketball_Girls_Div3.html  (NEW)
└── 2024_Basketball_Girls_Div4.html  (NEW)
```

Should see **8 total HTML files**, no `_files` folders.

---

## Step 5: Mark as Present in Manifest (1 minute)

Open: `tests/fixtures/wiaa/manifest_wisconsin.yml`

For all 6 fixtures you just downloaded:

```yaml
# BEFORE
status: "planned"

# AFTER
status: "present"
```

Save the file.

---

## Step 6: Validate Fixtures (1-2 minutes)

Spot-check a few to ensure they parsed correctly:

```powershell
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2024 --gender Boys --division Div2
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2024 --gender Girls --division Div3
```

**Expected output for each**:
```text
[+] File exists
[+] HTML parsed successfully
[+] Found X games
[+] Finals found: Team A vs Team B
```

If you see **"0 games parsed"** or weird data, re-download that HTML file.

---

## Step 7: Run Tests & Verify Coverage (30 seconds)

```powershell
# Run historical tests
.venv\Scripts\python.exe -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

# Check coverage
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py
```

**Target Results**:
- **2024 row**: `[########--------] 8/8 (100%)`
- **Overall**: `8/80 fixtures (10%)`
- **Boys**: `4/40 (10%)`
- **Girls**: `4/40 (10%)`
- **Tests**: All 2024 tests passing

---

## Step 8: Commit Your Work (1 minute)

```powershell
git add tests/fixtures/wiaa/*.html
git add tests/fixtures/wiaa/manifest_wisconsin.yml
git commit -m "Add Wisconsin WIAA 2024 Div2-4 fixtures (6 HTML files)

- Manually discovered real WIAA URLs for 2024 Boys/Girls Div2-4
- Added url overrides to manifest (no more fallback 404s)
- Downloaded and validated 6 HTML bracket files
- Coverage now 8/80 (10%), 2024 season complete

Phase 13.4 - Priority 1 complete"
```

---

## ✅ SUCCESS CRITERIA

- ✅ All 6 fixtures have `url:` in manifest (no fallback warnings)
- ✅ All 6 HTML files saved to `tests/fixtures/wiaa/`
- ✅ All 6 fixtures marked `status: present`
- ✅ Inspector shows >0 games for each fixture
- ✅ Coverage dashboard shows 8/80 (10%)
- ✅ All 2024 historical tests passing

---

## 🚀 AFTER PRIORITY 1 IS DONE

Move to **Priority 2** (16 fixtures - 2023 + 2022):

```powershell
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 2 --dry-run
```

Follow the same workflow:
1. Find real URLs (16 fixtures this time)
2. Add to manifest
3. Download HTML
4. Mark present
5. Validate
6. Test

**Target after Priority 2**: 24/80 (30%), top 3 seasons complete

---

## 📋 QUICK REFERENCE - Commands You'll Use

```powershell
# Activate venv (if not already)
& .venv\Scripts\Activate.ps1

# Dry-run to see what's missing
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run

# Download fixtures (after adding URLs to manifest)
.venv\Scripts\python.exe -m scripts.open_missing_wiaa_fixtures --priority 1

# Validate a specific fixture
.venv\Scripts\python.exe -m scripts.inspect_wiaa_fixture --year 2024 --gender Boys --division Div2

# Check coverage
.venv\Scripts\python.exe scripts/show_wiaa_coverage.py

# Run tests
.venv\Scripts\python.exe -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
```

---

**You've got this!** The tooling is ready, the workflow is clear, and you're only 6 fixtures away from completing the 2024 season.
