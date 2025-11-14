# Wisconsin URL Override - Complete Function Changes

**File Modified**: `scripts/open_missing_wiaa_fixtures.py`
**Changes**: 3 functions modified, 1 section added
**Backward Compatible**: Yes (fallback behavior preserved)

---

## Function 1: `_construct_url()` - MODIFIED

**Line Numbers**: 118-163

**Old Signature**:
```python
def _construct_url(self, year: int, gender: str, division: str) -> str:
```

**New Signature**:
```python
def _construct_url(self, entry: dict) -> tuple[str, str]:
```

**Complete New Function**:
```python
def _construct_url(self, entry: dict) -> tuple[str, str]:
    """
    Construct or retrieve WIAA URL for a given fixture.

    NEW: Supports explicit URL overrides in manifest to fix 404 issues.

    Priority:
    1. Use manifest 'url' field if present (explicit override)
    2. Fall back to halftime.wiaawi.org pattern with warning

    Args:
        entry: Manifest entry dict with year, gender, division, and optional url

    Returns:
        Tuple of (url, source) where source is "manifest" or "fallback"

    Example manifest entry with override:
        - year: 2024
          gender: "Boys"
          division: "Div2"
          url: "https://actual-url-from-wiaa-site.com/bracket.html"
          notes: "URL discovered manually, halftime pattern gives 404"
    """
    year = entry["year"]
    gender = entry["gender"]
    division = entry["division"]

    # Priority 1: Check for explicit URL override in manifest
    if "url" in entry and entry["url"]:
        url = entry["url"]
        if self.verbose:
            print(f"  URL source: manifest override (explicit 'url' field)")
        return url, "manifest"

    # Priority 2: Fall back to halftime.wiaawi.org pattern
    filename = f"{year}_Basketball_{gender}_{division}.html"
    url = BASE_URL + filename

    if self.verbose:
        print(f"  URL source: fallback pattern (no 'url' in manifest)")
        print(f"  ⚠️  WARNING: If this URL gives 404, you need to:")
        print(f"      1. Manually find the real bracket URL on WIAA website")
        print(f"      2. Edit tests/fixtures/wiaa/manifest_wisconsin.yml")
        print(f"      3. Add 'url: <actual_url>' to the {year} {gender} {division} entry")

    return url, "fallback"
```

**What Changed**:
- ✅ Now accepts full `entry` dict instead of individual parameters
- ✅ Returns tuple `(url, source)` instead of just `url`
- ✅ Checks for `entry["url"]` first (new behavior)
- ✅ Falls back to old pattern with warning (backward compatible)
- ✅ Adds debug output showing URL source

---

## Function 2: `get_missing_fixtures()` - MODIFIED

**Line Numbers**: 165-237 (specifically lines 222-235)

**Section Changed**:
```python
# OLD CODE (lines 181-189):
missing.append({
    "year": year_val,
    "gender": gender_val,
    "division": division_val,
    "url": self._construct_url(year_val, gender_val, division_val),
    "filename": file_path.name,
    "status": status,
    "priority": entry.get("priority")
})

# NEW CODE (lines 222-235):
# Add to missing list
# NEW: Pass full entry to _construct_url for URL override support
url, url_source = self._construct_url(entry)

missing.append({
    "year": year_val,
    "gender": gender_val,
    "division": division_val,
    "url": url,
    "url_source": url_source,  # Track whether URL is from manifest or fallback
    "filename": file_path.name,
    "status": status,
    "priority": entry.get("priority")
})
```

**What Changed**:
- ✅ Pass full `entry` dict to `_construct_url()` instead of individual values
- ✅ Unpack tuple return: `url, url_source = self._construct_url(entry)`
- ✅ Add `url_source` to fixture dict for debugging
- ✅ Adds comment explaining change

---

## Function 3: `main()` - MODIFIED

**Line Numbers**: 417-589 (specifically lines 507-567)

**Section Added**: Dry-run mode handler

**Complete New Section** (lines 514-561):
```python
# DRY-RUN MODE: Just show what would be downloaded
if args.dry_run:
    print("\n" + "="*80)
    print("DRY-RUN MODE: Showing URLs without opening browser")
    print("="*80)

    if not missing:
        print("\n✅ No missing fixtures found!")
        print(f"   {helper.stats['already_present']} fixtures already present")
        return

    total = len(missing)
    print(f"\nFound {total} missing fixture(s) to download:")
    print(f"({helper.stats['already_present']} fixtures already present)\n")

    for i, fixture in enumerate(missing, 1):
        year = fixture["year"]
        gender = fixture["gender"]
        division = fixture["division"]
        url = fixture["url"]
        url_source = fixture["url_source"]
        filename = fixture["filename"]

        print(f"{'-'*80}")
        print(f"Fixture {i}/{total}: {year} {gender} {division}")
        print(f"{'-'*80}")
        print(f"  Filename:    {filename}")
        print(f"  Save to:     {FIXTURES_DIR.resolve()}")
        print(f"  URL:         {url}")
        print(f"  URL Source:  {url_source}")

        if url_source == "fallback":
            print(f"  ⚠️  WARNING: Using fallback pattern - may 404!")
            print(f"     If this URL doesn't work, add 'url:' field to manifest")

        print()

    print(f"\n{'='*80}")
    print("DRY-RUN COMPLETE - No browsers opened")
    print("="*80)
    print("\nNext steps:")
    print("1. For any fixtures showing 'fallback' URL source:")
    print("   - Manually find the real bracket URL on WIAA website")
    print("   - Edit tests/fixtures/wiaa/manifest_wisconsin.yml")
    print("   - Add 'url: <actual_url>' field to that fixture entry")
    print("2. Re-run without --dry-run to download fixtures")
    print()
    return

# NORMAL MODE: Process fixtures (open browsers)
helper.process_batch(missing, batch_size=args.batch_size)
```

**What Changed**:
- ✅ New `if args.dry_run:` block before `process_batch()` call
- ✅ Shows fixture info without opening browser
- ✅ Highlights fixtures using fallback URLs (404-prone)
- ✅ Provides actionable next steps
- ✅ Returns early without calling `process_batch()` in dry-run mode

---

## Section 4: argparse - MODIFIED

**Line Numbers**: 482-491

**Addition**:
```python
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Show what would be downloaded without opening browser (preview URLs)"
)
```

**What Changed**:
- ✅ Added new CLI flag `--dry-run`
- ✅ Boolean flag (no arguments)
- ✅ Help text explains purpose

---

## Section 5: Help Examples - MODIFIED

**Line Numbers**: 422-450

**Addition** (line 423-424):
```python
Examples:
  # Preview URLs before downloading (DRY-RUN)
  python scripts/open_missing_wiaa_fixtures.py --priority 1 --dry-run
  # ... rest of examples
```

**Addition** (line 450):
```python
  - Use --dry-run to preview URLs before attempting to download (helps catch 404s)
```

**What Changed**:
- ✅ Added dry-run example as first example (most useful)
- ✅ Added note in Notes section about dry-run usage

---

## Summary of Changes

### Files Modified:
- `scripts/open_missing_wiaa_fixtures.py`: 3 functions + 2 sections

### Lines Changed:
- Modified: ~90 lines
- Added: ~60 lines
- Total impact: ~150 lines

### Backward Compatibility:
- ✅ **Preserved**: Script works same way if no `url` fields in manifest
- ✅ **Enhanced**: Adds URL override capability when needed
- ✅ **Additive**: New feature (dry-run) doesn't affect normal usage

### Breaking Changes:
- ❌ **None**: All changes are backward compatible

### Dependencies Added:
- ❌ **None**: Uses existing imports (no new packages)

---

## Testing Checklist

### ✅ Syntax Validation:
```bash
python -m py_compile scripts/open_missing_wiaa_fixtures.py
# Result: ✅ Passes
```

### ✅ Help Output:
```bash
python -m scripts.open_missing_wiaa_fixtures --help
# Result: ✅ Shows --dry-run flag
```

### ⏳ Dry-Run Test:
```bash
python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
# Expected: Shows URLs without opening browser
```

### ⏳ URL Override Test:
```yaml
# Add to manifest:
- year: 2024
  gender: "Boys"
  division: "Div2"
  url: "https://test.example.com/test.html"

# Run dry-run:
python -m scripts.open_missing_wiaa_fixtures --year 2024 --dry-run
# Expected: Shows "URL Source: manifest"
```

### ⏳ Fallback Test:
```yaml
# Entry without url field:
- year: 2024
  gender: "Boys"
  division: "Div3"
  # No url field

# Run dry-run:
python -m scripts.open_missing_wiaa_fixtures --year 2024 --dry-run
# Expected: Shows "URL Source: fallback" with warning
```

---

## Rollback Instructions

If issues occur, revert these specific changes:

### 1. Revert `_construct_url()` signature:
```python
# Change back to:
def _construct_url(self, year: int, gender: str, division: str) -> str:
    filename = f"{year}_Basketball_{gender}_{division}.html"
    return BASE_URL + filename
```

### 2. Revert `get_missing_fixtures()` call:
```python
# Change back to:
"url": self._construct_url(year_val, gender_val, division_val),
# Remove: "url_source": url_source,
```

### 3. Remove `--dry-run` flag:
```python
# Delete lines 487-491
```

### 4. Remove dry-run handler in `main()`:
```python
# Delete lines 514-561
```

**Result**: Script returns to original behavior

---

**Status**: All functions documented and ready for integration
**Next Step**: Update PROJECT_LOG with compact summary
