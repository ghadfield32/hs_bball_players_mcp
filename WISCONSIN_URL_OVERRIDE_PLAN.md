# Wisconsin URL Override Implementation Plan

## Integration Strategy

### Current Architecture:
```
Manifest (YAML)
  ↓ load
FixtureBrowserHelper._load_manifest()
  ↓ filter
FixtureBrowserHelper.get_missing_fixtures()
  ↓ for each fixture
FixtureBrowserHelper._construct_url(year, gender, division)
  ↓ returns hard-coded pattern URL
open_fixture_in_browser(fixture_with_url)
```

### New Architecture:
```
Manifest (YAML) [with optional 'url' field]
  ↓ load
FixtureBrowserHelper._load_manifest()
  ↓ filter
FixtureBrowserHelper.get_missing_fixtures()
  ↓ for each fixture
FixtureBrowserHelper._construct_url(entry_dict)  ← Changed to accept full entry
  ↓ checks entry["url"] first, falls back to pattern
  ↓ prints debug info about URL source
open_fixture_in_browser(fixture_with_url)
```

## Changes Required

### 1. Update `_construct_url()` Method

**Current signature**:
```python
def _construct_url(self, year: int, gender: str, division: str) -> str:
```

**New signature**:
```python
def _construct_url(self, entry: dict) -> str:
```

**New logic**:
1. Check if `entry.get("url")` exists and is non-empty
2. If yes: return it with debug message "Using manifest URL override"
3. If no: build fallback URL with warning "Using default pattern, may 404"

**Backward compatibility**: Maintained - fallback behavior same as before

### 2. Update `get_missing_fixtures()` Method

**Current** (line 185):
```python
missing.append({
    ...
    "url": self._construct_url(year_val, gender_val, division_val),
    ...
})
```

**New**:
```python
missing.append({
    ...
    "url": self._construct_url(entry),  # Pass full entry dict
    ...
})
```

### 3. Add `--dry-run` CLI Flag

**Purpose**: List fixtures and URLs without opening browser

**Implementation**:
- Add argparse argument
- In `main()`, check dry-run flag
- If dry-run: print fixture info, don't call `webbrowser.open()`

### 4. Enhance Debug Output

**In `open_fixture_in_browser()`**:
- Show URL source (manifest vs fallback)
- Print warnings for fallback usage
- Suggest how to fix 404s

## Dependencies

### None Added:
- ✅ No new imports needed (webbrowser, yaml already used)
- ✅ No new dependencies
- ✅ No schema changes to test files

### Manifest Changes (backward compatible):
- Add optional `url` field to fixture entries
- If not present: script behaves as before (with warning)
- If present: script uses explicit URL

## Testing Strategy

### Unit Testing (Manual):

1. **Test with URL override**:
   ```yaml
   - year: 2024
     gender: "Boys"
     division: "Div2"
     url: "https://test.example.com/test.html"
   ```
   Expected: Opens test.example.com URL

2. **Test without URL override**:
   ```yaml
   - year: 2024
     gender: "Boys"
     division: "Div3"
     # No url field
   ```
   Expected: Uses fallback pattern with warning

3. **Test dry-run mode**:
   ```powershell
   python -m scripts.open_missing_wiaa_fixtures --priority 1 --dry-run
   ```
   Expected: Prints URLs, doesn't open browser

### Integration Testing:

1. **Existing fixtures still work**:
   - Coverage script still reads manifest
   - Inspection script still validates files
   - Tests still pass for present fixtures

2. **New workflow**:
   - Dry-run shows 404-prone URLs
   - User manually finds real URLs
   - Updates manifest with URL overrides
   - Re-runs script successfully

## Rollback Plan

If issues occur:
1. Revert `_construct_url()` signature change
2. Revert `get_missing_fixtures()` call site
3. Remove `--dry-run` flag
4. Existing behavior restored

**Risk**: LOW - Changes are additive, fallback preserves old behavior

## Success Criteria

✅ **Code changes**:
- `_construct_url()` accepts entry dict
- Checks `entry["url"]` first
- Falls back to pattern with warning
- All changes backward compatible

✅ **User workflow**:
- Dry-run shows URLs before attempting
- 404s are visible and actionable
- Manifest documents discovered URLs
- No guessing or hiding problems

✅ **Testing**:
- Existing tests pass
- Coverage dashboard still works
- Inspection scripts still work
- New fixtures validate correctly

## Timeline

1. Code implementation: 20 minutes
2. Testing: 10 minutes
3. Documentation: 10 minutes
4. **Total**: 40 minutes

**Next Step**: Implement changes incrementally
