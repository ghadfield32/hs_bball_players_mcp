# Wisconsin WIAA 404 Error - Root Cause Analysis

**Date**: 2025-11-14
**Issue**: 404 errors when downloading 2024 Div2-4 fixtures
**Status**: Data problem, not code bug

---

## 1. EXAMINE THE OUTPUT

### Expected Behavior:
```
Script Execution Flow:
1. Load manifest_wisconsin.yml
2. Find fixtures with status="planned", priority=1
3. For each fixture (year, gender, division):
   - Build URL: BASE_URL + f"{year}_Basketball_{gender}_{division}.html"
   - Open URL in browser
   - User saves HTML file
4. Mark fixtures as "present" after validation
```

### Actual Output:
```
Fixture 1/6: 2024 Boys Div2
URL: https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/2024_Basketball_Boys_Div2.html

Server Error
404 - File or directory not found.
```

### Discrepancy:
- ✅ **Script Logic**: Working as written (correct Python code)
- ❌ **Data Assumption**: URL pattern is WRONG for this fixture
- ❌ **Result**: Browser opens valid URL that doesn't exist on WIAA server

---

## 2. REVIEW ERROR MESSAGES

### HTTP 404 Breakdown:

**What it means**:
- Server received request successfully (connection OK)
- Requested resource doesn't exist at that URL
- File may exist elsewhere with different name/path

**What it DOESN'T mean**:
- Python code has bugs
- Import errors
- Network connectivity issues

### Why the URL is Wrong:

**Assumption in code**:
```python
# scripts/open_missing_wiaa_fixtures.py line 118-121
def _construct_url(self, year: int, gender: str, division: str) -> str:
    """Construct WIAA URL for a given fixture."""
    filename = f"{year}_Basketball_{gender}_{division}.html"
    return BASE_URL + filename

# BASE_URL = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/"
```

**The assumption**:
"All Wisconsin WIAA brackets follow the pattern:
`{year}_Basketball_{gender}_{division}.html`"

**Reality**:
- 2024 Boys/Girls Div1: ✅ Works (we have these fixtures)
- 2024 Boys/Girls Div2-4: ❌ 404 errors (different URL pattern)
- 2023, 2022, 2015-2021: ❓ Unknown (likely different patterns)

---

## 3. TRACE CODE EXECUTION

### Step-by-Step Flow for 2024 Boys Div2:

```python
# Step 1: Load manifest
manifest = {
    "fixtures": [
        {
            "year": 2024,
            "gender": "Boys",
            "division": "Div2",
            "status": "planned",
            "priority": 1
            # NOTE: No "url" field!
        }
    ]
}

# Step 2: Filter for priority=1, status != "present"
missing_fixtures = [
    (2024, "Boys", "Div2"),
    (2024, "Boys", "Div3"),
    # ... etc
]

# Step 3: Build URL (THE PROBLEM)
def _construct_url(2024, "Boys", "Div2"):
    filename = "2024_Basketball_Boys_Div2.html"
    url = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/HTML/" + filename
    return url
    # Returns: https://...HTML/2024_Basketball_Boys_Div2.html
    # But this URL doesn't exist!

# Step 4: Open browser with wrong URL
webbrowser.open("https://...HTML/2024_Basketball_Boys_Div2.html")
# Result: 404 page opens in browser
```

### Intermediate State Analysis:

| Variable | Value | Correctness |
|----------|-------|-------------|
| `year` | 2024 | ✅ Correct from manifest |
| `gender` | "Boys" | ✅ Correct from manifest |
| `division` | "Div2" | ✅ Correct from manifest |
| `filename` | "2024_Basketball_Boys_Div2.html" | ⚠️ Assumption (may be wrong) |
| `BASE_URL` | "https://halftime.wiaawi.org/.../HTML/" | ⚠️ Assumption (may be wrong path) |
| `url` | Full concatenated URL | ❌ **404 - Doesn't exist** |

---

## 4. DEBUG ASSUMPTIONS

### Assumption 1: "All brackets have same URL pattern"

**Status**: ❌ **FALSE**

**Evidence**:
- 2024 Div1: Works with pattern
- 2024 Div2: 404 with same pattern
- Conclusion: Pattern varies by division/year

**Why this assumption was made**:
- Initial implementation only had 2 fixtures (2024 Div1)
- Both worked with the pattern
- Assumption extrapolated to all fixtures

**Impact**:
- Cannot backfill 2023, 2022, 2015-2021 without knowing real URLs
- Will hit more 404s as we expand coverage

### Assumption 2: "URL is derivable from (year, gender, division)"

**Status**: ❌ **FALSE**

**Evidence**:
- Same inputs (2024, Boys, Div2) produce 404
- Different URL needed, but we can't derive it
- URL is **independent data**, not computable

**Correct Model**:
```
URL = f(year, gender, division)  ❌ WRONG
URL = data[year, gender, division]["url"]  ✅ CORRECT
```

### Assumption 3: "WIAA site structure is stable"

**Status**: ❌ **FALSE**

**Evidence**:
- Different divisions use different URLs
- Historical years may use different servers/paths
- May have PDFs instead of HTML for older years

**Implications**:
- Need flexible system to handle URL variations
- Need manual URL discovery process
- Need to store discovered URLs as data

---

## 5. POTENTIAL FIXES

### ❌ **Bad Fix 1**: Try different URL patterns until one works

```python
# DON'T DO THIS!
def _construct_url(year, gender, division):
    patterns = [
        f"{year}_Basketball_{gender}_{division}.html",
        f"{year}_{gender}_{division}.html",
        f"Basketball_{year}_{gender}_{division}.html",
        # ... endless guessing
    ]
    for pattern in patterns:
        url = BASE_URL + pattern
        if check_url_exists(url):  # Makes HTTP request
            return url
```

**Why bad**:
- Makes HTTP requests (violates bot protection respect)
- Guessing is unreliable
- Doesn't help with historical data
- Hides the real problem

### ❌ **Bad Fix 2**: Mark as "present" and fill with fake data

```python
# DON'T DO THIS!
if response_code == 404:
    # Just skip it and mark as present anyway
    update_manifest(status="present")
```

**Why bad**:
- Creates fake data in dataset
- Tests will pass but data is wrong
- Future users won't know which fixtures are real
- Violates "no covering up problems" rule

### ✅ **Good Fix**: Make URLs explicit data in manifest

```yaml
# manifest_wisconsin.yml
fixtures:
  - year: 2024
    gender: "Boys"
    division: "Div2"
    status: "planned"
    priority: 1
    url: "https://ACTUAL_URL_DISCOVERED_MANUALLY"  # ADD THIS
    notes: "URL discovered via WIAA site navigation"
```

```python
# scripts/open_missing_wiaa_fixtures.py
def _construct_url(self, entry: dict) -> str:
    """
    Get URL for fixture, with explicit override support.

    Priority:
    1. Use manifest 'url' field if present (explicit override)
    2. Fall back to halftime pattern with WARNING
    """
    # Check for explicit URL override first
    if "url" in entry and entry["url"]:
        return entry["url"]

    # Fall back to pattern (with warning)
    year, gender, division = entry["year"], entry["gender"], entry["division"]
    filename = f"{year}_Basketball_{gender}_{division}.html"
    url = BASE_URL + filename

    print(f"⚠️  WARNING: Using default URL pattern (no 'url' in manifest)")
    print(f"   If this 404s, add 'url: <actual_url>' to manifest entry")

    return url
```

**Why good**:
- URL becomes explicit data, not derived
- Manual discovery process is documented
- Works for any URL structure (HTML, PDF, different servers)
- No guessing or hiding problems
- Scalable to all historical years

---

## 6. RECOMMENDED WORKFLOW

### Phase 1: Enhance Scripts (Code Changes)

1. **Add URL override support to manifest**
   - Allow optional `url` field per fixture
   - Update loader to pass URL to constructor

2. **Update `_construct_url()` method**
   - Check manifest for explicit URL first
   - Fall back to pattern with visible warning
   - Never guess or hide 404s

3. **Add `--dry-run` mode**
   - Show all URLs without opening browser
   - Let user verify URLs before attempting download

4. **Add debug output**
   - Show URL source (manifest vs fallback)
   - Print warnings for fallback pattern usage
   - Make 404s visible and actionable

### Phase 2: Fix 2024 Div2-4 (Manual URL Discovery)

For each 404 fixture:

1. **Find real URL manually**:
   - Navigate to WIAA site in browser
   - Find 2024 Boys/Girls Div2-4 brackets
   - Copy actual URL from address bar

2. **Update manifest**:
   ```yaml
   - year: 2024
     gender: "Boys"
     division: "Div2"
     status: "planned"
     priority: 1
     url: "https://DISCOVERED_URL_HERE"
     notes: "URL discovered 2025-11-14, differs from Div1 pattern"
   ```

3. **Re-run script**:
   ```powershell
   python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
   # Verify URLs are correct
   python -m scripts.open_missing_wiaa_fixtures --priority 1
   # Download HTML files
   ```

4. **Validate and update**:
   - Run `inspect_wiaa_fixture.py` to validate
   - Update status to "present" after validation
   - Run tests to confirm

### Phase 3: Historical Backfill (Repeat for 2015-2023)

1. **Dry-run to see attempted URLs**:
   ```powershell
   python -m scripts.open_missing_wiaa_fixtures --year 2023 --dry-run
   ```

2. **For each 404**:
   - Manually find real URL on WIAA site
   - Update manifest with `url` field
   - Re-run without dry-run
   - Validate and mark present

3. **Document patterns discovered**:
   - If certain years/divisions use same pattern, document it
   - Create manifest notes for future reference
   - Track which fixtures are unavailable (PDF only, etc.)

---

## 7. ROOT CAUSE SUMMARY

**Problem**: 404 errors when downloading fixtures

**NOT the cause**:
- ❌ Python code bugs
- ❌ Import errors
- ❌ Script logic errors

**ACTUAL cause**:
- ✅ Hard-coded URL pattern assumption
- ✅ URL treated as derivable instead of data
- ✅ WIAA site uses different URLs for different fixtures

**Fix approach**:
- ✅ Make URLs explicit data in manifest
- ✅ Add override capability
- ✅ Manual discovery + documentation
- ✅ Never guess or hide problems

**Timeline**:
1. Code changes: ~30 minutes (add override support)
2. URL discovery: ~5 min per fixture (manual)
3. Validation: ~2 min per fixture (automated)
4. Total for 6 fixtures: ~1 hour

---

## 8. TESTING PLAN

### After Code Changes:

1. **Test URL override**:
   ```powershell
   # Add test URL to one manifest entry
   python -m scripts.open_missing_wiaa_fixtures --year 2024 --dry-run
   # Should show: "URL source: manifest (explicit override)"
   ```

2. **Test fallback warning**:
   ```powershell
   # Entry without URL field
   python -m scripts.open_missing_wiaa_fixtures --year 2023 --dry-run
   # Should show: "WARNING: Using default URL pattern"
   ```

3. **Test dry-run mode**:
   ```powershell
   python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
   # Should list all fixtures and URLs WITHOUT opening browser
   ```

4. **Test real download**:
   ```powershell
   # After fixing URLs in manifest
   python -m scripts.open_missing_wiaa_fixtures --priority 1
   # Should open correct URLs, no 404s
   ```

### After URL Discovery:

1. **Validate HTML files**:
   ```powershell
   python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2
   # Should parse successfully, show game counts
   ```

2. **Run tests**:
   ```powershell
   python -m pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v
   # New fixtures should be tested
   ```

3. **Check coverage**:
   ```powershell
   python scripts/show_wiaa_coverage.py
   # Should show 8/80 after completing 2024
   ```

---

**Status**: Analysis complete, ready for implementation
**Next Step**: Implement URL override system in `open_missing_wiaa_fixtures.py`
