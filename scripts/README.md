# Automation Scripts

This directory contains powerful automation tools for developing and maintaining datasource adapters.

## Overview

| Script | Purpose | Time Savings |
|--------|---------|-------------|
| [generate_adapter.py](#adapter-generator) | Auto-generate new adapter files | **2 hours → 15 minutes** |
| [inspect_website.py](#website-inspector) | Inspect league websites | Structured guidance |
| [verify_adapters.py](#adapter-verification) | Test all adapters systematically | Automated testing |

---

## Adapter Generator

**File**: `generate_adapter.py`
**Purpose**: Automatically generate a new datasource adapter and test file from templates

### Features

- ✅ Interactive CLI with smart defaults
- ✅ Auto-generates adapter Python file (250+ lines)
- ✅ Auto-generates comprehensive test file (200+ lines)
- ✅ Updates `__init__.py` exports
- ✅ Optionally updates `aggregator.py` imports
- ✅ Provides step-by-step next steps checklist
- ✅ Smart naming (handles spaces, special characters)
- ✅ Region detection (US, Canada, Europe, Australia, Global)
- ✅ State code support for US leagues

### Usage

```bash
# Interactive mode (recommended)
python scripts/generate_adapter.py

# You'll be prompted for:
#   - League name (e.g., "Overtime Elite")
#   - Display name
#   - URL prefix (e.g., "ote")
#   - Base URL (e.g., "https://overtimeelite.com")
#   - Region (US, CANADA, EUROPE, etc.)
#   - State code (optional, for US leagues)
#   - Player level (HIGH_SCHOOL, PROFESSIONAL, etc.)
```

### Example Session

```
🏀 Basketball Adapter Generator
======================================================================

📝 League Information
----------------------------------------------------------------------
League name: Overtime Elite
Display name [Overtime Elite]:
URL/file prefix [overtime]: ote
Base URL: https://overtimeelite.com

Region options: US, CANADA, EUROPE, AUSTRALIA, GLOBAL
Region [US]:
State code (optional):

Level options: HIGH_SCHOOL, PROFESSIONAL, JUNIOR, GRASSROOTS
Player level [HIGH_SCHOOL]: PROFESSIONAL

📋 Summary
======================================================================
League: Overtime Elite
Prefix: ote
Base URL: https://overtimeelite.com
Region: US
Level: PROFESSIONAL
Region path: src/datasources/us/ote.py

Generate files? (yes/no) [yes]:

🔨 Generating Files
======================================================================
✅ Created adapter: src/datasources/us/ote.py
✅ Created test file: tests/test_datasources/test_ote.py
✅ Updated src/datasources/us/__init__.py
✅ Updated aggregator.py

✅ Generation Complete!
======================================================================

📋 Next Steps:
1. Visit https://overtimeelite.com
2. Update URLs in src/datasources/us/ote.py
3. Add DataSourceType.OTE to src/models/source.py
4. Run tests: pytest tests/test_datasources/test_ote.py -v
```

### Output Files

**Adapter File** (`src/datasources/{region}/{prefix}.py`):
- Complete class structure extending `BaseDataSource`
- All required methods implemented with helper functions
- TODO comments marking what needs updating
- Comprehensive docstrings

**Test File** (`tests/test_datasources/test_{prefix}.py`):
- 10+ test cases covering all functionality
- Real API call tests (integration tests)
- Sample data printing for debugging
- Pytest fixtures and async support

---

## Website Inspector

**File**: `inspect_website.py`
**Purpose**: Inspect league websites to gather information for adapter implementation

### Features

- ✅ **EYBL-specific mode** for debugging broken adapter
- ✅ **Generic website inspection** for new adapters
- ✅ **Existing adapter inspection** for verification
- ✅ HTML table detection and analysis
- ✅ JavaScript framework detection
- ✅ Alternative URL discovery
- ✅ Manual inspection guidance

### Usage

```bash
# Fix EYBL adapter (broken - website changed)
python scripts/inspect_website.py --adapter eybl

# Inspect new website for adapter creation
python scripts/inspect_website.py --url https://newleague.com

# Inspect existing adapter
python scripts/inspect_website.py --adapter psal

# Interactive mode
python scripts/inspect_website.py
```

### EYBL Fix Workflow

```bash
# Step 1: Run inspection
python scripts/inspect_website.py --adapter eybl

# Step 2: Follow the checklist provided:
#   - Check current stats URL
#   - Try alternative URLs
#   - Manual browser inspection guidance
#   - Update adapter code instructions

# Step 3: Update adapter based on findings
# Edit src/datasources/us/eybl.py:
#   - Update stats_url
#   - Update table_class_hint
#   - Update column mappings if changed

# Step 4: Test
pytest tests/test_datasources/test_eybl.py -v -s
```

### What It Checks

**For Each URL**:
- ✅ Accessibility (404, redirects, timeouts)
- ✅ Number of tables found
- ✅ Table class names and IDs
- ✅ Column headers
- ✅ Row counts
- ✅ JavaScript frameworks (React, Vue, Angular)

**Output Example**:
```
🔍 Inspecting: https://nikeeyb.com/stats
✅ Status: 200 OK
📊 Found 2 table(s)

🔎 Table Analysis:

  Table 1:
    Classes: stats-table, sortable
    Headers (15): Player, Team, Pos, GP, PPG, RPG, APG, SPG, BPG, ...
    Rows: 142

  Table 2:
    Classes: team-standings
    Headers (8): Rank, Team, W, L, Win%, PPG, Opp PPG, Diff
    Rows: 16
```

---

## Adapter Verification

**File**: `verify_adapters.py`
**Purpose**: Systematically test all datasource adapters and report their status

### Features

- ✅ **5-test suite** per adapter
- ✅ Health check (website accessibility)
- ✅ Player search (data extraction)
- ✅ Player lookup (get by ID)
- ✅ Season stats (statistics retrieval)
- ✅ Leaderboard (rankings)
- ✅ Comprehensive error reporting
- ✅ JSON report generation
- ✅ Quick mode (health check only)

### Usage

```bash
# Test all adapters (full suite)
python scripts/verify_adapters.py

# Test specific adapter
python scripts/verify_adapters.py --adapter eybl

# Quick health check all adapters
python scripts/verify_adapters.py --quick

# Generate JSON report
python scripts/verify_adapters.py --report

# Test and report
python scripts/verify_adapters.py --adapter psal --report
```

### Test Output Example

```
======================================================================
Testing: EYBL (EYBLDataSource)
======================================================================

1️⃣  Health Check... ✅ PASS

2️⃣  Search Players... ✅ PASS - Found 5 players
   Sample: John Doe (Lakers)

3️⃣  Get Player by ID... ✅ PASS

4️⃣  Get Season Stats... ✅ PASS
   Games: 25, PPG: 18.5, RPG: 6.2, APG: 3.8

5️⃣  Get Leaderboard... ✅ PASS - Found 5 leaders
   Top 3:
     1. Jane Smith: 24.3
     2. Bob Johnson: 22.1
     3. Alice Brown: 21.7

======================================================================
📊 ADAPTER TEST SUMMARY
======================================================================

✅ EYBL - PASSING
   Tests: 5 passed, 0 failed

⚠️  PSAL - PASSING_WITH_WARNINGS
   Tests: 4 passed, 1 failed
   Warnings: 1
     - Season stats returned None

❌ MN Hub - FAILING
   Tests: 2 passed, 3 failed
   Errors: 2
     - No stats table found
     - Search players error: Table not found

======================================================================
Total: 1 passing, 1 failing, 1 with warnings
======================================================================
```

### JSON Report Format

```json
{
  "timestamp": "2025-11-11T15:30:00",
  "summary": {
    "total_adapters": 4,
    "passing": 2,
    "failing": 2,
    "with_warnings": 1
  },
  "adapters": {
    "EYBL": {
      "name": "EYBL",
      "class": "EYBLDataSource",
      "status": "passing",
      "healthy": true,
      "tests_passed": 5,
      "tests_failed": 0,
      "errors": [],
      "warnings": [],
      "player_count": 142,
      "sample_player": {
        "id": "eybl_john_doe",
        "name": "John Doe",
        "team": "Lakers",
        "position": "PG"
      }
    }
  }
}
```

---

## Workflows

### Creating a New Adapter

```bash
# 1. Generate files
python scripts/generate_adapter.py

# 2. Inspect website
python scripts/inspect_website.py --url https://newleague.com

# 3. Update generated adapter file based on inspection
#    - Update URLs
#    - Update table_class_hint
#    - Update column mappings if needed

# 4. Add DataSourceType enum value
#    Edit src/models/source.py

# 5. Test adapter
python scripts/verify_adapters.py --adapter newleague

# 6. Fix any issues and retest

# 7. Full test suite
pytest tests/test_datasources/test_newleague.py -v -s
```

### Fixing Broken Adapter

```bash
# 1. Verify it's broken
python scripts/verify_adapters.py --adapter eybl

# 2. Inspect website to understand changes
python scripts/inspect_website.py --adapter eybl

# 3. Update adapter code based on findings

# 4. Test again
python scripts/verify_adapters.py --adapter eybl

# 5. If passing, commit changes
git add src/datasources/us/eybl.py
git commit -m "Fix EYBL adapter after website structure change"
```

### Regular Maintenance

```bash
# Weekly: Check all adapters
python scripts/verify_adapters.py --quick

# Monthly: Full test suite with report
python scripts/verify_adapters.py --report

# Review report for issues
cat adapter_test_report_*.json
```

---

## Requirements

All scripts require:
- Python 3.10+
- httpx (for HTTP requests)
- beautifulsoup4 (for HTML parsing)
- Project dependencies (see requirements.txt)

Install with:
```bash
pip install httpx beautifulsoup4
# or
pip install -r requirements.txt
```

---

## Tips & Best Practices

### Adapter Generator

**DO**:
- ✅ Use descriptive league names
- ✅ Keep prefixes short and memorable
- ✅ Specify state for US regional leagues
- ✅ Run generator from project root

**DON'T**:
- ❌ Use special characters in prefix
- ❌ Create duplicate adapters
- ❌ Skip the next steps checklist

### Website Inspector

**DO**:
- ✅ Inspect before implementing
- ✅ Check multiple pages (stats, teams, schedule)
- ✅ Note exact table class names
- ✅ Document column name variations

**DON'T**:
- ❌ Assume URL patterns
- ❌ Skip JavaScript framework check
- ❌ Ignore redirect warnings

### Adapter Verification

**DO**:
- ✅ Run before committing changes
- ✅ Generate reports for tracking
- ✅ Fix warnings even if tests pass
- ✅ Use quick mode for rapid checks

**DON'T**:
- ❌ Ignore warnings
- ❌ Skip specific adapter tests
- ❌ Assume failing tests are temporary

---

## Troubleshooting

### Script Won't Run

```bash
# Ensure you're in project root
cd /path/to/hs_bball_players_mcp

# Check Python path
python --version  # Should be 3.10+

# Install dependencies
pip install -r requirements.txt
```

### Import Errors

```bash
# Make sure project is in Python path
export PYTHONPATH="$PWD:$PYTHONPATH"

# Or run from project root
cd /path/to/hs_bball_players_mcp
python scripts/generate_adapter.py
```

### Adapter Generator Issues

**Issue**: "Could not update aggregator.py"
**Solution**: Manually add import line provided in error message

**Issue**: "Invalid prefix"
**Solution**: Use only lowercase letters, numbers, and underscores

### Website Inspector Issues

**Issue**: "Request timed out"
**Solution**: Check internet connection, try again, or increase timeout

**Issue**: "No tables found"
**Solution**: Website may use JavaScript rendering - check browser

### Adapter Verification Issues

**Issue**: "Import error"
**Solution**: Ensure adapter is in correct directory and imports are valid

**Issue**: "All tests failing"
**Solution**: Run website inspector to check if website structure changed

---

## Contributing

When adding new scripts:
1. Follow existing naming convention
2. Include comprehensive docstrings
3. Add error handling
4. Update this README
5. Test on Windows, Mac, and Linux

---

## Links

- [ADAPTER_TESTING_REPORT.md](../ADAPTER_TESTING_REPORT.md) - Detailed testing findings
- [PROJECT_LOG.md](../PROJECT_LOG.md) - Full project history
- [DATASOURCE_IMPLEMENTATION_GUIDE.md](../DATASOURCE_IMPLEMENTATION_GUIDE.md) - Implementation guide

---

*Last Updated: 2025-11-11*
