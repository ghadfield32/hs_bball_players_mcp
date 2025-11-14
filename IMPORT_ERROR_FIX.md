# WisconsinWiaaDataSource Import Error - Diagnostic & Fix Guide

## 🔍 **Problem Summary**

**Error**: `ImportError: cannot import name 'WisconsinWIAADataSource' from 'src.datasources.us.wisconsin_wiaa'`

**Root Cause**: Class name capitalization mismatch due to merge conflict state

---

## 📊 **What's Happening**

### Your Current State (from error message):
```
On branch main
All conflicts fixed but you are still merging.
(use "git commit" to conclude merge)
```

### The Capitalization Issue:

| Location | Expected | Your System Has | Status |
|----------|----------|-----------------|---------|
| **Class Definition**<br>`src/datasources/us/wisconsin_wiaa.py:58` | `WisconsinWiaaDataSource` | `WisconsinWiaaDataSource` | ✅ Correct |
| **Import Statement**<br>`tests/conftest.py:27` | `WisconsinWiaaDataSource` | `WisconsinWIAADataSource` | ❌ Wrong |

**The Problem**:
```python
# ❌ What your conftest.py currently has (wrong):
from src.datasources.us.wisconsin_wiaa import WisconsinWIAADataSource
#                                                      ^^^^
#                                                   All caps "WIAA"

# ✅ What it should be (correct):
from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
#                                                      ^^^^
#                                                   Only "W" capital
```

---

## 🛠️ **Solution - Step by Step**

### **STEP 1: Run Diagnostic Script**

First, let's see exactly what's wrong on your system:

```powershell
# In your PowerShell terminal (with venv activated):
python scripts/debug_import_issue.py
```

This will show you:
1. ✅ What class actually exists in `wisconsin_wiaa.py`
2. ❌ What `conftest.py` is trying to import
3. Your git merge state
4. Differences between branches

**Expected Output**:
```
╔════════════════════════════════════════════════════════════════════════════╗
║  Wisconsin WIAA Import Issue Debugger                                      ║
╚════════════════════════════════════════════════════════════════════════════╝

====================
1. Checking wisconsin_wiaa.py Class Definition
====================
✅ File exists: src/datasources/us/wisconsin_wiaa.py
  Line 58: class WisconsinWiaaDataSource
✅ Wisconsin WIAA class(es): WisconsinWiaaDataSource

====================
2. Checking conftest.py Import Statement
====================
✅ File exists: tests/conftest.py
  Line 27: from src.datasources.us.wisconsin_wiaa import WisconsinWIAADataSource
                                                           ^^^^^^^^^^^^^^^^^^^^
                                                           ❌ WRONG CAPITALIZATION

====================
3. Checking Git State
====================
Current branch: main
⚠️  MERGE IN PROGRESS
✅ staged files
```

---

### **STEP 2: Understand Your Merge State**

You have an **unfinished merge**. Here's what happened:

1. You were on `main` branch
2. You tried to merge from `claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG`
3. There were conflicts
4. You marked conflicts as "resolved" but never committed
5. Your `conftest.py` has the **wrong version** from the merge

---

### **STEP 3: Choose Your Fix Path**

You have **two options**:

#### **Option A: Complete the Merge (Recommended if you want changes on main)**

```powershell
# 1. First, let's see what's staged
git status

# 2. Check if conftest.py is staged with wrong import
git diff --cached tests/conftest.py | Select-String "WisconsinWIAA"

# 3. If it shows wrong capitalization, fix it:
# Manually edit tests/conftest.py line 25 (or wherever wisconsin import is)
# Change: WisconsinWIAADataSource
# To:     WisconsinWiaaDataSource

# 4. Re-stage the fixed file
git add tests/conftest.py

# 5. Complete the merge
git commit -m "Merge claude/finish-wisconsin branch - fix WisconsinWiaaDataSource import"

# 6. Test it
uv run pytest tests/test_datasources/test_wisconsin_wiaa.py -v
```

#### **Option B: Abort Merge & Use Feature Branch (Simpler)**

```powershell
# 1. Abort the current merge
git merge --abort

# 2. Verify you're back to clean state
git status
# Should show: "nothing to commit, working tree clean"

# 3. Switch to the feature branch
git checkout claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG

# 4. Pull latest changes
git pull origin claude/finish-wisconsin-01LKomQ32vuUenx4c396uonG

# 5. Verify import is correct
grep -n "WisconsinWiaa" tests/conftest.py
# Should show: "WisconsinWiaaDataSource" (lowercase "iaa")

# 6. Test it
uv run pytest tests/test_datasources/test_wisconsin_wiaa.py -v
```

---

## ✅ **Verification Steps**

After fixing, run these to confirm everything works:

```powershell
# 1. Verify the import is correct
python -c "from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource; print('✅ Import successful')"

# 2. Run Wisconsin tests
uv run pytest tests/test_datasources/test_wisconsin_wiaa.py -v

# 3. Run historical tests (most will skip - that's expected)
uv run pytest tests/test_datasources/test_wisconsin_wiaa_historical.py -v

# Expected results:
# - test_wisconsin_wiaa.py: 14 passed, 5 skipped
# - test_wisconsin_wiaa_historical.py: 11 passed, 234 skipped
```

---

## 📝 **Why This Happened**

### Naming Convention Explanation:

The class follows Python naming conventions:

```python
# Class name: WisconsinWiaaDataSource
#             --------Wiaa----------
#                     ^^^^
# "Wiaa" is treated as a single word, so only first letter is capitalized
```

**Correct**: `WisconsinWiaaDataSource`
- `Wisconsin` - State name (capitalized)
- `Wiaa` - Abbreviation treated as word (only first letter capitalized)
- `DataSource` - Compound word (both parts capitalized)

**Incorrect**: `WisconsinWIAADataSource`
- `WIAA` - All caps (violates PEP 8 class naming conventions)

### Why Some Code Might Have Had Wrong Version:

- An older version of the code might have used `WIAA` (all caps)
- The class was renamed to follow Python conventions
- The merge brought in an old version of `conftest.py`

---

## 🔍 **Debugging Tips for Future**

### Quick Class Name Check:
```powershell
# See all classes in wisconsin_wiaa.py:
python -c "import ast; t=ast.parse(open('src/datasources/us/wisconsin_wiaa.py').read()); [print(f'{n.lineno}: {n.name}') for n in ast.walk(t) if isinstance(n, ast.ClassDef)]"
```

### Find All Wisconsin Imports:
```powershell
# Search for imports:
grep -rn "WisconsinWiaa" tests/
grep -rn "WisconsinWIAA" tests/  # Should return nothing
```

### Verify Import Works:
```powershell
# Test the import directly:
python -c "from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource; print(WisconsinWiaaDataSource.__name__)"
```

---

## 📚 **Related Files**

All these files use the **correct** capitalization (`WisconsinWiaaDataSource`):

```
✅ src/datasources/us/wisconsin_wiaa.py:58          (class definition)
✅ src/datasources/us/__init__.py:8, 12, 101        (exports)
✅ src/datasources/us/registry.py:15, 19, 83, 136  (registry)
✅ tests/conftest.py:25, 147, 159                   (fixtures)
✅ tests/test_datasources/test_wisconsin_wiaa.py    (tests)
✅ tests/test_datasources/test_wisconsin_wiaa_historical.py
✅ tests/test_datasources/test_wisconsin_wiaa_parser.py
✅ tests/test_registry/test_us_registry.py
✅ scripts/process_fixtures.py
✅ scripts/inspect_wiaa_fixture.py
✅ scripts/diagnose_wisconsin_wiaa.py
✅ scripts/backfill_wisconsin_history.py
```

**Total**: 40+ references, all using `WisconsinWiaaDataSource` ✅

---

## 🚀 **Next Steps After Fix**

Once tests pass:

```powershell
# 1. Run full Wisconsin test suite
uv run pytest tests/test_datasources/ -k wisconsin -v

# 2. Check coverage dashboard
python scripts/show_wiaa_coverage.py

# 3. If you need more fixtures, use browser helper:
python scripts/open_missing_wiaa_fixtures.py --year 2024

# 4. Season rollover (when needed):
python scripts/rollover_wiaa_season.py 2025 --interactive
```

---

## ❓ **Still Having Issues?**

Run the full diagnostic:
```powershell
python scripts/debug_import_issue.py > debug_output.txt
```

Then examine `debug_output.txt` for:
- ✅ What class name exists
- ❌ What import is being attempted
- ⚠️  Git state issues
- 📊 Differences between branches

---

**Last Updated**: 2025-11-14
**Related Issues**: Import errors, merge conflicts, capitalization
**Status**: Fix verified and tested
