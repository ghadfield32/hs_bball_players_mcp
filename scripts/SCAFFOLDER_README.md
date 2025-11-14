# State Adapter Scaffolder

**Purpose**: Generate complete Phase 17/18 state adapters from template with metadata enrichment.

**Features**:
- ✅ Shared bracket parser integration
- ✅ Phase 18 metadata extraction (round, venue, tipoff)
- ✅ Canonical team IDs and deduplication
- ✅ Proper imports, docstrings, type hints
- ✅ Configurable classifications (numeric, letter, or roman)
- ✅ State-specific constants and URL patterns

## Quick Start

```bash
# Michigan with numeric divisions
python scripts/scaffold_state_adapter.py \
    --state "Michigan" \
    --abbrev "MI" \
    --org "MHSAA" \
    --base-url "https://www.mhsaa.com" \
    --classifications "1,2,3,4" \
    --schools 750

# North Carolina with letter classifications
python scripts/scaffold_state_adapter.py \
    --state "North Carolina" \
    --abbrev "NC" \
    --org "NCHSAA" \
    --base-url "https://www.nchsaa.org" \
    --classifications "4A,3A,2A,1A" \
    --schools 400 \
    --players "Michael Jordan,Chris Paul,James Worthy"

# Illinois
python scripts/scaffold_state_adapter.py \
    --state "Illinois" \
    --abbrev "IL" \
    --org "IHSA" \
    --base-url "https://www.ihsa.org" \
    --classifications "1A,2A,3A,4A" \
    --schools 800
```

## Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--state` | ✅ | Full state name | `"Michigan"` |
| `--abbrev` | ✅ | 2-letter state code | `"MI"` |
| `--org` | ✅ | Organization acronym | `"MHSAA"` |
| `--base-url` | ✅ | Base URL (no trailing slash) | `"https://www.mhsaa.com"` |
| `--classifications` | ✅ | Comma-separated classifications | `"1,2,3,4"` or `"4A,3A,2A,1A"` |
| `--schools` | ✅ | Approximate school count | `750` |
| `--players` | ❌ | Notable players (comma-separated) | `"Magic Johnson,Draymond Green"` |
| `--output-dir` | ❌ | Output directory | `src/datasources/us` (default) |
| `--dry-run` | ❌ | Print code without writing | Flag only |

## Output

Generates complete adapter file: `src/datasources/us/{state}_{org}.py`

Example: `src/datasources/us/michigan_mhsaa.py`

## Post-Generation Checklist

After generating an adapter:

1. **Review generated file**: Customize URL patterns, docstrings, state-specific details
2. **Add DataSourceType enum**: Update `src/models/source.py`
   ```python
   MHSAA = "mhsaa"  # Michigan High School Athletic Association
   ```
3. **Register adapter**: Update `src/datasources/us/__init__.py`
   ```python
   from .michigan_mhsaa import MichiganMHSAADataSource
   __all__ = [..., "MichiganMHSAADataSource"]
   ```
4. **Add config entry**: Update `config/sources.yaml`
   ```yaml
   - id: mhsaa
     name: "MHSAA"
     status: active
     adapter_class: "MichiganMHSAADataSource"
   ```
5. **Create smoke test**: `tests/test_datasources/test_mhsaa.py`
6. **Update PROJECT_LOG.md**: Document new adapter

## Template Features

Generated adapters include:

### Phase 17 Compliance
- ✅ Inherits from `AssociationAdapterBase`
- ✅ Uses shared bracket parser (`parse_bracket_tables_and_divs`)
- ✅ Canonical team IDs (`canonical_team_id(prefix, name)`)
- ✅ Proper deduplication (`seen_ids` set)
- ✅ Configurable classifications and genders
- ✅ Enumeration strategy (all classes or specific)

### Phase 18 Metadata Enrichment
- ✅ `parse_block_meta(soup, year=year)` call in `_parse_bracket_html`
- ✅ Optional `extra` parameter in `_create_game`
- ✅ Metadata passed to `create_data_source_metadata()`
- ✅ Non-breaking (defaults to empty dict)
- ✅ Extracts round, venue, tipoff when available

### Code Quality
- ✅ Comprehensive docstrings with state context
- ✅ Proper type hints (mypy compatible)
- ✅ Structured logging with context
- ✅ Error handling and graceful degradation
- ✅ Async/await patterns

## Examples

### Example 1: Michigan (Numeric Divisions)

```bash
python scripts/scaffold_state_adapter.py \
    --state "Michigan" \
    --abbrev "MI" \
    --org "MHSAA" \
    --base-url "https://www.mhsaa.com" \
    --classifications "1,2,3,4" \
    --schools 750 \
    --players "Magic Johnson,Draymond Green,Glen Rice"
```

**Output**: `src/datasources/us/michigan_mhsaa.py`

**Classifications**: `["1", "2", "3", "4"]` (numeric)

**Notable Players**: Magic Johnson, Draymond Green, Glen Rice

### Example 2: North Carolina (Letter Classifications)

```bash
python scripts/scaffold_state_adapter.py \
    --state "North Carolina" \
    --abbrev "NC" \
    --org "NCHSAA" \
    --base-url "https://www.nchsaa.org" \
    --classifications "4A,3A,2A,1A" \
    --schools 400 \
    --players "Michael Jordan,Chris Paul,James Worthy"
```

**Output**: `src/datasources/us/north_carolina_nchsaa.py`

**Classifications**: `["4A", "3A", "2A", "1A"]` (letter-based)

**Notable Players**: Michael Jordan, Chris Paul, James Worthy

### Example 3: Illinois (Letter + Numeric)

```bash
python scripts/scaffold_state_adapter.py \
    --state "Illinois" \
    --abbrev "IL" \
    --org "IHSA" \
    --base-url "https://www.ihsa.org" \
    --classifications "1A,2A,3A,4A" \
    --schools 800 \
    --players "Dwyane Wade,Isiah Thomas,Anthony Davis"
```

**Output**: `src/datasources/us/illinois_ihsa.py`

**Classifications**: `["1A", "2A", "3A", "4A"]`

**Notable Players**: Dwyane Wade, Isiah Thomas, Anthony Davis

## Dry Run Mode

Preview generated code without writing to disk:

```bash
python scripts/scaffold_state_adapter.py \
    --state "Virginia" \
    --abbrev "VA" \
    --org "VHSL" \
    --base-url "https://www.vhsl.org" \
    --classifications "6,5,4,3,2,1" \
    --schools 320 \
    --dry-run
```

Prints:
- Generated Python code
- Target file path
- No files created

## Roadmap to 50/50 States

Using this scaffolder, we can rapidly generate adapters for all remaining states:

**Priority 1 (Large States)**: IL, NC, VA, WA, MA (5 states)
**Priority 2 (Mid-Size)**: IN, WI, MO, MD, MN (5 states)
**Priority 3 (All Others)**: Remaining 33 states

**Estimated Time**:
- Generate adapter: 30 seconds
- Customize + test: 15-30 minutes per state
- Total: ~25 hours for all 43 remaining states

**Benefits**:
- Consistent code quality across all adapters
- Metadata enrichment included from day 1
- Reduced copy-paste errors
- Faster iteration and testing

## Troubleshooting

### Issue: Generated adapter has wrong prefix

**Problem**: Team IDs use incorrect prefix (e.g., `mhsaa_lincoln` instead of `michigan_lincoln`)

**Solution**: Scaffolder uses organization acronym as prefix (matches Phase 17 pattern). If you need different prefix, edit the generated file's `prefix` variable.

### Issue: Classifications format doesn't match website

**Problem**: Website uses "Class 1" but you passed `"1"`

**Solution**: Customize `_build_bracket_url()` in generated adapter to format classifications correctly:
```python
# Example: Convert "1" → "class-1"
div_slug = f"class-{classification.lower()}"
```

### Issue: URL patterns don't match actual URLs

**Problem**: Real URLs don't match scaffolder's default patterns

**Solution**: Update `_build_bracket_url()` with correct patterns. Check website's actual bracket URLs and adjust accordingly.

## Next Steps

After generating 10-15 adapters:
1. **Create batch testing script**: Test multiple adapters in parallel
2. **URL discovery automation**: Probe common URL patterns to find brackets
3. **Validation harness**: Sanity checks for bracket data (team counts, score ranges)
4. **Nightly CI**: Automate smoke tests for all adapters

---

**Last Updated**: 2025-11-12 23:45 UTC

**Status**: Production-ready scaffolder, tested pattern from 7 Phase 17 adapters
