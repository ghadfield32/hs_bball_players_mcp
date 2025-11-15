# Coverage Measurement - Quick Start

**Goal**: Measure and improve your actual HS basketball data coverage in ONE SITTING.

**Current Status**: ✅ Infrastructure 100% | ❌ Data 0%

---

## The Weekend Plan (4 Steps)

### Step 1: Build Mini Cohort (5 min)

```bash
# Create 2018-2020 D1 cohort template
python scripts/helpers/build_mini_cohort.py --years 2018-2020

# Optionally: Append real players from your database
# (See output for DuckDB SQL template)
```

**Output**: `data/college_cohort_d1_2018_2020.csv`

---

### Step 2: Run Baseline Measurement (2 min)

```bash
# Measure current coverage
bash scripts/helpers/run_coverage_baseline.sh
```

**What You Get**:
- Overall coverage % (likely 30-50% without recruiting data)
- State-by-state priority ranking
- Specific recommendations per state

**Output**: `data/state_gaps_baseline.csv`

---

### Step 3: Quick Win - Activate Recruiting CSV (1 min)

```bash
# Copy example recruiting CSV to active location
bash scripts/helpers/activate_recruiting.sh

# Re-run measurement
python scripts/dashboard_coverage.py \
  --cohort data/college_cohort_d1_2018_2020.csv \
  --export data/state_gaps_after_recruiting.csv
```

**Expected Improvement**: +20-30% for top-ranked players

---

### Step 4: Pick Your First State (10 min)

```bash
# Analyze which state to tackle first
python scripts/helpers/pick_first_state.py
```

**What You Get**:
- Top 5 state candidates ranked by priority
- Specific action plan for #1 state
- Expected impact estimate

---

## Compare Before/After

```bash
# Show coverage improvement
bash scripts/helpers/compare_coverage.sh \
  data/state_gaps_baseline.csv \
  data/state_gaps_after_recruiting.csv
```

---

## Full Command Reference

| Task | Command |
|------|---------|
| **Build cohort** | `python scripts/helpers/build_mini_cohort.py --years 2018-2020` |
| **Measure baseline** | `bash scripts/helpers/run_coverage_baseline.sh` |
| **Activate recruiting** | `bash scripts/helpers/activate_recruiting.sh` |
| **Pick first state** | `python scripts/helpers/pick_first_state.py` |
| **Compare coverage** | `bash scripts/helpers/compare_coverage.sh` |
| **Visual dashboard** | `python scripts/dashboard_coverage.py --cohort COHORT.csv` |
| **Detailed report** | `python scripts/report_coverage.py --cohort COHORT.csv` |

---

## What Each File Does

### Helper Scripts (Copy-Paste Ready)
- `build_mini_cohort.py` - Creates starter cohort CSV (2018-2020)
- `run_coverage_baseline.sh` - Runs measurement + dashboard
- `activate_recruiting.sh` - Activates recruiting CSV import
- `pick_first_state.py` - Recommends which state to implement first
- `compare_coverage.sh` - Diffs before/after CSVs

### Core Coverage Tools
- `dashboard_coverage.py` - Visual ASCII dashboard
- `report_coverage.py` - Detailed per-player coverage report

### Data Files
- `college_cohort_example.csv` - 30 real D1 players (template)
- `recruiting/247_rankings_example.csv` - 26 real recruiting ranks
- `recruiting/247_rankings.csv` - Active recruiting data (create this)

---

## Realistic Coverage Targets

| Segment | Target Coverage |
|---------|----------------|
| **Top 100 Recruits** | 80-90% ✅ |
| **D1 Players (Top States)** | 70-80% ✅ |
| **All US D1 Players** | 60-70% ✅ |
| **International Players** | 30-40% ⚠️ |

**Why Not 100%?**
- Some states have no public HS stats
- International players (FIBA data gaps)
- G League Ignite / prep schools
- Privacy restrictions
- Historical data gaps (pre-2018)

---

## Quick Troubleshooting

### Issue: Low MaxPreps matching (<50%)

**Fix**: State normalization already handles this (Enhancement 12.1)
```python
# Already fixed - "Florida" → "FL", "Fla" → "FL", etc.
```

### Issue: No recruiting coverage

**Fix**: Import recruiting CSV
```bash
bash scripts/helpers/activate_recruiting.sh
```

### Issue: Low advanced stats coverage

**Fix**: Implement state-specific datasource
```bash
# Use pick_first_state.py to find best candidate
python scripts/helpers/pick_first_state.py
```

---

## Next Steps After Weekend Plan

1. **Implement 1-2 State Datasources** (based on dashboard priority)
   - Copy `src/datasources/us/state/state_template.py`
   - Find state HS athletics data source
   - Wire into aggregator

2. **Populate Recruiting CSVs** (if you have data)
   - `data/recruiting/247_rankings.csv`
   - `data/recruiting/espn_rankings.csv`
   - `data/recruiting/on3_rankings.csv`

3. **Expand Cohort** (if mini cohort works well)
   - Extend to 2014-2023 (full D1 cohort)
   - Export from your main player database

4. **Automate Coverage Loop** (weekly monitoring)
   - Run dashboard weekly
   - Track progress over time
   - Prioritize based on gaps

---

## File Paths Quick Reference

```
hs_bball_players_mcp/
├── data/
│   ├── college_cohort_d1_2018_2020.csv    # Your cohort
│   ├── college_cohort_example.csv          # Template
│   ├── state_gaps_baseline.csv             # Before measurements
│   ├── state_gaps_after_recruiting.csv     # After measurements
│   └── recruiting/
│       ├── 247_rankings_example.csv        # Example data
│       └── 247_rankings.csv                # Active data (create this)
│
├── scripts/
│   ├── dashboard_coverage.py               # Visual dashboard
│   ├── report_coverage.py                  # Detailed report
│   └── helpers/
│       ├── build_mini_cohort.py            # Step 1
│       ├── run_coverage_baseline.sh        # Step 2
│       ├── activate_recruiting.sh          # Step 3
│       ├── pick_first_state.py             # Step 4
│       └── compare_coverage.sh             # Compare
│
└── docs/
    ├── QUICKSTART.md                       # This file
    └── COVERAGE_WORKFLOW.md                # Full guide
```

---

## Summary: Your 30-Minute Weekend Checklist

- [ ] Build mini cohort (2018-2020)
- [ ] Run baseline measurement
- [ ] Note top 3 priority states
- [ ] Activate recruiting CSV
- [ ] Re-measure coverage
- [ ] Compare before/after
- [ ] Pick first state to implement
- [ ] Review action plan

**After this weekend**: You'll have concrete metrics, know your gaps, and have a clear plan for improvement.

**Remember**: 60-70% coverage is realistic and sufficient for high-quality forecasting!
